"""Orchestration: validated request → property facts → analysis (spec §6 request flow)."""

import time
from typing import Any, Dict, Optional

from .analysis import Fact, PropertyFacts, build_analysis, missing_required
from .errors import AmbiguousMatch, InsufficientData, PropertyNotFound
from .provider import Candidate, PropertyProvider
from .validation import AnalysisRequest, parse_request


def _manual_facts(req: AnalysisRequest) -> PropertyFacts:
    p = req.property

    def user(value: Any) -> Optional[Fact]:
        return None if value is None else Fact(value, "user", "You entered this")

    return PropertyFacts(
        address=user(req.address),
        price=user(p.purchase_price),
        beds=user(p.beds),
        state=user(p.state),
        hoa_monthly=user(p.hoa_monthly),
    )


def run_analysis(
    payload: Any, provider: PropertyProvider, budget_s: float = 15.0
) -> Dict[str, Any]:
    req = parse_request(payload)
    deadline = time.monotonic() + budget_s

    if req.property is not None:
        facts = _manual_facts(req)
    else:
        if req.candidate_id:
            candidate = Candidate(id=req.candidate_id, display=req.address)
        else:
            candidates = provider.search(req.address, deadline)
            if not candidates:
                raise PropertyNotFound()
            if len(candidates) > 1:
                raise AmbiguousMatch([c.to_dict() for c in candidates])
            candidate = candidates[0]
        facts = provider.get_property(candidate, deadline)

    missing = missing_required(facts)
    if missing:
        raise InsufficientData(
            "The data source did not provide: " + ", ".join(missing) + ". "
            "Enter the price, bedrooms, and state to continue.",
            missing=missing,
            manual_entry_required=True,
        )
    return {"success": True, "analysis": build_analysis(req, facts)}
