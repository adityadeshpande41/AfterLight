"""
Agent trace — records every step each agent takes during a workflow run.

Each trace entry captures:
- Which agent ran
- What tools it called (with arguments)
- What results it got back
- How long it took
- The final output it produced

The full trace is returned in the API response and stored for the Console's "Agent runs" view.
"""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """A single tool invocation by an agent."""

    tool_name: str
    arguments: dict
    result_summary: str  # Truncated result for display
    duration_ms: int = 0


@dataclass
class AgentStep:
    """One agent's complete execution trace."""

    agent_name: str
    started_at: float = 0
    finished_at: float = 0
    duration_ms: int = 0
    tool_calls: list[ToolCall] = field(default_factory=list)
    output_summary: str = ""
    error: str | None = None


@dataclass
class WorkflowTrace:
    """Full trace of a workflow run across all agents."""

    workflow_id: str = ""
    incident_id: str = ""
    steps: list[AgentStep] = field(default_factory=list)
    total_duration_ms: int = 0
    total_tool_calls: int = 0
    total_llm_calls: int = 0

    def start_agent(self, agent_name: str) -> AgentStep:
        step = AgentStep(agent_name=agent_name, started_at=time.time())
        self.steps.append(step)
        return step

    def finish_agent(self, step: AgentStep, output_summary: str = ""):
        step.finished_at = time.time()
        step.duration_ms = int((step.finished_at - step.started_at) * 1000)
        step.output_summary = output_summary

    def add_tool_call(self, step: AgentStep, tool_name: str, arguments: dict, result: str, duration_ms: int = 0):
        # Truncate result for readability
        result_summary = result[:300] + "..." if len(result) > 300 else result
        step.tool_calls.append(ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            result_summary=result_summary,
            duration_ms=duration_ms,
        ))
        self.total_tool_calls += 1

    def to_dict(self) -> dict:
        self.total_duration_ms = sum(s.duration_ms for s in self.steps)
        return {
            "workflow_id": self.workflow_id,
            "incident_id": self.incident_id,
            "total_duration_ms": self.total_duration_ms,
            "total_tool_calls": self.total_tool_calls,
            "total_llm_calls": self.total_llm_calls,
            "steps": [
                {
                    "agent_name": s.agent_name,
                    "duration_ms": s.duration_ms,
                    "tool_calls": [
                        {
                            "tool_name": tc.tool_name,
                            "arguments": tc.arguments,
                            "result_summary": tc.result_summary,
                            "duration_ms": tc.duration_ms,
                        }
                        for tc in s.tool_calls
                    ],
                    "output_summary": s.output_summary,
                    "error": s.error,
                }
                for s in self.steps
            ],
        }
