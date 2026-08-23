"""
Pattern Agent — ReAct-style agent with SQL tools.

This agent DECIDES what queries to run based on the incident context.
It uses OpenAI function calling to invoke SQL tools, observes results,
and synthesizes a pattern analysis.
"""

import json

from openai import OpenAI

from app.config import settings
from app.workflows.tools.sql_tools import SQL_TOOL_FUNCTIONS, SQL_TOOLS

SYSTEM_PROMPT = """You are the Pattern Agent for Afterlight, a risk-intelligence platform for nightlife venues.

Your job: Analyze incident patterns for a venue by querying the database. You have SQL tools available.

Strategy:
1. First, query all recent incidents for the venue to understand frequency.
2. If the current incident has a specific location, query incidents at that location to check for repeats.
3. Check time-of-day patterns — nightlife incidents often cluster between 11 PM and 3 AM.
4. Check action completion stats to understand if the venue closes out corrective actions.

After gathering data, synthesize your findings into a structured pattern analysis.

Output your final analysis as a JSON object:
{
    "pattern_detected": true/false,
    "incidents_30d": number,
    "incidents_60d": number,
    "total_incidents": number,
    "trend": "increasing" | "stable" | "decreasing",
    "top_location": "location name or null",
    "location_repeat_count": number,
    "night_cluster_count": number,
    "has_high_severity_recent": true/false,
    "supporting_incident_ids": ["INC-XXXX", ...],
    "summary": "human-readable pattern summary"
}"""


MAX_TOOL_CALLS = 6  # Safety limit


async def pattern_agent(state: dict) -> dict:
    """
    ReAct-style pattern analysis using OpenAI function calling + SQL tools.

    The agent decides what to query, observes results, and reasons about patterns.
    """
    incident = state.get("incident")
    venue = state.get("venue")

    if not incident or not venue:
        return {**state, "pattern_analysis": None}

    client = OpenAI(api_key=settings.openai_api_key)

    # Initial message with context
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""Analyze patterns for this incident:

Venue: {venue['name']} (ID: {venue['id']}, capacity: {venue['capacity']})
Incident: {incident['ref_code']} - {incident['title']}
Type: {incident['type']}, Severity: {incident['severity']}
Location: {incident['location']}
Time: {incident['occurred_at']}

Use your tools to query the database and build a pattern analysis.
When you have enough information, provide your final JSON analysis (no tool call)."""},
    ]

    tool_calls_made = 0

    # ReAct loop: let the agent call tools until it provides a final answer
    while tool_calls_made < MAX_TOOL_CALLS:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=SQL_TOOLS,
            tool_choice="auto",
            temperature=0.1,
        )

        message = response.choices[0].message

        # If no tool calls, the agent is providing its final answer
        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content})
            break

        # Process tool calls
        messages.append(message)  # Add assistant message with tool_calls

        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            # Execute the tool
            if function_name in SQL_TOOL_FUNCTIONS:
                try:
                    tool_result = SQL_TOOL_FUNCTIONS[function_name](**arguments)
                    result_str = json.dumps(tool_result, default=str)
                except Exception as e:
                    result_str = json.dumps({"error": str(e)})
            else:
                result_str = json.dumps({"error": f"Unknown tool: {function_name}"})

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_str,
            })
            tool_calls_made += 1

    # Parse the final response
    final_content = messages[-1].get("content", "") if isinstance(messages[-1], dict) else message.content

    try:
        # Extract JSON from the response
        if "```json" in final_content:
            json_str = final_content.split("```json")[1].split("```")[0]
        elif "{" in final_content:
            # Find the JSON object
            start = final_content.index("{")
            end = final_content.rindex("}") + 1
            json_str = final_content[start:end]
        else:
            json_str = final_content

        pattern_analysis = json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        # Fallback: return what we have
        pattern_analysis = {
            "pattern_detected": False,
            "incidents_30d": 0,
            "incidents_60d": 0,
            "total_incidents": 0,
            "trend": "unknown",
            "top_location": None,
            "location_repeat_count": 0,
            "night_cluster_count": 0,
            "has_high_severity_recent": False,
            "supporting_incident_ids": [],
            "summary": f"Agent analysis: {final_content[:200]}",
        }

    return {**state, "pattern_analysis": pattern_analysis}
