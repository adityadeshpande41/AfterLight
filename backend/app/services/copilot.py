"""
Risk Copilot — A grounded chat agent with guardrails.

Architecture:
1. Input guardrails (off-topic detection, safety, scope)
2. Semantic cache lookup (pgvector)
3. ReAct agent with SQL + RAG tools
4. Output guardrails (no claims beyond data, citations required)
5. Cache eligible responses
"""

import json
import time
from typing import Any

from openai import OpenAI

from app.config import settings
from app.services.copilot_cache import SemanticCache
from app.services.copilot_guardrails import GuardrailResult, check_guardrails
from app.workflows.tools.rag_tools import RAG_TOOL_FUNCTIONS, RAG_TOOLS
from app.workflows.tools.sql_tools import SQL_TOOL_FUNCTIONS, SQL_TOOLS


SYSTEM_PROMPT = """You are the Afterlight Risk Copilot — a grounded assistant for venue managers.

IDENTITY:
- You help venue managers understand their operational risk data
- You answer questions about incidents, evidence, scores, actions, and patterns
- You cite your sources (playbook sections, incident records, evidence items)

RULES:
1. ONLY answer questions about the venue's operational risk data
2. NEVER make up data — only report what the tools return
3. NEVER give legal advice, medical advice, or insurance opinions
4. NEVER blame individuals or determine fault
5. If you don't have enough data, say so — don't speculate
6. Always cite the source of your information
7. Keep answers concise and actionable
8. Suggest concrete next steps when relevant

TOOLS:
You have SQL tools to query the venue's database and RAG tools to search approved playbooks.
Use them to ground every claim in real data.

RESPONSE FORMAT:
Provide your response as JSON:
{
    "answer": "your natural language response",
    "citations": [{"source": "document/table name", "section": "specific section", "content_preview": "brief quote"}],
    "suggested_actions": [{"title": "what to do next", "link": "/venue/relevant-page"}]
}"""

MAX_TOOL_CALLS = 5


class CopilotAgent:
    def __init__(self, venue_id: str):
        self.venue_id = venue_id
        self.venue_uuid = self._resolve_venue_id(venue_id)
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.cache = SemanticCache(venue_id=venue_id)

    def _resolve_venue_id(self, venue_id: str) -> str:
        """Resolve a slug or UUID to the actual UUID string."""
        if len(venue_id) == 36 and "-" in venue_id:
            return venue_id  # Already a UUID
        # Look up by slug
        from sqlalchemy import create_engine, text
        from app.sync_db import SYNC_URL
        engine = create_engine(SYNC_URL)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id FROM venues WHERE slug = :slug"),
                {"slug": venue_id},
            )
            row = result.fetchone()
        engine.dispose()
        if row:
            return str(row[0])
        return venue_id  # Fallback

    async def answer(self, question: str) -> dict[str, Any]:
        """Full pipeline: guardrails → cache → agent → output guardrails → cache store."""

        # 1. Input guardrails
        guardrail_result = check_guardrails(question)
        if guardrail_result.blocked:
            return {
                "answer": guardrail_result.response,
                "citations": [],
                "suggested_actions": [],
                "is_cached": False,
                "guardrail_triggered": True,
                "guardrail_reason": guardrail_result.reason,
            }

        # 2. Semantic cache lookup
        cached = await self.cache.lookup(question)
        if cached:
            return {
                **cached,
                "is_cached": True,
                "guardrail_triggered": False,
                "guardrail_reason": None,
            }

        # 3. Run the ReAct agent
        agent_result = self._run_agent(question)

        # 4. Output guardrails (check the response doesn't violate rules)
        agent_result = self._apply_output_guardrails(agent_result)

        # 5. Cache eligible responses
        if self._is_cacheable(question, agent_result):
            await self.cache.store(question, agent_result)

        return {
            **agent_result,
            "is_cached": False,
            "guardrail_triggered": False,
            "guardrail_reason": None,
        }

    def _run_agent(self, question: str) -> dict:
        """ReAct loop: LLM decides what tools to call, then composes answer."""
        all_tools = SQL_TOOLS + RAG_TOOLS
        all_tool_functions = {**SQL_TOOL_FUNCTIONS, **RAG_TOOL_FUNCTIONS}

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Venue ID: {self.venue_uuid}\n\nQuestion: {question}"},
        ]

        tool_calls_made = 0

        while tool_calls_made < MAX_TOOL_CALLS:
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                tools=all_tools,
                tool_choice="auto",
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            message = response.choices[0].message

            # If no tool calls, parse the final answer
            if not message.tool_calls:
                return self._parse_response(message.content or "")

            messages.append(message)

            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                # Inject venue_id if the tool expects it but it's not provided
                if "venue_id" in str(SQL_TOOLS) and "venue_id" not in arguments:
                    if function_name in SQL_TOOL_FUNCTIONS:
                        arguments["venue_id"] = self.venue_uuid

                if function_name in all_tool_functions:
                    try:
                        result_str = all_tool_functions[function_name](**arguments)
                    except Exception as e:
                        result_str = json.dumps({"error": str(e)})
                else:
                    result_str = json.dumps({"error": f"Unknown tool: {function_name}"})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_str if isinstance(result_str, str) else json.dumps(result_str),
                })
                tool_calls_made += 1

        # If we exhausted tool calls, try to get a final answer
        response = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return self._parse_response(response.choices[0].message.content or "")

    def _parse_response(self, content: str) -> dict:
        """Parse the LLM's JSON response into our format."""
        try:
            parsed = json.loads(content)
            return {
                "answer": parsed.get("answer", content),
                "citations": parsed.get("citations", []),
                "suggested_actions": parsed.get("suggested_actions", []),
            }
        except json.JSONDecodeError:
            return {
                "answer": content,
                "citations": [],
                "suggested_actions": [],
            }

    def _apply_output_guardrails(self, result: dict) -> dict:
        """Post-processing guardrails on the agent's response."""
        answer = result.get("answer", "")

        # Block responses that make definitive legal/fault claims
        forbidden_phrases = [
            "is liable", "is at fault", "should sue",
            "file a claim", "you are entitled",
            "definitely", "I guarantee",
        ]
        for phrase in forbidden_phrases:
            if phrase.lower() in answer.lower():
                result["answer"] = (
                    "I can help you understand the documented facts, but I can't make "
                    "legal determinations or assign fault. Would you like me to summarize "
                    "what the record shows instead?"
                )
                result["citations"] = []
                result["suggested_actions"] = [
                    {"title": "View incident record", "link": "/venue/incidents"}
                ]
                break

        return result

    def _is_cacheable(self, question: str, result: dict) -> bool:
        """Determine if this response should be cached."""
        # Don't cache:
        # - Questions about real-time or very recent events
        # - Drafting/action requests
        # - Very short answers (probably errors)
        non_cacheable_signals = [
            "right now", "just happened", "create", "submit",
            "approve", "reject", "upload",
        ]
        if any(signal in question.lower() for signal in non_cacheable_signals):
            return False
        if len(result.get("answer", "")) < 50:
            return False
        return True
