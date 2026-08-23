"""
Validator — deterministic Python node.

Validates:
1. Pydantic schema compliance (all required fields present)
2. Citation verification (citations reference real playbook source_ids or findings)
3. Priority/owner field correctness
4. No unsupported claims
5. Reasonable action count

If invalid: allows one bounded repair pass, then routes to human review.
"""


VALID_PRIORITIES = {"Urgent", "Important", "Routine"}


async def validator_agent(state: dict) -> dict:
    """
    Validate the action plan draft with citation cross-referencing.

    No LLM — purely deterministic validation.
    """
    action_plan = state.get("action_plan_draft", [])
    playbook_citations = state.get("playbook_citations", [])
    findings = state.get("findings", [])
    errors = []

    if not action_plan:
        return {
            **state,
            "validation_result": {"status": "no_plan", "errors": ["No action plan was generated"]},
            "is_valid": False,
            "needs_human_review": True,
        }

    # Build a set of valid citation sources for cross-referencing
    valid_sources = set()

    # From playbook citations
    for cite in playbook_citations:
        valid_sources.add(cite.get("document", "").lower())
        valid_sources.add(cite.get("section", "").lower())
        # Full reference
        valid_sources.add(f"{cite.get('document', '')} / {cite.get('section', '')}".lower())

    # From findings
    for finding in findings:
        if finding.get("cite"):
            valid_sources.add(finding["cite"].lower())
        if finding.get("title"):
            valid_sources.add(finding["title"].lower())

    # Add common evidence references
    valid_sources.add("evidence checklist")
    valid_sources.add("pattern analysis")
    valid_sources.add("incident record")

    citation_verification_results = []

    for i, action in enumerate(action_plan):
        prefix = f"Action {i + 1}"

        # 1. Check required fields
        if not action.get("title"):
            errors.append(f"{prefix}: missing title")
        if not action.get("owner"):
            errors.append(f"{prefix}: missing owner")
        if not action.get("priority"):
            errors.append(f"{prefix}: missing priority")
        elif action["priority"] not in VALID_PRIORITIES:
            errors.append(f"{prefix}: invalid priority '{action['priority']}' (must be Urgent/Important/Routine)")
        if not action.get("due_description"):
            errors.append(f"{prefix}: missing due timeframe")
        if not action.get("required_proof"):
            errors.append(f"{prefix}: missing required proof description")

        # 2. Citation verification
        citation = action.get("citation", "")
        if not citation:
            errors.append(f"{prefix}: missing citation — every action must cite its source")
            citation_verification_results.append({"action": i + 1, "status": "missing"})
        else:
            # Check if the citation references a known source
            citation_lower = citation.lower()
            # Remove common prefixes like "Source: "
            citation_clean = citation_lower.replace("source:", "").strip()

            is_grounded = any(
                source in citation_clean or citation_clean in source
                for source in valid_sources
                if len(source) > 3  # Skip very short matches
            )

            if is_grounded:
                citation_verification_results.append({
                    "action": i + 1,
                    "status": "verified",
                    "citation": citation,
                })
            else:
                # Not a hard error — the LLM may paraphrase sources
                # But flag it for human review
                citation_verification_results.append({
                    "action": i + 1,
                    "status": "unverified",
                    "citation": citation,
                    "note": "Citation does not directly match a retrieved source. Human should verify.",
                })

    # 3. Check reasonable action count
    if len(action_plan) > 6:
        errors.append("Too many actions proposed (max 6). Prioritize the most critical.")

    # 4. Check for unverified citations (warning, not hard failure)
    unverified_citations = [r for r in citation_verification_results if r["status"] == "unverified"]

    is_valid = len(errors) == 0
    has_unverified = len(unverified_citations) > 0

    validation_result = {
        "status": "valid" if is_valid else "invalid",
        "errors": errors,
        "action_count": len(action_plan),
        "citation_verification": citation_verification_results,
        "all_citations_verified": not has_unverified,
        "checked_fields": ["title", "owner", "priority", "due_description", "required_proof", "citation"],
        "valid_sources_count": len(valid_sources),
    }

    return {
        **state,
        "validation_result": validation_result,
        "is_valid": is_valid,
        # Always needs human review per product rules,
        # but especially if citations are unverified
        "needs_human_review": True,
    }
