"""
Celery task that triggers the LangGraph incident case workflow.
"""

import asyncio

from app.worker import celery_app


@celery_app.task(name="run_incident_workflow", bind=True, max_retries=2)
def run_incident_workflow(self, incident_id: str):
    """
    Entry point: queued by FastAPI after an incident is confirmed.
    Runs the LangGraph incident case supervisor.
    """
    from app.workflows.incident_case import run_incident_case

    try:
        result = asyncio.run(run_incident_case(incident_id))
        return {
            "status": "complete",
            "incident_id": incident_id,
            "findings_count": len(result.get("findings", [])),
            "actions_proposed": len(result.get("action_plan_draft", [])),
        }
    except Exception as exc:
        self.retry(exc=exc, countdown=30)
