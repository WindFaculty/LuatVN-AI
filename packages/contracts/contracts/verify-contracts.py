import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError


HERE = Path(__file__).resolve().parent
ID = "6ee86364-3a35-456a-930b-cf1c4f37861b"
DATE = "2025-05-05"
TIME = DATE + "T00:00:00Z"


def check_internal():
    schema = json.loads((HERE / "internal-v1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    envelope = dict(id=ID, correlation_id=ID, producer="fixture", environment="testing", occurred_at=TIME)

    def evidence_query(**original):
        payload = dict(
            query_vi="Quy định nào áp dụng?", legal_as_of=DATE, recorded_as_of=TIME,
            snapshot_id=ID, scope_ref="fixture-scope", filters={"verified_only": True}, top_k=5,
        )
        return dict(envelope, type="EvidenceQuery.v1", transport="query", deadline_at=TIME,
                    payload=dict(payload, **original))

    validator.validate(evidence_query())
    validator.validate(evidence_query(query_original="Which rule applies?", query_language="en"))
    assert not validator.is_valid(evidence_query(query_original="Which rule applies?"))
    assert not validator.is_valid(evidence_query(query_language="en"))
    assert not validator.is_valid(evidence_query(query_original="test", query_language="fr"))

    metric = dict(
        denominator=50, independent_groups=50, numerator=49, observed=0.98,
        evidence_ref="fixture-evidence", ci=dict(ci_low=0.89, ci_high=1, ci_method="wilson"),
    )
    metric_ids = [
        "AC-06", "citation_coverage", "false_abstention", "useful_answer_rate",
        "graph_precision", "graph_coverage", "extraction_cer",
    ]
    gate = dict(
        gate="G5", manifest_digest="sha256:" + "a" * 64, dataset_digest="sha256:" + "b" * 64,
        scope={"level": "global", "mode": "standard"}, status="PASS", independent_groups=50,
        s0_count=0, s1_count=0, metrics=[dict(metric, metric_id=name) for name in metric_ids],
        report_ref="fixture-report",
    )

    def gate_report(payload):
        return dict(envelope, type="GateReport.v1", transport="event", aggregate_revision=1, payload=payload)

    validator.validate(gate_report(gate))
    validator.validate(gate_report(dict(gate, status="FAIL", s0_count=1, s1_count=2)))
    for severity in ("s0_count", "s1_count"):
        assert not validator.is_valid(gate_report(dict(gate, **{severity: 1}))), severity
        old_gate = {key: value for key, value in gate.items() if key != severity}
        assert not validator.is_valid(gate_report(dict(old_gate, critical_failures=0))), severity
    assert not validator.is_valid(gate_report(dict(gate, metrics=[dict(metric, metric_id="unknown")])))
    incomplete_ci = dict(metric, metric_id="AC-06", ci={"ci_low": 0.89})
    assert not validator.is_valid(gate_report(dict(gate, metrics=[incomplete_ci])))


def check_answers(models):
    api = yaml.safe_load((HERE / "answers.openapi.yaml").read_text(encoding="utf-8"))

    def validator(ref):
        schema = {"$ref": ref, "components": api["components"]}
        return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)

    def check(api_validator, model, payload, valid=True):
        assert api_validator.is_valid(payload) == valid, (model.__name__, payload)
        try:
            model.model_validate_json(json.dumps(payload))
        except ValidationError:
            assert not valid, (model.__name__, payload)
        else:
            assert valid, (model.__name__, payload)

    answer_validator = validator("#/components/schemas/AnswerResult")
    run_validator = validator("#/components/schemas/RunState")
    claim = dict(claim_id=ID, text="Fixture claim.", verification="verified", evidence_ids=[ID])
    evidence = dict(
        evidence_id=ID, provision_id=ID, version_id=ID, quote="Fixture quote.",
        url="https://example.test/fixture", anchor="Article 1", source_revision="fixture",
        validity=dict(valid_from=DATE, valid_to=None),
    )
    answer = dict(
        answer_id=ID, request_id=ID, snapshot_id=ID, mode="advanced", language="en",
        legal_as_of=DATE, recorded_as_of=TIME, facts=[], assumptions=[], missing_facts=[],
        limitations=[], expert_review_required=False, status="verified", summary="Fixture summary.",
        claims=[claim], evidence=[evidence], risks=[],
    )
    for status in ("verified", "partial"):
        payload = dict(answer, status=status)
        check(answer_validator, models.AnswerResult, payload)
        check(run_validator, models.RunState, payload)
    for status in ("needs_facts", "insufficient_evidence", "policy_denied", "canceled", "failed"):
        payload = dict(answer, status=status, summary=None, claims=[], evidence=[])
        check(answer_validator, models.AnswerResult, payload)
        check(run_validator, models.RunState, payload)
    for status in ("queued", "running", "cancelling"):
        check(run_validator, models.RunState, dict(answer_id=ID, status=status))
    for invalid in (
        dict(answer, summary=""), dict(answer, claims=[]), dict(answer, evidence=[]),
        dict(answer, status="failed"), dict(answer, status="failed", summary=None, claims=[], evidence=[], risks=["x"]),
    ):
        check(answer_validator, models.AnswerResult, invalid, valid=False)
    assert not answer_validator.is_valid(dict(answer, internal_debug="x"))

    responses = api["paths"]["/v1/answers/{id}/events"]["get"]["responses"]
    stream = responses["200"]["content"]["text/event-stream"]
    assert stream["schema"]["type"] == "string"
    frame_validator = validator(stream["x-frame-data-schema"])
    progress = dict(type="answer.progress", answer_id=ID, status="started", stage="planning")
    completed = dict(type="answer.completed", answer_id=ID, result=answer)
    for cursor, data in enumerate((progress, completed), 1):
        frame = f"id: {cursor}\nevent: {data['type']}\ndata: {json.dumps(data)}\n\n"
        _, event, encoded_data = frame.strip().splitlines()
        decoded_data = json.loads(encoded_data.removeprefix("data: "))
        assert event.removeprefix("event: ") == decoded_data["type"]
        check(frame_validator, models.SseData, decoded_data)
    check(frame_validator, models.SseData, dict(completed, result=dict(answer, claims=[])), valid=False)

    error_response = api["components"]["responses"]["InternalError"]
    error_json = error_response["content"]["application/json"]
    error_validator = Draft202012Validator(dict(error_json["schema"], components=api["components"]))
    error_payload = error_json["example"]
    error_validator.validate(error_payload)
    models.Error.model_validate_json(json.dumps(error_payload))
    assert not error_validator.is_valid(dict(error_payload, code="dependency_unavailable"))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python verify-contracts.py <directory containing answer_models.py>")
    sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
    import answer_models

    check_internal()
    check_answers(answer_models)
    print("PASS: Internal schema, Answer OpenAPI, generated Pydantic models and SSE fixtures")
