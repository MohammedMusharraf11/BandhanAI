"""
Graph builder for Ralph marketing automation agent.
This file creates and compiles the complete LangGraph for LangGraph Studio.
"""

from typing import Annotated, List, TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from config import mcp_config
from nodes import (
    create_assistant_node_with_llm,
    human_tool_review_node,
    assistant_router
)


class AgentState(TypedDict):
    """
    The state of the Ralph marketing automation agent.
    
    Attributes:
        messages: The list of messages in the conversation
        protected_tools: List of tools that require human approval
        yolo_mode: Whether to skip human review of protected tool calls
    """
    messages: Annotated[List[BaseMessage], add_messages]
    protected_tools: List[str]
    yolo_mode: bool


def build_graph():
    """
    Build and compile the Ralph agent graph for LangGraph Studio.
    
    Returns:
        Compiled StateGraph ready for use in LangGraph Studio
    """
    
    # Initialize MCP client and get tools
    print("Initializing MCP client...")
    client = MultiServerMCPClient(connections=mcp_config["mcpServers"])
    
    # For LangGraph Studio, we need to handle async operations differently
    # Get tools synchronously or handle the async call properly
    try:
        import asyncio
        # Try to get existing event loop or create new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we can't use asyncio.run()
                # This is a common issue in LangGraph Studio
                import nest_asyncio
                nest_asyncio.apply()
                tools = loop.run_until_complete(client.get_tools())
            else:
                tools = asyncio.run(client.get_tools())
        except RuntimeError:
            # No event loop exists, create one
            tools = asyncio.run(client.get_tools())
    except Exception as e:
        print(f"Error getting tools: {e}")
        # Fallback to empty tools list for now
        tools = []
    
    print(f"Loaded {len(tools)} tools from MCP servers")

    # Initialize LLM with tools
    print("Initializing LLM...")
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.1
    )
    
    # Only bind tools if we have them
    if tools:
        llm = llm.bind_tools(tools)

    # Create the graph builder
    print("Building graph structure...")
    builder = StateGraph(AgentState)

    # Create and add nodes
    assistant_node_func = create_assistant_node_with_llm(llm)
    
    builder.add_node("assistant_node", assistant_node_func)
    builder.add_node("human_tool_review_node", human_tool_review_node)
    
    # Always add tools node, even if empty - this prevents the edge error
    if tools:
        builder.add_node("tools", ToolNode(tools))
    else:
        # Create a dummy tools node that just returns the state unchanged
        def dummy_tools_node(state):
            return state
        builder.add_node("tools", dummy_tools_node)

    # Add edges
    builder.add_edge(START, "assistant_node")
    
    # Always use the same routing structure
    builder.add_conditional_edges(
        "assistant_node",
        assistant_router,
        {
            "tools": "tools",
            "human_tool_review_node": "human_tool_review_node",
            "END": END
        }
    )
    
    # Tools always go back to assistant
    builder.add_edge("tools", "assistant_node")
    
    # Human review can go to tools or back to assistant
    builder.add_edge("human_tool_review_node", "tools")

    # Compile the graph with memory checkpoint
    print("Compiling graph...")
    compiled_graph = builder.compile(checkpointer=MemorySaver())
    
    print("Graph compiled successfully!")
    return compiled_graph


# This is the key change - LangGraph Studio expects a non-async function
# Remove the async from the original function and handle async operations inside
graph = build_graph


def print_graph_info():
    """Print information about the graph structure."""
    print("=== Ralph Marketing Agent Graph ===")
    print("Nodes:")
    print("  - assistant_node: Main LLM processing")
    print("  - human_tool_review_node: Human approval for protected tools")
    print("  - tools: Execute approved tool calls")
    print("\nProtected Tools (require approval):")
    print("  - create_campaign")
    print("  - send_campaign_email")
    print("\nEdge Flow:")
    print("  START -> assistant_node")
    print("  assistant_node -> [tools | human_tool_review_node | END]")
    print("  tools -> assistant_node")
    print("  human_tool_review_node -> tools")


if __name__ == "__main__":
    print("Testing Ralph Agent Graph Build...")
    try:
        compiled_graph = build_graph()
        print("\n✅ Graph built and compiled successfully!")
        print_graph_info()
        
        # Test basic graph structure
        graph_dict = compiled_graph.get_graph()
        print(f"\nGraph has {len(graph_dict.nodes)} nodes and {len(graph_dict.edges)} edges")
        
    except Exception as e:
        print(f"\n❌ Error building graph: {e}")
        import traceback
        traceback.print_exc()