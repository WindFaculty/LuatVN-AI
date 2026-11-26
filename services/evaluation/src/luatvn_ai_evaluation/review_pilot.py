"""G1 pilot record validation and descriptive summaries."""

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from statistics import mean, median


DOMAINS = ("CIV", "CRI", "ADM", "LAB", "LND", "BUS", "TRA", "EDU", "ENV")


@dataclass(frozen=True)
class PilotCase:
    case_id: str
    revision: str
    group_id: str
    primary_domain: str
    task: str
    risk: str
    scope: str
    legal_on: date
    recorded_at: datetime
    snapshot: str
    rights_ref: str
    anchor_refs: tuple[str, ...]
    family_ids: tuple[str, ...]
    scenario_id: str
    translation_of: str | None
    required_tier: str


@dataclass(frozen=True)
class ReviewRecord:
    case_id: str
    revision: str
    reviewer_id: str
    reviewer_role: str
    tier: str
    verdict: str
    reviewed_at: datetime
    evidence_ref: str
    credential_ref: str | None
    active_minutes: float
    wait_minutes: float
    adjudication_minutes: float
    adjudicated: bool


def _filled(values) -> bool:
    return all(isinstance(value, str) and value.strip() for value in values)


def summarize(cases: list[PilotCase], final_reviews: list[ReviewRecord]) -> dict:
    """Consume current cases and at most one resolved record per case/tier from the owner log."""
    by_id = {}
    group_domains = {}
    group_by_lineage = {}
    for case in cases:
        if (case.case_id in by_id or case.primary_domain not in DOMAINS or case.required_tier not in {"L2", "L3"}
                or case.recorded_at.utcoffset() is None or not case.anchor_refs or not case.family_ids
                or not _filled((case.case_id, case.revision, case.group_id, case.task, case.risk, case.scope,
                                case.snapshot, case.rights_ref, case.scenario_id, *case.anchor_refs, *case.family_ids))):
            raise ValueError("invalid or duplicate current case")
        by_id[case.case_id] = case
        if group_domains.setdefault(case.group_id, case.primary_domain) != case.primary_domain:
            raise ValueError("group has multiple primary domains")
        lineage = [("scenario", case.scenario_id), *(("family", family) for family in case.family_ids)]
        for key in lineage:
            if group_by_lineage.setdefault(key, case.group_id) != case.group_id:
                raise ValueError("connected cases must use the same group")

    for case in cases:
        if case.translation_of is not None:
            original = by_id.get(case.translation_of)
            if original is None or original.case_id == case.case_id or original.group_id != case.group_id:
                raise ValueError("translation must share the original's group")

    by_case = defaultdict(dict)
    records_by_tier = defaultdict(list)
    for review in final_reviews:
        case = by_id.get(review.case_id)
        if (case is None or review.revision != case.revision or review.tier not in {"L2", "L3"}
                or review.tier in by_case[review.case_id] or review.verdict not in {"pass", "reject", "needs_clarification"}
                or review.reviewed_at.utcoffset() is None or review.reviewed_at < case.recorded_at
                or not _filled((review.reviewer_id, review.reviewer_role, review.evidence_ref))
                or not all(type(value) in {int, float} and math.isfinite(value) and value >= 0 for value in (
                    review.active_minutes, review.wait_minutes, review.adjudication_minutes))
                or review.active_minutes == 0 or type(review.adjudicated) is not bool
                or (review.tier == "L3" and not _filled((review.credential_ref,)))):
            raise ValueError("invalid, duplicate, or stale human review record")
        by_case[review.case_id][review.tier] = review
        records_by_tier[review.tier].append(review)

    states = Counter()
    strata = Counter((case.primary_domain, case.task, case.risk) for case in cases)
    for case in cases:
        reviews = by_case[case.case_id]
        if reviews.get("L2") and reviews.get("L3") and reviews["L2"].reviewer_id == reviews["L3"].reviewer_id:
            raise ValueError("L3 reviewer must be independent of the L2 reviewer")
        sufficient = reviews.get("L3") or reviews.get(case.required_tier)
        if any(record.verdict != "pass" or not record.adjudicated for record in reviews.values()):
            states["NEEDS_REVIEW"] += 1
        elif sufficient:
            states[sufficient.tier] += 1
        else:
            states[f"PENDING_{case.required_tier}"] += 1

    effort = {}
    for tier in ("L2", "L3"):
        records = records_by_tier[tier]
        times = sorted(record.active_minutes for record in records)
        effort[tier] = {
            "n": len(times), "active_mean": mean(times) if times else None,
            "active_median": median(times) if times else None,
            "active_p90": times[math.ceil(0.9 * len(times)) - 1] if times else None,
            "reviews_per_active_hour": 60 * len(times) / sum(times) if times else None,
            "wait_minutes": sum(record.wait_minutes for record in records) if records else None,
            "adjudication_minutes": sum(record.adjudication_minutes for record in records) if records else None,
        }
    required_l3 = sum(case.required_tier == "L3" for case in cases)
    return {
        "cases": len(cases), "groups": len(group_domains),
        "groups_by_domain": dict(Counter(group_domains.values())), "states": dict(states),
        "cases_by_stratum": [{"domain": d, "task": t, "risk": r, "count": n}
                             for (d, t, r), n in sorted(strata.items())],
        "required_l3": required_l3, "required_l3_ratio": required_l3 / len(cases) if cases else None,
        "pending_ratio": (1 - (states["L2"] + states["L3"]) / len(cases)) if cases else None,
        "effort": effort,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True, help="G1 pilot case records as a JSON array")
    parser.add_argument("--reviews", type=Path, help="Resolved human review records as a JSON array")
    parser.add_argument("--output", type=Path, required=True, help="Path for the descriptive summary")
    args = parser.parse_args()

    cases = [
        PilotCase(**{
            **row,
            "legal_on": date.fromisoformat(row["legal_on"]),
            "recorded_at": datetime.fromisoformat(row["recorded_at"]),
        })
        for row in json.loads(args.cases.read_text(encoding="utf-8"))
    ]
    reviews = []
    if args.reviews is not None:
        reviews = [
            ReviewRecord(**{**row, "reviewed_at": datetime.fromisoformat(row["reviewed_at"])})
            for row in json.loads(args.reviews.read_text(encoding="utf-8"))
        ]
    report = summarize(cases, reviews)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
