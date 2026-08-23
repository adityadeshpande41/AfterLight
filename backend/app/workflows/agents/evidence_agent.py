"""
Evidence Agent — deterministic evidence completeness assessment.

No LLM needed. Uses rules to check what's required vs what's present.
"""

from typing import Any


# Required evidence types by incident type
REQUIRED_EVIDENCE = {
    "Injury": [
        {"kind": "Photo", "label_contains": "condition", "urgency": "high"},
        {"kind": "Video", "label_contains": "camera", "urgency": "urgent"},
        {"kind": "Statement", "label_contains": "witness", "urgency": "high"},
        {"kind": "Document", "label_contains": "ems", "urgency": "medium"},
    ],
    "Security": [
        {"kind": "Video", "label_contains": "camera", "urgency": "urgent"},
        {"kind": "Statement", "label_contains": "witness", "urgency": "high"},
        {"kind": "Document", "label_contains": "report", "urgency": "medium"},
    ],
    "Crowd management": [
        {"kind": "Video", "label_contains": "camera", "urgency": "high"},
        {"kind": "Document", "label_contains": "report", "urgency": "medium"},
    ],
    "Property damage": [
        {"kind": "Photo", "label_contains": "damage", "urgency": "high"},
        {"kind": "Document", "label_contains": "report", "urgency": "medium"},
    ],
}


async def evidence_agent(state: dict) -> dict:
    """
    Assess evidence completeness for the incident.

    Outputs:
    - evidence_assessment: completeness stats
    - findings: list of supported/gap findings
    """
    incident = state.get("incident")
    evidence_items = state.get("evidence_items", [])

    if not incident:
        return {**state, "errors": state.get("errors", []) + ["No incident data"]}

    # Tracing
    import time
    from app.workflows.tracing import WorkflowTrace
    trace: WorkflowTrace = state.get("_trace")
    trace_step = trace.start_agent("evidence_agent") if trace else None

    incident_type = incident.get("type", "Injury")
    requirements = REQUIRED_EVIDENCE.get(incident_type, REQUIRED_EVIDENCE["Injury"])

    findings = []
    missing_items = []
    verified_count = 0
    total_required = len(requirements)

    for req in requirements:
        # Check if any evidence item matches this requirement
        matched = None
        for item in evidence_items:
            if (
                item["kind"].lower() == req["kind"].lower()
                or req["label_contains"].lower() in item["label"].lower()
            ):
                matched = item
                break

        if matched:
            if matched["status"] == "Verified":
                verified_count += 1
                findings.append({
                    "status": "supported",
                    "title": f"{matched['label']} is verified",
                    "cite": f"{matched['kind']} · {matched['label']}",
                    "urgency": None,
                })
            elif matched["status"] == "Pending review":
                findings.append({
                    "status": "pending",
                    "title": f"{matched['label']} awaiting verification",
                    "cite": f"{matched['kind']} · {matched['label']}",
                    "urgency": req["urgency"],
                })
            else:
                findings.append({
                    "status": "gap",
                    "title": f"{matched['label']} is not yet preserved",
                    "cite": f"Evidence checklist · source missing",
                    "urgency": req["urgency"],
                })
                missing_items.append(matched["label"])
        else:
            findings.append({
                "status": "gap",
                "title": f"Missing: {req['kind']} evidence ({req['label_contains']})",
                "cite": "Evidence checklist · not attached",
                "urgency": req["urgency"],
            })
            missing_items.append(f"{req['kind']} ({req['label_contains']})")

    completeness_pct = (verified_count / total_required * 100) if total_required > 0 else 0

    evidence_assessment = {
        "completeness_pct": round(completeness_pct, 1),
        "verified_count": verified_count,
        "total_required": total_required,
        "missing_items": missing_items,
        "has_urgent_gaps": any(f["urgency"] == "urgent" for f in findings if f["status"] == "gap"),
    }

    # Finish trace
    if trace and trace_step:
        gaps = len([f for f in findings if f["status"] == "gap"])
        trace.finish_agent(trace_step, output_summary=f"{completeness_pct:.0f}% complete, {gaps} gaps found")

    return {
        **state,
        "evidence_assessment": evidence_assessment,
        "findings": findings,
    }
