"""
LangGraph workflow definitions for BandhanAI.

This module defines the agentic state machine that powers Ralph:
  - assistant_node: Invokes the LLM with system prompt + conversation history
  - human_tool_review_node: Human-in-the-loop interrupt for protected tools
  - tools (ToolNode): Executes MCP tool calls

The graph supports:
  - Per-tenant MCP configs (via mcp_config_override)
  - Per-tenant system prompts (via system_prompt)
  - Persistent checkpointing via AsyncPostgresSaver (or MemorySaver fallback)
"""

from typing import Annotated, List, Literal, TypedDict
from langchain_groq import ChatGroq
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    AIMessage,
    ToolMessage
)
from langgraph.types import Command, interrupt
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
import json


class AgentState(TypedDict):
    """The state of the agent.
    
    Attributes:
        messages: The list of messages in the conversation.
        protected_tools: Tool names that require human approval before execution.
        yolo_mode: Whether to skip human review of protected tool calls.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    protected_tools: List[str]
    yolo_mode: bool


async def create_mcp_client(mcp_config_override: dict = None):
    """
    Create a MultiServerMCPClient and load tools.
    
    Returns:
        tuple: (client, tools) — the MCP client and the list of tools.
    """
    if mcp_config_override:
        active_mcp_config = mcp_config_override
    else:
        from backend.config import mcp_config
        active_mcp_config = mcp_config

    servers = active_mcp_config.get("mcpServers", {})
    client = MultiServerMCPClient(servers)
    tools = await client.get_tools()
    return client, tools


async def build_graph(
    checkpointer=None,
    mcp_config_override: dict = None,
    system_prompt: str = None,
    tools=None,
):
    """
    Build the LangGraph application.
    
    Args:
        checkpointer: LangGraph checkpointer instance (AsyncPostgresSaver for production,
                       MemorySaver fallback for dev/CLI). Defaults to MemorySaver if None.
        mcp_config_override: Per-tenant MCP config dict. If None, falls back to the
                              static mcp_config from config.py. Ignored if tools is provided.
        system_prompt: Per-tenant system prompt string. If None, falls back to the
                        default ralph_system_prompt.
        tools: Pre-loaded list of tools. If provided, skips MCP client creation.
    
    Returns:
        Compiled LangGraph StateGraph ready for streaming.
    """
    # Resolve system prompt
    if system_prompt is None:
        from backend.prompts import ralph_system_prompt
        active_prompt = ralph_system_prompt
    else:
        active_prompt = system_prompt

    # If tools not provided, create MCP client inline (for CLI usage)
    _inline_client = None
    if tools is None:
        _inline_client, tools = await create_mcp_client(mcp_config_override)

    # Initialize LLM with tools
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.1
    ).bind_tools(tools)

    # --- Graph Nodes ---

    def assistant_node(state: AgentState):
        """Invoke the LLM with the system prompt and conversation history."""
        response = llm.invoke(
            [SystemMessage(content=active_prompt)] +
            state["messages"]
        )
        return {"messages": [response]}
    
    def human_tool_review_node(state: AgentState) -> Command[Literal["assistant_node", "tools"]]:
        """
        Human-in-the-loop review node.
        
        Interrupts execution and waits for user to:
          - 'continue': Approve and execute the tool call as-is
          - 'update': Modify the tool call arguments before execution
          - 'feedback': Reject with a reason, sent back to the LLM
        """
        last_message = state["messages"][-1]
        tool_call = last_message.tool_calls[-1]

        human_review: dict = interrupt({
            "message": "Your input is required for the following tool:",
            "tool_call": tool_call
        })

        review_action = human_review["action"]
        review_data = human_review.get("data")

        if review_action == "continue":
            return Command(goto="tools")
        
        elif review_action == "update":
            updated_message = AIMessage(
                content=last_message.content,
                tool_calls=[{
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "args": json.loads(review_data)
                }],
                id=last_message.id
            )
            return Command(goto="tools", update={"messages": [updated_message]})
        
        elif review_action == "feedback":
            tool_message = ToolMessage(
                content=review_data,
                name=tool_call["name"],
                tool_call_id=tool_call["id"]
            )
            return Command(goto="assistant_node", update={"messages": [tool_message]})

    # --- Routing Logic ---

    def assistant_router(state: AgentState) -> str:
        """Route after assistant response: END if no tool calls, else tools or review."""
        last_message = state["messages"][-1]
        if not last_message.tool_calls:
            return END
        else:
            if not state.get("yolo_mode", False):
                protected = state.get("protected_tools", ["create_campaign", "send_campaign_email"])
                if any(
                    tool_call["name"] in protected
                    for tool_call in last_message.tool_calls
                ):
                    return "human_tool_review_node"
            return "tools"

    # --- Build Graph ---

    builder = StateGraph(AgentState)

    builder.add_node(assistant_node)
    builder.add_node(human_tool_review_node)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "assistant_node")
    builder.add_conditional_edges(
        "assistant_node",
        assistant_router,
        ["tools", "human_tool_review_node", END],
    )
    builder.add_edge("tools", "assistant_node")

    # Use provided checkpointer or fall back to in-memory
    if checkpointer is None:
        checkpointer = MemorySaver()

    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Graph Visualization Utilities (CLI only)
# ---------------------------------------------------------------------------

def inspect_graph_cli(graph, output_file="graph.png"):
    """Visualize the graph and save as PNG file for CLI usage."""
    try:
        png_data = graph.get_graph(xray=True).draw_mermaid_png()
        with open(output_file, "wb") as f:
            f.write(png_data)
        
        print(f"Graph visualization saved to {output_file}")
        
        import subprocess
        import sys
        
        try:
            if sys.platform.startswith('darwin'):
                subprocess.run(['open', output_file])
            elif sys.platform.startswith('win'):
                subprocess.run(['start', output_file], shell=True)
            elif sys.platform.startswith('linux'):
                subprocess.run(['xdg-open', output_file])
            print(f"Opened {output_file} with system default viewer")
        except Exception as e:
            print(f"Could not auto-open file: {e}")
            
    except Exception as e:
        print(f"Error generating graph visualization: {e}")


def inspect_graph_text(graph):
    """Print a text representation of the graph structure."""
    print("=== Graph Structure ===")
    print("Nodes:", list(graph.get_graph().nodes()))
    print("Edges:", list(graph.get_graph().edges()))
    
    try:
        graph_dict = graph.get_graph(xray=True).to_dict()
        print("\n=== Detailed Graph Info ===")
        for key, value in graph_dict.items():
            if key != 'edges':
                print(f"{key}: {value}")
    except Exception as e:
        print(f"Could not get detailed graph info: {e}")


if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()

    graph = asyncio.run(build_graph())
    inspect_graph_cli(graph)
    inspect_graph_text(graph)
