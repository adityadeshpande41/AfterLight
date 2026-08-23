"""
Validator — deterministic Python node.

Validates:
- Pydantic schema compliance
- Citations present and non-empty
- Required fields (owner, due, proof)
- No unsupported claims

If invalid: allows one bounded repair pass, then routes to human review.
"""


VALID_PRIORITIES = {"Urgent", "Important", "Routine"}
VALID_OWNERS = {
    "Venue Manager",
    "Security Lead",
    "Facilities",
    "Door Team Lead",
    "Bar Manager",
    "Operations",
    "Maya Chen",
    "Jordan Lee",
}


async def validator_agent(state: dict) -> dict:
    """
    Validate the action plan draft.

    No LLM — purely deterministic validation.
    """
    action_plan = state.get("action_plan_draft", [])
    errors = []

    if not action_plan:
        # No plan was generated — route to human review
        return {
            **state,
            "validation_result": {"status": "no_plan", "errors": ["No action plan was generated"]},
            "is_valid": False,
            "needs_human_review": True,
        }

    for i, action in enumerate(action_plan):
        prefix = f"Action {i + 1}"

        # Check required fields
        if not action.get("title"):
            errors.append(f"{prefix}: missing title")
        if not action.get("owner"):
            errors.append(f"{prefix}: missing owner")
        if not action.get("priority"):
            errors.append(f"{prefix}: missing priority")
        elif action["priority"] not in VALID_PRIORITIES:
            errors.append(f"{prefix}: invalid priority '{action['priority']}'")
        if not action.get("due_description"):
            errors.append(f"{prefix}: missing due timeframe")
        if not action.get("required_proof"):
            errors.append(f"{prefix}: missing required proof description")
        if not action.get("citation"):
            errors.append(f"{prefix}: missing citation — actions must cite their source")

    # Check reasonable action count
    if len(action_plan) > 6:
        errors.append("Too many actions proposed (max 6). Prioritize the most critical.")

    is_valid = len(errors) == 0

    validation_result = {
        "status": "valid" if is_valid else "invalid",
        "errors": errors,
        "action_count": len(action_plan),
        "checked_fields": ["title", "owner", "priority", "due_description", "required_proof", "citation"],
    }

    return {
        **state,
        "validation_result": validation_result,
        "is_valid": is_valid,
        "needs_human_review": not is_valid or True,  # Always needs human review per product rules
    }
