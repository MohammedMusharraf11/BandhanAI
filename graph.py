from pydantic import BaseModel
from typing import Annotated, List, Literal
from langchain_google_genai import ChatGoogleGenerativeAI
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
from config import mcp_config
from prompts import ralph_system_prompt
import json


class  AgentState(BaseModel):
    """The state of the agent.
    
    Attributes:
        messages: The list of messages in the conversation.
        yolo_mode: Whether to skip human review of protected tool calls.
    """
    messages: Annotated[List[BaseMessage], add_messages] = []
    protected_tools: List[str] = ["create_campaign", "send_campaign_email"]
    yolo_mode: bool = False


async def build_graph():
    """
    Build the LangGraph application.
    """
    client = MultiServerMCPClient(connections=mcp_config["mcpServers"])
    tools = await client.get_tools()

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.1
    ).bind_tools(tools)

    def assistant_node(state: AgentState) -> AgentState:
        response = llm.invoke(
            [SystemMessage(content=ralph_system_prompt)] +
            state.messages
            )
        state.messages = state.messages + [response]
        return state
    
    def human_tool_review_node(state: AgentState) -> Command[Literal["assistant_node", "tools"]]:
        last_message = state.messages[-1]
        tool_call = last_message.tool_calls[-1]

        human_review: dict = interrupt({
            "message": "Your input is required for the following tool:",
            "tool_call": tool_call
        })

        review_action = human_review["action"]
        review_data = human_review.get("data")

        if review_action == "continue":
            return Command(goto="tools")
        
        # Change the tool call arguments created by our Agent
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
        
        # Send feedback to the Agent as a tool message (required after a tool call)
        elif review_action == "feedback":
            
            tool_message = ToolMessage(
                content=review_data,
                name=tool_call["name"],
                tool_call_id=tool_call["id"]
            )
            return Command(goto="assistant_node", update={"messages": [tool_message]})


    def assistant_router(state: AgentState) -> str:
        last_message = state.messages[-1]
        if not last_message.tool_calls:
            return END
        else:
            if not state.yolo_mode:
                if any(tool_call["name"] in state.protected_tools for tool_call in last_message.tool_calls):
                    return "human_tool_review_node"
            return "tools"

    builder = StateGraph(AgentState)

    builder.add_node(assistant_node)
    builder.add_node(human_tool_review_node)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "assistant_node")
    builder.add_conditional_edges("assistant_node", assistant_router, ["tools", "human_tool_review_node", END])
    builder.add_edge("tools", "assistant_node")

    return builder.compile(checkpointer=MemorySaver())


def inspect_graph_cli(graph, output_file="graph.png"):
    """
    Visualize the graph and save as PNG file for CLI usage.
    """
    try:
        # Get the mermaid PNG data
        png_data = graph.get_graph(xray=True).draw_mermaid_png()
        
        # Save to file
        with open(output_file, "wb") as f:
            f.write(png_data)
        
        print(f"Graph visualization saved to {output_file}")
        print(f"Open the file with your preferred image viewer")
        
        # Optionally try to open with system default viewer
        import subprocess
        import sys
        
        try:
            if sys.platform.startswith('darwin'):  # macOS
                subprocess.run(['open', output_file])
            elif sys.platform.startswith('win'):   # Windows
                subprocess.run(['start', output_file], shell=True)
            elif sys.platform.startswith('linux'): # Linux
                subprocess.run(['xdg-open', output_file])
            print(f"Opened {output_file} with system default viewer")
        except Exception as e:
            print(f"Could not auto-open file: {e}")
            print(f"Please manually open {output_file}")
            
    except Exception as e:
        print(f"Error generating graph visualization: {e}")


def inspect_graph_text(graph):
    """
    Print a text representation of the graph structure.
    """
    print("=== Graph Structure ===")
    print("Nodes:", list(graph.get_graph().nodes()))
    print("Edges:", list(graph.get_graph().edges()))
    
    # Print more detailed structure if available
    try:
        graph_dict = graph.get_graph(xray=True).to_dict()
        print("\n=== Detailed Graph Info ===")
        for key, value in graph_dict.items():
            if key != 'edges':  # edges can be verbose
                print(f"{key}: {value}")
    except Exception as e:
        print(f"Could not get detailed graph info: {e}")


if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()

    graph = asyncio.run(build_graph())
    
    # Save visualization as PNG
    inspect_graph_cli(graph)
    
    # Also print text representation
    inspect_graph_text(graph)
