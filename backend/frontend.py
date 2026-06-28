from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
import logging
import uuid
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

# Import psycopg for AsyncConnectionPool
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

# Import checkpoint savers
from langgraph.checkpoint.memory import MemorySaver
try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
except ImportError:
    try:
        from langgraph.checkpoint.postgres import PostgresSaver as AsyncPostgresSaver
    except ImportError:
        AsyncPostgresSaver = None

# Import our backend modules
from backend.graph import build_graph, create_mcp_client, AgentState
from backend.auth import get_current_user, get_ws_user, get_org_id_for_user
from backend.config import build_mcp_config_for_tenant
from backend.prompts import build_system_prompt
import backend.oauth as oauth
import backend.upload as upload
import backend.app.csv.routes as csv_routes

from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.types import Command

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
SUPABASE_URI = os.getenv("SUPABASE_URI", "")

# Global variables for db pool and checkpointer
pool: Optional[AsyncConnectionPool] = None
checkpointer: Any = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app: handles db pool and checkpointer setup."""
    global pool, checkpointer
    if SUPABASE_URI:
        try:
            logger.info("Initializing Supabase/PostgreSQL pool...")
            pool = AsyncConnectionPool(
                conninfo=SUPABASE_URI,
                min_size=1,
                max_size=10,
                open=True,
                kwargs={"row_factory": dict_row, "prepare_threshold": None}
            )
            # Inject connection pool into OAuth, CSV upload, and CSV pipeline modules
            oauth.set_pg_pool(pool)
            upload.set_pg_pool(pool)
            csv_routes.set_pg_pool(pool)
            
            if AsyncPostgresSaver:
                logger.info("Setting up PostgresSaver checkpointer...")
                checkpointer = AsyncPostgresSaver(pool)
                # Auto-create necessary checkpointer tables
                await checkpointer.setup()
                logger.info("Postgres checkpointer setup complete.")
            else:
                logger.warning("AsyncPostgresSaver could not be imported; falling back to MemorySaver.")
                checkpointer = MemorySaver()
        except Exception as e:
            logger.error(f"Failed to initialize database pool/checkpointer: {e}")
            logger.warning("Falling back to MemorySaver for local dev.")
            checkpointer = MemorySaver()
    else:
        logger.warning("SUPABASE_URI is not set; checkpointer falling back to MemorySaver.")
        checkpointer = MemorySaver()

    yield

    if pool:
        logger.info("Closing database pool...")
        await pool.close()
        logger.info("Database pool closed.")

app = FastAPI(
    title="Bandhan AI Multi-Tenant API",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(oauth.router)
app.include_router(upload.router)
app.include_router(csv_routes.router)

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_sessions: Dict[str, Dict[str, Any]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        org_id: str,
        mcp_config_override: dict,
        system_prompt: str
    ):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
        # Scope session history to tenant + session to prevent data leaking
        thread_id = f"{org_id}:{session_id}"
        
        # Create MCP client and enter its async context (keeps MCP servers alive)
        mcp_client, tools = await create_mcp_client(mcp_config_override)
        
        # Build tenant-scoped LangGraph instance with pre-loaded tools
        graph_instance = await build_graph(
            checkpointer=checkpointer,
            system_prompt=system_prompt,
            tools=tools,
        )

        self.agent_sessions[session_id] = {
            "graph": graph_instance,
            "config": {
                "configurable": {"thread_id": thread_id},
                "recursion_limit": 100
            },
            "yolo_mode": True,  # Allow rapid campaign creation, can be changed via settings
            "created_at": datetime.now(),
            "mcp_client": mcp_client,  # Store for cleanup on disconnect
        }
        logger.info(f"WebSocket session connected: {session_id} (Tenant: {org_id})")

    async def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.agent_sessions:
            session = self.agent_sessions.pop(session_id)
            # Clean up MCP client (exit async context to stop MCP server processes)
            mcp_client = session.get("mcp_client")
            if mcp_client:
                try:
                    await mcp_client.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Error closing MCP client for session {session_id}: {e}")
        logger.info(f"WebSocket session disconnected: {session_id}")

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {e}")
                await self.disconnect(session_id)

manager = ConnectionManager()

class BandhanAIWebSocketHandler:
    def __init__(self, manager: ConnectionManager):
        self.manager = manager

    async def stream_agent_responses(self, session_id: str, input_data: dict):
        """Stream responses from the agent to the WebSocket client"""
        try:
            session = self.manager.agent_sessions[session_id]
            graph = session["graph"]
            config = session["config"]
            
            # Send typing indicator
            await self.manager.send_message(session_id, {
                "type": "typing",
                "status": True,
                "timestamp": datetime.now().isoformat()
            })

            # Create graph input
            if isinstance(input_data, dict) and "resume" in input_data:
                # Handle resume command for interrupts
                graph_input = Command(resume=input_data["resume"])
            else:
                # Regular message
                graph_input = {
                    "messages": [HumanMessage(content=input_data.get("message", ""))],
                    "yolo_mode": session["yolo_mode"],
                }

            # Stream responses from the agent
            message_buffer = ""
            async for message_chunk, metadata in graph.astream(
                input=graph_input,
                stream_mode="messages",
                config=config
            ):
                if isinstance(message_chunk, AIMessageChunk):
                    # Handle finish reason
                    if message_chunk.response_metadata:
                        finish_reason = message_chunk.response_metadata.get("finish_reason", "")
                        if finish_reason == "tool_calls":
                            if message_buffer.strip():
                                await self.manager.send_message(session_id, {
                                    "type": "message_chunk",
                                    "content": message_buffer,
                                    "is_complete": False,
                                    "timestamp": datetime.now().isoformat()
                                })
                                message_buffer = ""

                    # Handle tool calls
                    if message_chunk.tool_call_chunks:
                        tool_chunk = message_chunk.tool_call_chunks[0]
                        tool_name = tool_chunk.get("name", "")
                        args = tool_chunk.get("args", "")

                        if tool_name:
                            await self.manager.send_message(session_id, {
                                "type": "tool_call",
                                "tool_name": tool_name,
                                "args": args,
                                "timestamp": datetime.now().isoformat()
                            })
                    else:
                        # Regular message content
                        if message_chunk.content:
                            message_buffer += message_chunk.content
                            await self.manager.send_message(session_id, {
                                "type": "message_chunk",
                                "content": message_chunk.content,
                                "is_complete": False,
                                "timestamp": datetime.now().isoformat()
                            })

            # Send final message if there's buffered content
            if message_buffer.strip():
                await self.manager.send_message(session_id, {
                    "type": "message",
                    "content": message_buffer,
                    "is_complete": True,
                    "timestamp": datetime.now().isoformat()
                })

            # Stop typing indicator
            await self.manager.send_message(session_id, {
                "type": "typing",
                "status": False,
                "timestamp": datetime.now().isoformat()
            })

            # Check for interrupts (approval requests)
            await self.handle_interrupts(session_id)

        except Exception as e:
            logger.error(f"Error in stream_agent_responses: {e}")
            await self.manager.send_message(session_id, {
                "type": "error",
                "message": f"Agent error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
            await self.manager.send_message(session_id, {
                "type": "typing",
                "status": False,
                "timestamp": datetime.now().isoformat()
            })

    async def handle_interrupts(self, session_id: str):
        """Handle agent interrupts (approval requests)"""
        try:
            session = self.manager.agent_sessions[session_id]
            graph = session["graph"]
            config = session["config"]
            
            thread_state = graph.get_state(config=config)
            
            if thread_state.interrupts:
                for interrupt in thread_state.interrupts:
                    await self.manager.send_message(session_id, {
                        "type": "approval_request",
                        "data": interrupt.value,
                        "interrupt_id": str(uuid.uuid4()),
                        "timestamp": datetime.now().isoformat()
                    })
        except Exception as e:
            logger.error(f"Error handling interrupts: {e}")

    async def handle_approval_response(self, session_id: str, approval_data: dict):
        """Handle user's approval response"""
        try:
            action = approval_data.get("action", "continue")
            data = approval_data.get("data", None)
            
            resume_input = {
                "resume": {
                    "action": action,
                    "data": data
                }
            }
            await self.stream_agent_responses(session_id, resume_input)
        except Exception as e:
            logger.error(f"Error handling approval response: {e}")
            await self.manager.send_message(session_id, {
                "type": "error",
                "message": f"Approval handling error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })

websocket_handler = BandhanAIWebSocketHandler(manager)

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, token: Optional[str] = Query(None)):
    """Tenant-isolated, token-authorized WebSocket connection endpoint."""
    logger.info(f"WebSocket connection attempt: session_id={session_id}, has_token={bool(token)}")
    try:
        # 1. Authenticate WebSocket connection
        logger.info("Step 1: Authenticating...")
        user = await get_ws_user(websocket, token)
        logger.info(f"Step 1 OK: user={user.get('sub', 'unknown')}")
        
        # 2. Lookup the tenant's org_id
        logger.info("Step 2: Looking up org_id...")
        org_id = await get_org_id_for_user(user["sub"], pool)
        logger.info(f"Step 2 OK: org_id={org_id}")
        
        # 3. Fetch tenant metadata
        logger.info("Step 3: Fetching tenant metadata...")
        tenant = None
        async with pool.connection() as conn:
            result = await conn.execute(
                "SELECT * FROM tenants WHERE org_id = %s",
                (org_id,)
            )
            tenant = await result.fetchone()
        logger.info(f"Step 3 OK: tenant={tenant.get('org_name') if tenant else None}")

        # 4. Dynamically configure MCP config and agent persona
        logger.info("Step 4: Building MCP config...")
        mcp_config_override = await build_mcp_config_for_tenant(org_id, pool)
        system_prompt = build_system_prompt(tenant) if tenant else None
        logger.info(f"Step 4 OK: MCP servers={list(mcp_config_override.get('mcpServers', {}).keys())}")

        # 5. Connect and register graph instance
        logger.info("Step 5: Building graph and accepting WebSocket...")
        await manager.connect(websocket, session_id, org_id, mcp_config_override, system_prompt)
        logger.info("Step 5 OK: WebSocket connected and graph built!")
    except Exception as e:
        import traceback
        logger.error(f"WebSocket auth/connection setup failed at: {e}\n{traceback.format_exc()}")
        # ws connection has been handled or closed
        return

    try:
        agent_name = tenant.get("agent_name", "Ralph") if tenant else "Ralph"
        await manager.send_message(session_id, {
            "type": "message",
            "content": f"Hello! I'm {agent_name}, your AI growth partner. How can I assist you today?",
            "is_complete": True,
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            message_type = message_data.get("type", "message")
            
            if message_type == "message":
                user_message = message_data.get("content", "")
                if user_message.strip():
                    await manager.send_message(session_id, {
                        "type": "user_message",
                        "content": user_message,
                        "timestamp": datetime.now().isoformat()
                    })
                    await websocket_handler.stream_agent_responses(
                        session_id, 
                        {"message": user_message}
                    )
            
            elif message_type == "approval_response":
                await websocket_handler.handle_approval_response(
                    session_id, 
                    message_data
                )
            
            elif message_type == "ping":
                await manager.send_message(session_id, {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                logger.warning(f"Unknown WS message type: {message_type}")

    except WebSocketDisconnect:
        await manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket connection error for session {session_id}: {e}")
        await manager.disconnect(session_id)

# ---------------------------------------------------------------------------
# REST Streaming Chat API (replaces WebSocket for chat)
# ---------------------------------------------------------------------------

from fastapi.responses import StreamingResponse

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

# In-memory session store for REST chat (keyed by org_id:session_id)
_chat_sessions: Dict[str, Dict[str, Any]] = {}

async def _get_or_create_session(org_id: str, session_id: str, tenant: dict) -> Dict[str, Any]:
    """Get an existing chat session or create a new one with MCP tools + graph."""
    key = f"{org_id}:{session_id}"
    if key in _chat_sessions:
        return _chat_sessions[key]

    logger.info(f"Creating new chat session: {key}")
    mcp_config = await build_mcp_config_for_tenant(org_id, pool)
    system_prompt = build_system_prompt(tenant) if tenant else None

    client, tools = await create_mcp_client(mcp_config)
    graph = await build_graph(
        checkpointer=checkpointer,
        system_prompt=system_prompt,
        tools=tools,
    )

    session = {
        "graph": graph,
        "config": {"configurable": {"thread_id": key}, "recursion_limit": 100},
        "mcp_client": client,
        "yolo_mode": True,
    }
    _chat_sessions[key] = session
    return session

@app.post("/api/chat")
async def chat_endpoint(
    req: ChatRequest,
    user: dict = Depends(get_current_user),
):
    """
    Send a message to the AI agent and stream the response as Server-Sent Events.
    
    Each SSE event is a JSON object with a `type` field:
      - typing: {status: bool}
      - message_chunk: {content: str}
      - message: {content: str, is_complete: true}
      - tool_call: {tool_name: str, args: str}
      - approval_request: {data: dict}
      - error: {message: str}
      - done: {}
    """
    # Look up tenant
    org_id = await get_org_id_for_user(user["sub"], pool)

    tenant = None
    async with pool.connection() as conn:
        result = await conn.execute("SELECT * FROM tenants WHERE org_id = %s", (org_id,))
        tenant = await result.fetchone()

    session = await _get_or_create_session(org_id, req.session_id, tenant)

    async def event_stream():
        try:
            graph = session["graph"]
            config = session["config"]

            graph_input = {
                "messages": [HumanMessage(content=req.message)],
                "yolo_mode": session["yolo_mode"],
            }

            # Signal typing
            yield f"data: {json.dumps({'type': 'typing', 'status': True})}\n\n"

            message_buffer = ""
            async for message_chunk, metadata in graph.astream(
                input=graph_input,
                stream_mode="messages",
                config=config,
            ):
                if isinstance(message_chunk, AIMessageChunk):
                    # Tool call finish
                    if message_chunk.response_metadata:
                        finish_reason = message_chunk.response_metadata.get("finish_reason", "")
                        if finish_reason == "tool_calls" and message_buffer.strip():
                            yield f"data: {json.dumps({'type': 'message_chunk', 'content': message_buffer})}\n\n"
                            message_buffer = ""

                    # Tool call chunks
                    if message_chunk.tool_call_chunks:
                        tc = message_chunk.tool_call_chunks[0]
                        tool_name = tc.get("name", "")
                        args = tc.get("args", "")
                        if tool_name:
                            yield f"data: {json.dumps({'type': 'tool_call', 'tool_name': tool_name, 'args': args})}\n\n"
                    elif message_chunk.content:
                        message_buffer += message_chunk.content
                        yield f"data: {json.dumps({'type': 'message_chunk', 'content': message_chunk.content})}\n\n"

            # Final message
            if message_buffer.strip():
                yield f"data: {json.dumps({'type': 'message', 'content': message_buffer, 'is_complete': True})}\n\n"

            # Stop typing
            yield f"data: {json.dumps({'type': 'typing', 'status': False})}\n\n"

            # Check for interrupts (approval requests)
            thread_state = graph.get_state(config=config)
            if thread_state.interrupts:
                for interrupt in thread_state.interrupts:
                    yield f"data: {json.dumps({'type': 'approval_request', 'data': interrupt.value, 'interrupt_id': str(uuid.uuid4())})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class ApprovalRequest(BaseModel):
    session_id: str = "default"
    action: str  # "continue", "update", "feedback"
    data: Optional[str] = None

@app.post("/api/chat/approve")
async def chat_approve_endpoint(
    req: ApprovalRequest,
    user: dict = Depends(get_current_user),
):
    """Handle approval response for agent interrupts."""
    org_id = await get_org_id_for_user(user["sub"], pool)
    key = f"{org_id}:{req.session_id}"

    if key not in _chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")

    session = _chat_sessions[key]

    async def event_stream():
        try:
            graph = session["graph"]
            config = session["config"]
            resume_input = Command(resume={"action": req.action, "data": req.data})

            yield f"data: {json.dumps({'type': 'typing', 'status': True})}\n\n"

            message_buffer = ""
            async for message_chunk, metadata in graph.astream(
                input=resume_input,
                stream_mode="messages",
                config=config,
            ):
                if isinstance(message_chunk, AIMessageChunk):
                    if message_chunk.tool_call_chunks:
                        tc = message_chunk.tool_call_chunks[0]
                        tool_name = tc.get("name", "")
                        if tool_name:
                            yield f"data: {json.dumps({'type': 'tool_call', 'tool_name': tool_name, 'args': tc.get('args', '')})}\n\n"
                    elif message_chunk.content:
                        message_buffer += message_chunk.content
                        yield f"data: {json.dumps({'type': 'message_chunk', 'content': message_chunk.content})}\n\n"

            if message_buffer.strip():
                yield f"data: {json.dumps({'type': 'message', 'content': message_buffer, 'is_complete': True})}\n\n"

            yield f"data: {json.dumps({'type': 'typing', 'status': False})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.error(f"Approval stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# REST API Endpoints for Tenancy & Onboarding (Phase 2 & 6)
# ---------------------------------------------------------------------------

class RegisterTenantRequest(BaseModel):
    org_name: str
    agent_name: str = "Ralph"
    backstory: Optional[str] = None
    tone_instructions: Optional[str] = None

@app.post("/auth/register-tenant")
async def register_tenant(
    req: RegisterTenantRequest,
    user: dict = Depends(get_current_user)
):
    """
    Onboarding: Create a new tenant record and link to their Supabase auth account.
    Also creates a corresponding integrations row automatically.
    """
    auth_uid = user["sub"]
    email = user.get("email", "")
    
    if not pool:
        raise HTTPException(status_code=500, detail="Database connection not available")

    try:
        async with pool.connection() as conn:
            # Check if tenant already exists
            result = await conn.execute(
                "SELECT org_id FROM tenants WHERE owner_auth_uid = %s",
                (auth_uid,)
            )
            row = await result.fetchone()
            if row:
                await conn.execute(
                    """
                    UPDATE tenants
                    SET org_name = %s,
                        agent_name = %s,
                        backstory = %s,
                        tone_instructions = %s
                    WHERE org_id = %s
                    """,
                    (
                        req.org_name,
                        req.agent_name,
                        req.backstory,
                        req.tone_instructions,
                        row["org_id"],
                    )
                )
                return {"org_id": str(row["org_id"]), "status": "updated"}
            
            # Create the tenant row
            result = await conn.execute(
                """
                INSERT INTO tenants (owner_email, owner_auth_uid, org_name, agent_name, backstory, tone_instructions)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING org_id
                """,
                (email, auth_uid, req.org_name, req.agent_name, req.backstory, req.tone_instructions)
            )
            row = await result.fetchone()
            org_id = row["org_id"]
            
            # Create placeholder integrations record
            await conn.execute(
                "INSERT INTO integrations (org_id) VALUES (%s)",
                (org_id,)
            )
            
        logger.info(f"Successfully registered tenant {req.org_name} (org_id: {org_id})")
        return {"org_id": str(org_id), "status": "created"}
    except Exception as e:
        logger.error(f"Onboarding registration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Onboarding failed: {str(e)}")

@app.get("/campaigns")
async def get_campaigns(user: dict = Depends(get_current_user)):
    """Fetch all campaigns for the current authenticated tenant (Phase 6)."""
    if not pool:
        raise HTTPException(status_code=500, detail="Database connection not available")

    org_id = await get_org_id_for_user(user["sub"], pool)
    
    try:
        async with pool.connection() as conn:
            result = await conn.execute(
                "SELECT * FROM public.marketing_campaigns WHERE org_id = %s ORDER BY created_at DESC",
                (org_id,)
            )
            rows = await result.fetchall()
            return {"campaigns": [dict(r) for r in rows]}
    except Exception as e:
        logger.error(f"Failed to fetch campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/settings/integrations")
async def get_integrations(user: dict = Depends(get_current_user)):
    """Fetch active integration states and agent details for settings view (Phase 6)."""
    if not pool:
        raise HTTPException(status_code=500, detail="Database connection not available")

    org_id = await get_org_id_for_user(user["sub"], pool)
    
    try:
        async with pool.connection() as conn:
            t_res = await conn.execute(
                "SELECT org_name, agent_name, backstory, tone_instructions, schema_def FROM tenants WHERE org_id = %s",
                (org_id,)
            )
            tenant = await t_res.fetchone()
            
            i_res = await conn.execute(
                "SELECT gmail_access_token, slack_bot_token FROM integrations WHERE org_id = %s",
                (org_id,)
            )
            integration = await i_res.fetchone()
            
        return {
            "agent_name": tenant["agent_name"] if tenant else "Ralph",
            "org_name": tenant["org_name"] if tenant else "BandhanAI",
            "backstory": tenant["backstory"] if tenant else "",
            "tone_instructions": tenant["tone_instructions"] if tenant else "",
            "schema_def": tenant["schema_def"] if tenant else None,
            "integrations": {
                "gmail": bool(integration and integration.get("gmail_access_token")),
                "slack": bool(integration and integration.get("slack_bot_token"))
            }
        }
    except Exception as e:
        logger.error(f"Failed to fetch integration settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def get_root():
    return {"message": "Bandhan AI WebSocket & REST Server", "websocket_url": "/ws/{session_id}"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
        "active_sessions": len(manager.agent_sessions),
        "timestamp": datetime.now().isoformat()
    }

# Mount static files safely at the very end
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

if __name__ == "__main__":
    import sys
    from pathlib import Path
    # Ensure backend package is in python path
    sys.path.append(str(Path(__file__).parent.parent))
    sys.path.append(str(Path(__file__).parent))
    
    import uvicorn
    # Determine the correct import string based on current path / execution environment
    try:
        import backend.frontend
        app_import = "backend.frontend:app"
    except ImportError:
        app_import = "frontend:app"

    uvicorn.run(
        app_import,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
