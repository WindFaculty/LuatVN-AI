import unittest
from dataclasses import replace
from datetime import UTC, date, datetime

from luatvn_ai_evaluation.review_pilot import PilotCase, ReviewRecord, summarize


TIME = datetime(2026, 11, 26, tzinfo=UTC)
CASE = PilotCase("case-a", "r1", "group-a", "CIV", "lookup", "low", "fixture", date(2026, 1, 1),
                 TIME, "snapshot", "synthetic-rights", ("anchor-a",), ("family-a",), "scenario-a", None, "L2")
REVIEW = ReviewRecord("case-a", "r1", "fixture-reviewer", "fixture", "L2", "pass", TIME, "synthetic-log",
                      None, 7, 3, 0, True)


class G1ReviewTest(unittest.TestCase):
    def test_counts_verified_and_preserves_missing_review_effort(self):
        result = summarize([CASE], [REVIEW])
        self.assertEqual(result["states"], {"L2": 1})
        self.assertEqual(result["effort"]["L2"]["active_p90"], 7)
        self.assertIsNone(result["effort"]["L3"]["active_p90"])
        self.assertEqual(summarize([replace(CASE, required_tier="L3")], [REVIEW])["states"], {"PENDING_L3": 1})
        self.assertEqual(summarize([CASE], [replace(REVIEW, adjudicated=False)])["states"], {"NEEDS_REVIEW": 1})

    def test_shared_family_scenario_or_translation_cannot_cross_groups(self):
        second = replace(CASE, case_id="case-b", family_ids=("family-b",), scenario_id="scenario-b", group_id="group-b")
        for fields in ({"family_ids": CASE.family_ids}, {"scenario_id": CASE.scenario_id}, {"translation_of": CASE.case_id}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                summarize([CASE, replace(second, **fields)], [])
        self.assertEqual(summarize([CASE, replace(second, group_id=CASE.group_id, translation_of=CASE.case_id)], [])
                         ["groups"], 1)

    def test_l3_requires_independence_and_credential_record(self):
        l3_case = replace(CASE, required_tier="L3")
        l3_review = replace(REVIEW, tier="L3", reviewer_id="fixture-expert", credential_ref="synthetic-credential")
        self.assertEqual(summarize([l3_case], [REVIEW, l3_review])["states"], {"L3": 1})
        for bad in (replace(l3_review, reviewer_id=REVIEW.reviewer_id), replace(l3_review, credential_ref=None),
                    replace(l3_review, revision="old"), replace(l3_review, active_minutes=float("nan"))):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                summarize([l3_case], [REVIEW, bad])
