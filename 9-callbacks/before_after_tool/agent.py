"""
Before and After Tool Callbacks Example

This example demonstrates using tool callbacks to modify tool behavior.
"""

import copy
from typing import Any, Dict, Optional

from google.adk.agents import LlmAgent
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext


def get_capital_city(country: str) -> Dict[str, str]:
    """
    Retrieves the capital city of a given country.

    Args:
        country: Name of the country

    Returns:
        Dictionary with the capital city result
    """
    print(f"[TOOL] Executing get_capital_city tool with country: {country}")

    country_capitals = {
        "united states": "Washington, D.C.",
        "usa": "Washington, D.C.",
        "canada": "Ottawa",
        "france": "Paris",
        "germany": "Berlin",
        "japan": "Tokyo",
        "brazil": "Brasília",
        "australia": "Canberra",
        "india": "New Delhi",
    }

    result = country_capitals.get(country.lower(), f"Capital not found for {country}")
    print(f"[TOOL] Result: {result}")
    print(f"[TOOL] Returning: {{'result': '{result}'}}")

    return {"result": result}


def before_tool_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """
    Simple callback that modifies tool arguments or skips the tool call.
    """
    tool_name = tool.name
    print(f"[Callback] Before tool call for '{tool_name}'")
    print(f"[Callback] Original args: {args}")

    if tool_name == "get_capital_city" and args.get("country", "").lower() == "merica":
        print("[Callback] Converting 'Merica to 'United States'")
        args["country"] = "United States"
        print(f"[Callback] Modified args: {args}")
        return None

    if (
        tool_name == "get_capital_city"
        and args.get("country", "").lower() == "restricted"
    ):
        print("[Callback] Blocking restricted country")
        return {"result": "Access to this information has been restricted."}

    print("[Callback] Proceeding with normal tool call")
    return None


def after_tool_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> Optional[Dict]:
    """
    Simple callback that modifies the tool response after execution.
    """
    tool_name = tool.name
    print(f"[Callback] After tool call for '{tool_name}'")
    print(f"[Callback] Args used: {args}")
    print(f"[Callback] Original response: {tool_response}")

    original_result = tool_response.get("result", "")
    print(f"[Callback] Extracted result: '{original_result}'")

    if tool_name == "get_capital_city" and "washington" in original_result.lower():
        print("[Callback] DETECTED USA CAPITAL - adding patriotic note!")

        modified_response = copy.deepcopy(tool_response)
        modified_response["result"] = (
            f"{original_result} (Note: This is the capital of the USA. 🇺🇸)"
        )
        modified_response["note_added_by_callback"] = True

        print(f"[Callback] Modified response: {modified_response}")
        return modified_response

    print("[Callback] No modifications needed, returning original response")
    return None


root_agent = LlmAgent(
    name="tool_callback_agent",
    model="gemini-2.0-flash",
    description="An agent that demonstrates tool callbacks by looking up capital cities",
    instruction="""
    You are a helpful geography assistant.
    
    Your job is to:
    - Find capital cities when asked using the get_capital_city tool
    - Use the exact country name provided by the user
    - ALWAYS return the EXACT result from the tool, without changing it
    - When reporting a capital, display it EXACTLY as returned by the tool
    
    Examples:
    - "What is the capital of France?" → Use get_capital_city with country="France"
    - "Tell me the capital city of Japan" → Use get_capital_city with country="Japan"
    """,
    tools=[get_capital_city],
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
)
