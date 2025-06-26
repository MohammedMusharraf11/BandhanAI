from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio
import json
import logging
import uuid
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

# Import your existing modules
from graph import build_graph, AgentState
from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.types import Command

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Bandhan AI WebSocket API", version="1.0.0")

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_sessions: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        # Initialize agent session
        self.agent_sessions[session_id] = {
            "graph": await build_graph(),
            "config": {
                "configurable": {"thread_id": session_id},
                "recursion_limit": 100
            },
            "yolo_mode": True,
            "created_at": datetime.now()
        }
        logger.info(f"WebSocket connected for session: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.agent_sessions:
            del self.agent_sessions[session_id]
        logger.info(f"WebSocket disconnected for session: {session_id}")

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {e}")
                self.disconnect(session_id)

    async def broadcast(self, message: dict):
        disconnected = []
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {session_id}: {e}")
                disconnected.append(session_id)
        
        for session_id in disconnected:
            self.disconnect(session_id)

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
                graph_input = AgentState(
                    messages=[HumanMessage(content=input_data.get("message", ""))],
                    yolo_mode=session["yolo_mode"]
                )

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
                            # Send any buffered message content first
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
                            
                            # Send chunk to client for real-time streaming
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
            # Stop typing indicator on error
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
            
            # Resume the agent with the approval response
            resume_input = {
                "resume": {
                    "action": action,
                    "data": data
                }
            }
            
            # Continue streaming with the resume command
            await self.stream_agent_responses(session_id, resume_input)
            
        except Exception as e:
            logger.error(f"Error handling approval response: {e}")
            await self.manager.send_message(session_id, {
                "type": "error",
                "message": f"Approval handling error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })

# Initialize the handler
websocket_handler = BandhanAIWebSocketHandler(manager)

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        # Send initial greeting
        await manager.send_message(session_id, {
            "type": "message",
            "content": "Hello! I'm Bandhan AI, your CRM assistant. How can I help you today?",
            "is_complete": True,
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            message_type = message_data.get("type", "message")
            
            if message_type == "message":
                # Handle regular chat message
                user_message = message_data.get("content", "")
                if user_message.strip():
                    # Echo user message back (optional)
                    await manager.send_message(session_id, {
                        "type": "user_message",
                        "content": user_message,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Process with agent
                    await websocket_handler.stream_agent_responses(
                        session_id, 
                        {"message": user_message}
                    )
            
            elif message_type == "approval_response":
                # Handle approval response
                await websocket_handler.handle_approval_response(
                    session_id, 
                    message_data
                )
            
            elif message_type == "ping":
                # Handle ping/keepalive
                await manager.send_message(session_id, {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
            
            else:
                logger.warning(f"Unknown message type: {message_type}")

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        manager.disconnect(session_id)

@app.get("/")
async def get_root():
    """Serve the chat interface"""
    # You can serve your HTML file here or redirect to static files
    return {"message": "Bandhan AI WebSocket Server", "websocket_url": "/ws/{session_id}"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
        "active_sessions": len(manager.agent_sessions),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/sessions")
async def get_active_sessions():
    """Get information about active sessions"""
    sessions_info = {}
    for session_id, session_data in manager.agent_sessions.items():
        sessions_info[session_id] = {
            "created_at": session_data["created_at"].isoformat(),
            "yolo_mode": session_data["yolo_mode"],
            "connected": session_id in manager.active_connections
        }
    
    return {
        "active_sessions": sessions_info,
        "total_sessions": len(sessions_info)
    }

# Optional: Serve static files (your HTML frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "server:app",  # Change this to match your filename
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )