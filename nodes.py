"""
Node functions for the Ralph marketing automation agent.
Contains all the individual node logic separated for better organization.
"""

from typing import Literal
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langgraph.types import Command, interrupt
from prompts import ralph_system_prompt
import json


def assistant_node(state, llm_with_tools):
    """
    Main assistant node that processes user input and generates responses.
    
    Args:
        state: Current agent state
        llm_with_tools: LLM instance bound with tools
        
    Returns:
        Updated state with new message
    """
    response = llm_with_tools.invoke(
        [SystemMessage(content=ralph_system_prompt)] + state["messages"]
    )
    return {"messages": [response]}


def human_tool_review_node(state) -> Command[Literal["assistant_node", "tools"]]:
    """
    Human review node for protected tool calls.
    Handles approval, updates, and feedback for sensitive operations.
    
    Args:
        state: Current agent state
        
    Returns:
        Command directing to next node based on human input
    """
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[-1]

    # Interrupt execution to get human input
    human_review: dict = interrupt({
        "message": "Your input is required for the following tool:",
        "tool_call": tool_call,
        "tool_name": tool_call["name"],
        "tool_args": tool_call["args"]
    })

    review_action = human_review.get("action", "continue")
    review_data = human_review.get("data")

    if review_action == "continue":
        return Command(goto="tools")
    
    elif review_action == "update":
        # Update the tool call arguments with human modifications
        try:
            updated_args = json.loads(review_data) if isinstance(review_data, str) else review_data
        except json.JSONDecodeError:
            updated_args = review_data
            
        updated_message = AIMessage(
            content=last_message.content,
            tool_calls=[{
                "id": tool_call["id"],
                "name": tool_call["name"],
                "args": updated_args
            }],
            id=last_message.id
        )
        return Command(goto="tools", update={"messages": [updated_message]})
    
    elif review_action == "feedback":
        # Send feedback to the agent as a tool message
        tool_message = ToolMessage(
            content=review_data or "Human provided feedback instead of executing tool",
            name=tool_call["name"],
            tool_call_id=tool_call["id"]
        )
        return Command(goto="assistant_node", update={"messages": [tool_message]})
    
    else:
        # Default to continue if action is unclear
        return Command(goto="tools")


def assistant_router(state) -> str:
    """
    Router function to determine the next node after assistant processes input.
    
    Args:
        state: Current agent state
        
    Returns:
        Name of next node to execute
    """
    last_message = state["messages"][-1]
    
    # If no tool calls, end the conversation
    if not last_message.tool_calls:
        return "END"
    
    # Check if we need human approval for protected tools
    if not state.get("yolo_mode", False):
        protected_tools = state.get("protected_tools", ["create_campaign", "send_campaign_email"])
        
        for tool_call in last_message.tool_calls:
            if tool_call["name"] in protected_tools:
                return "human_tool_review_node"
    
    # Direct to tools if no human approval needed
    return "tools"


def create_assistant_node_with_llm(llm_with_tools):
    """
    Factory function to create an assistant node with bound LLM.
    
    Args:
        llm_with_tools: LLM instance with tools bound
        
    Returns:
        Assistant node function
    """
    def node_function(state):
        return assistant_node(state, llm_with_tools)
    
    return node_function