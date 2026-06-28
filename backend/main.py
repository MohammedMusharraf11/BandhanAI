import sys
from pathlib import Path

# Add project root and backend dir to sys.path to ensure absolute/relative imports work seamlessly
project_root = str(Path(__file__).resolve().parent.parent)
backend_dir = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.graph import build_graph, AgentState
from langchain_core.messages import AIMessageChunk, HumanMessage
from typing import AsyncGenerator, Any
from langgraph.graph import StateGraph
from langgraph.types import Command
import json
import asyncio
import logging
logging.getLogger().setLevel(logging.ERROR)




async def stream_graph_responses(
        input: dict[str, Any],
        graph: StateGraph,
        **kwargs
        ) -> AsyncGenerator[str, None]:
    """Asynchronously stream the result of the graph run.

    Args:
        input: The input to the graph.
        graph: The compiled graph.
        **kwargs: Additional keyword arguments.

    Returns:
        str: The final LLM or tool call response
    """
    async for message_chunk, metadata in graph.astream(
        input=input,
        stream_mode="messages",
        **kwargs
        ):
        if isinstance(message_chunk, AIMessageChunk):
            if message_chunk.response_metadata:
                finish_reason = message_chunk.response_metadata.get("finish_reason", "")
                if finish_reason == "tool_calls":
                    yield "\n\n"

            if message_chunk.tool_call_chunks:
                tool_chunk = message_chunk.tool_call_chunks[0]

                tool_name = tool_chunk.get("name", "")
                args = tool_chunk.get("args", "")

                if tool_name:
                    tool_call_str = f"\n\n< TOOL CALL: {tool_name} >\n\n"
                if args:
                    tool_call_str = args

                yield tool_call_str
            else:
                yield message_chunk.content
            continue


async def main():
    try:
        graph = await build_graph()

        config = {
            "configurable": {
                "thread_id": "1"
            },
            "recursion_limit": 100
        }
        yolo_mode = True

        graph_input = {
            "messages": [
                HumanMessage(content="Briefly introduce yourself and offer to help me.")
            ],
            "yolo_mode": yolo_mode,
        }

        while True:
            print(f" ---- 🤖 Assistant ---- \n")
            async for response in stream_graph_responses(graph_input, graph, config=config):
                print(response, end="", flush=True)

            thread_state = graph.get_state(config=config)

            while thread_state.interrupts:
                # if interrupt, collect input and handle resume
                for interrupt in thread_state.interrupts:
                    print("\n ----- ✅ / ❌ Human Approval Required ----- \n")
                    interrupt_json_str = json.dumps(interrupt.value, indent=2, ensure_ascii=False)
                    print(interrupt_json_str)
                    print("\n Please specify whether you want to continue, update, or provide feedback.")

                    action = input("Action (continue, update, feedback): ")
                    while action not in ["continue", "update", "feedback"]:
                        print("Invalid action. Please try again.")
                        action = input("Action (continue, update, feedback): ")

                    if action == "continue":
                        data=None
                    else:
                        data = input("Data: ")

                    print(f" ----- 🤖 Assistant ----- \n")
                    async for response in stream_graph_responses(Command(resume={"action": action, "data": data}), graph, config=config):
                        print(response, end="", flush=True)

                    thread_state = graph.get_state(config=config)

            user_input = input("User: ")
            if user_input.lower() in ["exit", "quit"]:
                print("\n\nExit command received. Exiting...\n\n")
                break
            graph_input = {
                "messages": [
                    HumanMessage(content=user_input)
                ],
                "yolo_mode": yolo_mode,
            }

            print(f"\n\n ----- 🥷 Human ----- \n\n{user_input}\n")

    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)}")
        raise


if __name__ == "__main__":
    import sys
    import uvicorn
    import nest_asyncio
    
    # Check if CLI mode is requested
    if "--cli" in sys.argv:
        nest_asyncio.apply()
        asyncio.run(main())
    else:
        # Default to starting the FastAPI server
        print("Starting Bandhan AI Multi-Tenant FastAPI Server...")
        print("Pass --cli to run the interactive CLI agent loop instead.")
        
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

