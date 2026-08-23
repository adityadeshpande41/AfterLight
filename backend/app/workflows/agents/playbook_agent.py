"""
Playbook Agent — ReAct-style agent with RAG tools.

This agent DECIDES what to search for in the playbook corpus.
It uses OpenAI function calling to invoke semantic search,
observes the results, and may search again with refined queries.

Returns cited excerpts only — does NOT make recommendations.
"""

import json

from openai import OpenAI

from app.config import settings
from app.workflows.tools.rag_tools import RAG_TOOL_FUNCTIONS, RAG_TOOLS

SYSTEM_PROMPT = """You are the Playbook Agent for Afterlight, a risk-intelligence platform for nightlife venues.

Your job: Search the approved playbook library to find guidance relevant to this incident.
You have a semantic search tool that queries embedded playbook documents.

Strategy:
1. Search for guidance related to the incident type and location.
2. If evidence gaps exist, search for evidence preservation protocols.
3. If patterns were detected, search for recurring incident procedures.
4. Search for response protocols matching the severity level.

You may call the search tool multiple times with different queries to gather comprehensive guidance.

IMPORTANT:
- You ONLY retrieve and cite playbook guidance
- You do NOT make recommendations — that's the Mitigation Agent's job
- Each result has a source_id — include these in your output for citation verification

After gathering relevant guidance, output a JSON array of citations:
[
    {
        "source_id": "uuid from search results",
        "document": "document title",
        "section": "section title",
        "content": "the relevant content",
        "relevance_score": 0.85,
        "search_query": "the query that found this"
    }
]"""

MAX_TOOL_CALLS = 5


async def playbook_agent(state: dict) -> dict:
    """
    ReAct-style playbook retrieval using OpenAI function calling + RAG tools.

    The agent decides what to search for, observes results, and may refine queries.
    """
    incident = state.get("incident")
    evidence_assessment = state.get("evidence_assessment")
    pattern_analysis = state.get("pattern_analysis")

    if not incident:
        return {**state, "playbook_citations": []}

    # Tracing
    from app.workflows.tracing import WorkflowTrace
    import time
    trace: WorkflowTrace = state.get("_trace")
    trace_step = trace.start_agent("playbook_agent") if trace else None

    client = OpenAI(api_key=settings.openai_api_key)

    # Build context for the agent
    context_parts = [
        f"Incident: {incident['ref_code']} - {incident['title']}",
        f"Type: {incident['type']}, Severity: {incident['severity']}",
        f"Location: {incident['location']}",
    ]
    if evidence_assessment:
        if evidence_assessment.get("missing_items"):
            context_parts.append(f"Missing evidence: {', '.join(evidence_assessment['missing_items'])}")
        if evidence_assessment.get("has_urgent_gaps"):
            context_parts.append("There are URGENT evidence gaps.")
    if pattern_analysis:
        if pattern_analysis.get("pattern_detected"):
            context_parts.append(f"Pattern detected: {pattern_analysis.get('summary', '')}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""Find relevant playbook guidance for this situation:

{chr(10).join(context_parts)}

Search the playbook library for applicable protocols and procedures.
Make multiple searches to cover: incident response, evidence preservation, and any pattern-specific guidance.
When done, provide your final JSON array of citations."""},
    ]

    tool_calls_made = 0
    all_citations = []

    while tool_calls_made < MAX_TOOL_CALLS:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=RAG_TOOLS,
            tool_choice="auto",
            temperature=0.1,
        )

        message = response.choices[0].message

        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content})
            break

        messages.append(message)

        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            tool_start = time.time()
            if function_name in RAG_TOOL_FUNCTIONS:
                try:
                    tool_result_str = RAG_TOOL_FUNCTIONS[function_name](**arguments)
                    tool_result = json.loads(tool_result_str)
                    # Collect citations as they come in
                    for r in tool_result:
                        r["search_query"] = arguments.get("query", "")
                        if r["source_id"] not in [c["source_id"] for c in all_citations]:
                            all_citations.append(r)
                    result_str = tool_result_str
                except Exception as e:
                    result_str = json.dumps({"error": str(e)})
            else:
                result_str = json.dumps({"error": f"Unknown tool: {function_name}"})
            tool_duration = int((time.time() - tool_start) * 1000)

            # Record in trace
            if trace and trace_step:
                trace.add_tool_call(trace_step, function_name, arguments, result_str, tool_duration)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_str,
            })
            tool_calls_made += 1

    # Finish trace
    if trace and trace_step:
        trace.finish_agent(trace_step, output_summary=f"{len(all_citations)} playbook citations retrieved")
        trace.total_llm_calls += tool_calls_made + 1

    # Deduplicate and return all gathered citations
    # Sort by relevance score
    all_citations.sort(key=lambda c: c.get("relevance_score", 0), reverse=True)

    return {
        **state,
        "playbook_citations": all_citations[:8],  # Cap at 8 most relevant
    }
