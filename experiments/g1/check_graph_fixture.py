"""Check the G1 draft graph schema against synthetic inputs only."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


def main() -> None:
    directory = Path(__file__).resolve().parent
    schema = json.loads((directory / "graph-gold-draft.schema.json").read_text(encoding="utf-8"))
    rows = json.loads((directory / "graph-gold-fixture.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    checker = Draft202012Validator.FORMAT_CHECKER
    if "date-time" not in checker.checkers:
        raise RuntimeError("install rfc3339-validator to check date-time fields")
    validator = Draft202012Validator(schema, format_checker=checker)
    for row in rows:
        validator.validate(row)
    structural, normative = rows
    invalid = [
        {key: value for key, value in structural.items() if key != "target_id"},
        {**structural, "type": "excepted_by"},
        {**structural, "review_state": "verified", "reviewer": "fixture", "review_ref": "fixture"},
        {**normative, "recorded": {"from": "2026-11-26T12:00:00", "until": None}},
        {key: value for key, value in normative.items() if key != "ambiguity_ref"},
    ]
    for index, row in enumerate(invalid, start=1):
        try:
            validator.validate(row)
        except ValidationError:
            continue
        raise RuntimeError(f"invalid synthetic case {index} was accepted")
    print(f"PASS: {len(rows)} synthetic graph records accepted; {len(invalid)} invalid records rejected")


if __name__ == "__main__":
    main()
