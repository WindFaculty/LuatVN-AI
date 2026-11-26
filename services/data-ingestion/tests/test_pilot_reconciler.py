import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from luatvn_ai_data_ingestion.pilot_reconciler import (
    G1_D02_TARGETS,
    build_qa_fixture,
    detect_conflicts,
    main,
    reconcile_pilot_data,
    select_g1_d02_pilot_samples,
    verify_reconciliation_invariants,
)
from luatvn_ai_data_ingestion.pilot_schema import (
    PILOT_DOMAINS,
    RunCutoff,
    record_execution_log,
    redact_sensitive_text,
    sha256_bytes,
)
from luatvn_ai_data_ingestion.source_rights import ACTIONS

CUTOFF = RunCutoff(
    run_id="TEST-RUN",
    cutoff_utc="2026-11-26T12:58:39Z",
    cutoff_vn="2026-11-26T19:58:39+07:00",
)


def catalog(
    *,
    source_id="SRC-01",
    source_record_id="rec-1",
    issuer="CHÍNH PHỦ",
    document_type="Nghị định",
    document_number="78/2025/NĐ-CP",
    title="Nghị định mẫu",
    issued_date="01/04/2025",
    gazette_published_date="03/04/2025",
    observed_effective_date="01/06/2025",
    gazette_issue="649+650",
    gazette_page="1-52",
    continuation_issues=None,
    version="1",
    relation_role="signed_original",
    related_to_document_number="",
    domain="ADM",
    is_pre_2020_reference=False,
    page_url=None,
    legal_status_verified=False,
    error="",
    status="CATALOGUED",
    **extra,
):
    return {
        "source_id": source_id,
        "source_record_id": source_record_id,
        "partition_id": extra.pop("partition_id", f"{source_id}__2025"),
        "data_origin": extra.pop("data_origin", "SYNTHETIC_FIXTURE"),
        "page_url": page_url or f"https://fixture.test/{source_id.lower()}/{source_record_id}.htm",
        "year": 2025,
        "quarter": "Q2",
        "observed_at": CUTOFF.cutoff_utc,
        "gazette_issue": gazette_issue,
        "gazette_page": gazette_page,
        "continuation_issues": list(continuation_issues or []),
        "issuer": issuer,
        "document_type": document_type,
        "document_number": document_number,
        "title": title,
        "issued_date": issued_date,
        "gazette_published_date": gazette_published_date,
        "observed_effective_date": observed_effective_date,
        "version": version,
        "relation_role": relation_role,
        "related_to_document_number": related_to_document_number,
        "domain_candidate": domain,
        "rights_ref": "TEST-RIGHTS",
        "status": status,
        "date_reconciliation_flag": "",
        "is_pre_2020_reference": is_pre_2020_reference,
        "eligible_for_pilot_denominator": False,
        "legal_status_verified": legal_status_verified,
        "error": error,
        "cutoff_utc": CUTOFF.cutoff_utc,
        "cutoff_vn": CUTOFF.cutoff_vn,
        **extra,
    }


def artifact(
    *,
    source_id="SRC-01",
    source_record_id="att-1",
    parent_id="rec-1",
    attachment_id="a1",
    document_number="78/2025/NĐ-CP",
    file_url="https://fixture.test/files/a1.pdf",
    file_type="pdf_text",
    relation_role="signed_original",
    version="1",
    domain="ADM",
    sha256=None,
    payload=None,
    status="STORED",
    quarantine_reason="",
    size_bytes=None,
    error="",
    **extra,
):
    payload = payload if payload is not None else f"%PDF-1.4\n%{attachment_id}\n%%EOF\n".encode()
    return {
        "source_id": source_id,
        "source_record_id": source_record_id,
        "partition_id": extra.pop("partition_id", f"{source_id}__2025"),
        "data_origin": extra.pop("data_origin", "SYNTHETIC_FIXTURE"),
        "parent_id": parent_id,
        "attachment_id": attachment_id,
        "page_url": extra.pop(
            "page_url", f"https://fixture.test/{source_id.lower()}/{parent_id}.htm"
        ),
        "file_url": file_url,
        "year": 2025,
        "quarter": "Q2",
        "observed_at": CUTOFF.cutoff_utc,
        "gazette_issue": "",
        "gazette_page": "",
        "document_number": document_number,
        "version": version,
        "relation_role": relation_role,
        "file_type": file_type,
        "declared_mime": extra.pop("declared_mime", "application/pdf"),
        "detected_mime": extra.pop("detected_mime", "application/pdf"),
        "size_bytes": len(payload) if size_bytes is None else size_bytes,
        "sha256": sha256 or sha256_bytes(payload),
        "stored_blob_path": "",
        "rights_ref": "TEST-RIGHTS",
        "status": status,
        "quarantine_reason": quarantine_reason,
        "error": error,
        "cutoff_utc": CUTOFF.cutoff_utc,
        "cutoff_vn": CUTOFF.cutoff_vn,
        **extra,
    }


def rights(source_id, status):
    return [
        {"source_id": source_id, "action": action, "status": status, "rights_ref": "TEST"}
        for action in sorted(ACTIONS)
    ]


class ReconcilerIdentityTest(unittest.TestCase):
    def test_cross_source_family_and_blob_dedup_keep_every_url(self):
        left = catalog(
            source_id="SRC-01",
            source_record_id="s1-78",
            issuer="CHÍNH PHỦ",
            issued_date="01/04/2025",
            continuation_issues=["651+652", "653+654"],
        )
        right = catalog(
            source_id="SRC-03",
            source_record_id="s3-78",
            issuer="Chính phủ",
            issued_date="01-04-2025",
            gazette_page="",
            page_url="https://fixture.test/src-03/213310.htm",
        )
        shared = b"%PDF-1.4\n%SYNTH-SHARED\n%%EOF\n"
        shared_sha = sha256_bytes(shared)
        artifacts = [
            artifact(
                source_id="SRC-01",
                source_record_id="s1-78:signed",
                parent_id="s1-78",
                attachment_id="s1-signed",
                file_url="https://fixture.test/src-01/78.signed.pdf",
                sha256=shared_sha,
                payload=shared,
            ),
            artifact(
                source_id="SRC-03",
                source_record_id="s3-78:signed",
                parent_id="s3-78",
                attachment_id="s3-signed",
                file_url="https://fixture.test/src-03/78.signed.pdf",
                sha256=shared_sha,
                payload=shared,
            ),
        ]
        for index in range(1, 4):
            artifacts.append(
                artifact(
                    source_id="SRC-03",
                    source_record_id=f"s3-78:pl{index}",
                    parent_id="s3-78",
                    attachment_id=f"s3-pl{index}",
                    file_url=f"https://fixture.test/src-03/78-pl{index}.pdf",
                    relation_role="appendix",
                )
            )
        for index in range(1, 3):
            artifacts.append(
                artifact(
                    source_id="SRC-01",
                    source_record_id=f"s1-78:cont{index}",
                    parent_id="s1-78",
                    attachment_id=f"s1-cont{index}",
                    file_type="doc",
                    file_url=f"https://fixture.test/src-01/78-cont{index}.doc",
                    relation_role="gazette_publication",
                    declared_mime="application/msword",
                    detected_mime="application/msword",
                )
            )
        result = reconcile_pilot_data([left, right], artifacts, CUTOFF, [], [])

        self.assertEqual(len(result["document_families"]), 1)
        self.assertEqual(len(result["document_versions"]), 1)
        self.assertRegex(result["document_families"][0]["document_family_id"], r"^fam_[0-9a-f]{16}$")
        self.assertRegex(result["document_versions"][0]["document_version_id"], r"^ver_[0-9a-f]{16}$")
        self.assertTrue(result["document_families"][0]["cross_source_overlap"])
        self.assertEqual(len(result["artifacts"]), 6)
        self.assertEqual(len(result["artifact_occurrences"]), 7)
        shared_artifact = next(row for row in result["artifacts"] if row["sha256"] == shared_sha)
        self.assertEqual(shared_artifact["occurrence_count"], 2)
        self.assertEqual(
            {occurrence["file_url"] for occurrence in shared_artifact["occurrences"]},
            {
                "https://fixture.test/src-01/78.signed.pdf",
                "https://fixture.test/src-03/78.signed.pdf",
            },
        )
        output_urls = {
            occurrence["file_url"]
            for occurrence in result["artifact_occurrences"]
        }
        self.assertEqual(output_urls, {row["file_url"] for row in artifacts})
        self.assertEqual(
            result["summary"]["totals"]["unique_blobs"], len(result["artifacts"])
        )

    def test_relation_roles_stay_distinct(self):
        roles = ("signed_original", "gazette_publication", "consolidated", "corrigendum", "amending")
        records = [
            catalog(
                source_record_id=f"rec-{index}",
                version=str(index + 1),
                relation_role=role,
                page_url=f"https://fixture.test/rec-{index}.htm",
            )
            for index, role in enumerate(roles)
        ]
        shared = b"%PDF-1.4\n%RELATION-SHARED\n%%EOF\n"
        artifacts = [
            artifact(
                source_record_id=f"att-{index}",
                parent_id="rec-0",
                attachment_id=f"a-{index}",
                file_url=f"https://fixture.test/files/a-{index}.pdf",
                relation_role=role,
                payload=f"%PDF-1.4\n%{role}\n%%EOF\n".encode(),
            )
            for index, role in enumerate(roles)
        ]
        artifacts.append(
            artifact(
                source_record_id="att-appendix",
                parent_id="rec-0",
                attachment_id="a-appendix",
                file_url="https://fixture.test/files/appendix.pdf",
                relation_role="appendix",
                sha256=sha256_bytes(shared),
                payload=shared,
            )
        )
        artifacts[0]["sha256"] = sha256_bytes(shared)
        artifacts[0]["size_bytes"] = len(shared)
        result = reconcile_pilot_data(records, artifacts, CUTOFF, [], [])

        self.assertEqual(len(result["document_families"]), 1)
        self.assertEqual(len(result["document_versions"]), 5)
        self.assertEqual(len({row["document_version_id"] for row in result["document_versions"]}), 5)
        self.assertEqual(
            {row["relation_role"] for row in result["document_versions"]},
            set(roles),
        )
        occurrence_roles = {row["relation_role"] for row in result["artifact_occurrences"]}
        self.assertTrue(set(roles) | {"appendix"} <= occurrence_roles)
        signed_blob = next(
            row for row in result["artifacts"] if row["sha256"] == sha256_bytes(shared)
        )
        self.assertEqual(len(result["artifacts"]), 5)
        self.assertEqual(signed_blob["occurrence_count"], 2)
        self.assertEqual(
            {row["relation_role"] for row in signed_blob["occurrences"]},
            {"signed_original", "appendix"},
        )


class ConflictDetectionTest(unittest.TestCase):
    def test_all_required_conflict_types_are_reported(self):
        date_mismatch_left = catalog(
            source_id="SRC-01",
            source_record_id="s1-78",
            title="Nghị định mẫu",
            observed_effective_date="01/06/2025",
        )
        date_mismatch_right = catalog(
            source_id="SRC-03",
            source_record_id="s3-78",
            issuer="Chính phủ",
            issued_date="01-04-2025",
            title="Nghị định khác tên",
            observed_effective_date="15/06/2025",
            page_url="https://fixture.test/src-03/78.htm",
        )
        missing_page = catalog(
            source_id="SRC-01",
            source_record_id="s1-99",
            document_number="99/2025/TT-BTNMT",
            gazette_page="",
        )
        date_anomaly = catalog(
            source_id="SRC-01",
            source_record_id="s1-61",
            document_number="61/2025/QĐ-TTg",
            issued_date="10/09/2025",
            gazette_published_date="05/09/2025",
            observed_effective_date="01/09/2025",
        )
        duplicate_left = catalog(
            source_id="SRC-01",
            source_record_id="s1-101",
            document_number="101/2025/QĐ-TTg",
            issuer="THỦ TƯỚNG CHÍNH PHỦ",
        )
        duplicate_right = catalog(
            source_id="SRC-03",
            source_record_id="s3-101",
            document_number="101/2025/QĐ-TTg",
            issuer="BỘ TƯ PHÁP",
        )
        quarantined = artifact(
            parent_id="s1-78",
            attachment_id="q1",
            status="QUARANTINED",
            quarantine_reason="TRUNCATED_OR_CORRUPT_PDF",
            file_url="https://fixture.test/files/truncated.pdf",
        )
        orphan = artifact(
            parent_id="MISSING-PARENT",
            attachment_id="orphan",
            relation_role="appendix",
            file_url="https://fixture.test/files/orphan.pdf",
        )
        conflicts = detect_conflicts(
            [
                date_mismatch_left,
                date_mismatch_right,
                missing_page,
                date_anomaly,
                duplicate_left,
                duplicate_right,
            ],
            [quarantined, orphan],
            CUTOFF,
        )
        by_type = {row["conflict_type"] for row in conflicts}
        self.assertEqual(
            by_type,
            {
                "METADATA_MISMATCH",
                "DATE_ANOMALY",
                "MISSING_GAZETTE_PAGE_OR_CONTINUATION",
                "SUSPECTED_DUPLICATE",
                "QUARANTINED_ARTIFACT",
                "MISSING_PARENT_ATTACHMENT",
            },
        )
        required = {
            "conflict_id",
            "conflict_type",
            "document_family_id",
            "document_number",
            "source_ids",
            "source_urls",
            "partition_ids",
            "details",
            "review_status",
            "cutoff_utc",
            "cutoff_vn",
        }
        for row in conflicts:
            self.assertTrue(required <= set(row))
            self.assertEqual(row["review_status"], "PENDING_REVIEW")
            self.assertEqual(row["cutoff_utc"], CUTOFF.cutoff_utc)
            self.assertRegex(row["conflict_id"], r"^cf_[0-9a-f]{16}$")
        codes = {(row["conflict_type"], row["conflict_code"]) for row in conflicts}
        self.assertIn(("METADATA_MISMATCH", "CROSS_SOURCE_EFFECTIVE_DATE_MISMATCH"), codes)
        self.assertIn(("METADATA_MISMATCH", "CROSS_SOURCE_TITLE_MISMATCH"), codes)
        self.assertIn(("DATE_ANOMALY", "GAZETTE_BEFORE_ISSUED_DATE"), codes)
        self.assertIn(("DATE_ANOMALY", "EFFECTIVE_BEFORE_ISSUED_DATE"), codes)
        self.assertIn(("SUSPECTED_DUPLICATE", "SAME_NUMBER_DATE_DIFFERENT_IDENTITY"), codes)
        orphan_row = next(row for row in conflicts if row["conflict_type"] == "MISSING_PARENT_ATTACHMENT")
        self.assertEqual(orphan_row["details"]["parent_id"], "MISSING-PARENT")
        self.assertIn("https://fixture.test/files/orphan.pdf", orphan_row["source_urls"])


class BoundaryAndRightsTest(unittest.TestCase):
    def test_boundaries_and_unknown_real_denominators(self):
        records = [
            catalog(
                source_id="SRC-01",
                source_record_id="pre-flag",
                issued_date="2024-05-01",
                is_pre_2020_reference=True,
                relation_role="pre_2020_reference",
            ),
            catalog(
                source_id="SRC-01",
                source_record_id="pre-date",
                issued_date="2019-12-31",
            ),
            catalog(
                source_id="SRC-01",
                source_record_id="post",
                issued_date="30/11/2026",
            ),
            catalog(
                source_id="SRC-01",
                source_record_id="missing",
                issued_date="",
                legal_status_verified=True,
            ),
            catalog(
                source_id="SRC-01",
                source_record_id="eligible",
                issued_date="01/06/2025",
                document_number="55/2025/NĐ-CP",
                legal_status_verified=True,
            ),
        ]
        result = reconcile_pilot_data(
            records, [], CUTOFF, rights("SRC-01", "PENDING_RIGHTS"), []
        )
        self.assertEqual(len(result["pre_2020_references"]), 2)
        self.assertEqual(len(result["out_of_window_excluded"]), 1)
        self.assertEqual(len(result["missing_or_invalid_date_records"]), 1)
        self.assertEqual(len(result["document_families"]), 1)
        self.assertEqual(result["summary"]["totals"]["pre_2020_references_excluded"], 2)
        self.assertEqual(result["summary"]["totals"]["post_cutoff_excluded"], 1)
        self.assertEqual(result["summary"]["totals"]["eligible"], 1)
        self.assertTrue(
            all(
                row["eligible_for_pilot_denominator"] is False
                for row in result["pre_2020_references"] + result["out_of_window_excluded"]
            )
        )
        self.assertTrue(
            any(
                row["conflict_code"] == "MISSING_OR_INVALID_ISSUED_DATE"
                for row in result["conflicts"]
            )
        )
        real = result["denominators"]["real_sources"]["SRC-01"]
        self.assertFalse(real["real_catalog_accessible"])
        self.assertEqual(real["measurement_status"], "UNKNOWN")
        self.assertEqual(real["observed"], "UNKNOWN")
        self.assertEqual(result["denominators"]["real"]["measurement_status"], "UNKNOWN")
        self.assertEqual(result["denominators"]["normalized_bytes_or_NOT_RUN"], "NOT_RUN")

        eligible = next(row for row in result["document_families"])
        self.assertFalse(eligible["legal_status_verified"])
        self.assertTrue(eligible["portal_effective_date_unverified"])
        self.assertFalse(
            next(
                row for row in result["source_records"] if row["source_record_id"] == "eligible"
            )["legal_status_verified"]
        )

    def test_approved_but_unexecuted_real_source_is_not_run(self):
        result = reconcile_pilot_data([], [], CUTOFF, rights("SRC-02", "APPROVED"), [])
        real = result["denominators"]["real_sources"]["SRC-02"]
        self.assertTrue(real["real_catalog_accessible"])
        self.assertEqual(real["measurement_status"], "NOT_RUN")
        self.assertEqual(real["observed"], "NOT_RUN")


class G1D02SamplingTest(unittest.TestCase):
    def _family(self, domain, index):
        return {
            "document_family_id": f"fam_{domain.lower()}{index:02d}",
            "domain_primary": domain,
            "version_ids": [],
            "source_ids": [f"FIXTURE-{domain}"],
            "rights_ref": "R",
            "data_origin": "SYNTHETIC_FIXTURE",
            "eligible_for_pilot_denominator": True,
            "cross_source_overlap": index == 0,
        }

    def _artifact(self, index, format_group, domain):
        return {
            "artifact_id": f"blb_{index:016x}",
            "sha256": f"{index:064x}",
            "format_group": format_group,
            "domain_primary": domain,
            "document_family_ids": [f"fam_{domain.lower()}00"],
            "document_version_ids": [],
            "eligible_for_extraction": True,
            "rights_ref": "R",
            "data_origin": "SYNTHETIC_FIXTURE",
        }

    def test_selection_meets_targets_without_double_counting(self):
        families = [
            self._family(domain, index)
            for index in range(5)
            for domain in PILOT_DOMAINS
        ]
        formats = (
            ["pdf_text"] * 6
            + ["pdf_scan"] * 6
            + ["html"] * 4
            + ["doc_docx"] * 4
            + ["spreadsheet"] * 4
            + ["pdf_text"] * 18
        )
        artifacts = [
            self._artifact(index, format_group, PILOT_DOMAINS[index % len(PILOT_DOMAINS)])
            for index, format_group in enumerate(formats)
        ]
        selection = select_g1_d02_pilot_samples(families, artifacts)
        self.assertEqual(selection["targets"], G1_D02_TARGETS)
        self.assertEqual(
            selection["counts"],
            {
                "pilot_catalog_families": 45,
                "extraction_artifacts": 36,
                "graph_families": 18,
                "review_candidate_cases": 27,
                "unique_families_total": 45,
                "unique_artifacts_total": 36,
                "unique_review_cases_total": 27,
            },
        )
        for layer in ("pilot_catalog_families", "extraction_artifacts", "graph_families", "review_candidate_cases"):
            self.assertEqual(selection["shortfalls"][layer]["status"], "MET")
        self.assertTrue(
            all(
                entry["status"] == "MET"
                for entry in selection["shortfalls"]["extraction_artifacts"]["by_format"].values()
            )
        )
        family_rows = [row for row in selection["rows"] if row["sample_kind"] == "document_family"]
        artifact_rows = [row for row in selection["rows"] if row["sample_kind"] == "artifact"]
        case_rows = [row for row in selection["rows"] if row["sample_kind"] == "review_case"]
        self.assertEqual(len(family_rows), 45)
        self.assertEqual(len({row["document_family_id"] for row in family_rows}), 45)
        self.assertEqual(sum(1 for row in family_rows if row["in_pilot_catalog"]), 45)
        self.assertEqual(sum(1 for row in family_rows if row["in_graph_gold"]), 18)
        self.assertEqual(len(artifact_rows), 36)
        self.assertEqual(len({row["artifact_id"] for row in artifact_rows}), 36)
        self.assertEqual(len(case_rows), 27)
        graph_ids = {row["document_family_id"] for row in family_rows if row["in_graph_gold"]}
        catalog_ids = {row["document_family_id"] for row in family_rows if row["in_pilot_catalog"]}
        self.assertTrue(graph_ids <= catalog_ids)

    def test_shortfalls_never_lower_targets(self):
        families = [self._family("ADM", 0), self._family("ENV", 0)]
        artifacts = [
            self._artifact(1, "pdf_text", "ADM"),
            self._artifact(2, "pdf_text", "ENV"),
            self._artifact(3, "html", "ADM"),
        ]
        selection = select_g1_d02_pilot_samples(families, artifacts)
        self.assertEqual(selection["targets"], {"pilot_catalog_families": 45, "extraction_artifacts": 36, "graph_families": 18, "review_candidate_cases": 27})
        self.assertEqual(selection["shortfalls"]["pilot_catalog_families"]["selected"], 2)
        self.assertEqual(selection["shortfalls"]["pilot_catalog_families"]["shortfall"], 43)
        self.assertEqual(selection["shortfalls"]["pilot_catalog_families"]["by_domain"]["ADM"]["target"], 5)
        self.assertEqual(selection["shortfalls"]["pilot_catalog_families"]["by_domain"]["ADM"]["selected"], 1)
        self.assertEqual(selection["shortfalls"]["pilot_catalog_families"]["by_domain"]["CIV"]["shortfall"], 5)
        self.assertEqual(selection["shortfalls"]["graph_families"]["shortfall"], 16)
        self.assertEqual(selection["shortfalls"]["review_candidate_cases"]["shortfall"], 21)
        self.assertEqual(selection["shortfalls"]["extraction_artifacts"]["shortfall"], 33)
        self.assertEqual(selection["shortfalls"]["extraction_artifacts"]["by_format"]["pdf_text"]["shortfall"], 4)
        self.assertEqual(selection["shortfalls"]["extraction_artifacts"]["by_format"]["html"]["shortfall"], 3)
        for layer in selection["shortfalls"].values():
            self.assertEqual(layer["status"], "SHORTFALL")


class DeterminismAndReplayTest(unittest.TestCase):
    def test_qa_fixture_replay_and_cli_manifest(self):
        fixtures = build_qa_fixture(CUTOFF)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            verification = verify_reconciliation_invariants(
                fixtures["catalog_records"],
                fixtures["artifact_records"],
                CUTOFF,
                fixtures["rights_matrix"],
                fixtures["partition_ledger"],
                run_a_dir=root / "a",
                run_b_dir=root / "b",
            )
            self.assertEqual(verification["status"], "PASS")
            self.assertTrue(all(check["passed"] for check in verification["checks"]))
            self.assertEqual(
                {check["name"] for check in verification["checks"]},
                {
                    "deterministic_output_digests",
                    "zero_lost_source_or_file_urls",
                    "every_occurrence_appendix_and_quarantine_reported",
                    "boundary_exclusions_hold",
                    "portal_metadata_never_affirms_legal_status",
                },
            )
            self.assertEqual(len(verification["file_sha256"]), 15)
            self.assertEqual(len(verification["jsonl_sha256"]), 7)
            self.assertEqual(len(verification["csv_sha256"]), 7)
            self.assertEqual(verification["summary"]["totals"]["pre_2020_references_excluded"], 2)
            self.assertEqual(verification["summary"]["totals"]["post_cutoff_excluded"], 1)
            manifest_rows = [
                json.loads(line)
                for line in (root / "a" / "artifact-manifest.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            shared_rows = [row for row in manifest_rows if row["occurrence_count"] > 1]
            self.assertEqual(len(shared_rows), 1)
            self.assertEqual(
                {occurrence["source_id"] for occurrence in shared_rows[0]["occurrences"]},
                {"FIXTURE-SRC-01", "FIXTURE-SRC-03"},
            )

        with TemporaryDirectory() as directory:
            qa_dir = Path(directory) / "qa"
            exit_code = main(
                [
                    "--qa-fixture-dir",
                    str(qa_dir),
                    "--cutoff-vn",
                    CUTOFF.cutoff_vn,
                    "--cutoff-utc",
                    CUTOFF.cutoff_utc,
                ]
            )
            self.assertEqual(exit_code, 0)
            manifest_path = qa_dir / "worker-manifest.json"
            self.assertTrue(manifest_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "PASS")
            self.assertTrue(manifest["passed"])
            self.assertTrue(manifest["replay"]["deterministic"])
            self.assertEqual(manifest["real_source_denominators"], "UNKNOWN")
            self.assertFalse(manifest["legal_status_verified"])
            self.assertEqual(len(manifest["replay"]["file_sha256"]), 15)

    def test_non_child_parent_slug_resolves_by_source_record_id_and_pending_registry_expands(self):
        rec = catalog(
            source_id="FIXTURE-SRC-01",
            source_record_id="55991",
            relation_role="gazette_publication",
            domain="ADM",
        )
        art = artifact(
            source_id="FIXTURE-SRC-01",
            source_record_id="55991",
            parent_id="44704",  # portal family slug != source_record_id
            attachment_id="att-slug",
            relation_role="gazette_publication",
            file_type="pdf",
            file_url="https://fixture.test/files/doc-scan.pdf",
        )
        result = reconcile_pilot_data([rec], [art], CUTOFF, [], [])
        self.assertEqual(len(result["artifacts"]), 1)
        self.assertEqual(result["artifacts"][0]["domain_primary"], "ADM")
        self.assertEqual(result["artifacts"][0]["format_group"], "pdf_scan")
        self.assertTrue(result["artifacts"][0]["eligible_for_extraction"])
        self.assertEqual(
            result["document_families"][0]["artifact_ids"],
            [result["artifacts"][0]["artifact_id"]],
        )

        # Fail-closed registry with empty actions expands to all 6 PENDING_RIGHTS actions per source
        root = Path(__file__).resolve().parents[3]
        with TemporaryDirectory() as directory:
            staging = Path(directory) / "staging"
            staging.mkdir()
            (staging / "catalog.jsonl").write_text(
                json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            (staging / "artifacts.jsonl").write_text(
                json.dumps(art, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            out_dir = Path(directory) / "merged"
            code = main(
                [
                    "--merge-staging-dirs",
                    str(staging),
                    "--output-dir",
                    str(out_dir),
                    "--cutoff-vn",
                    CUTOFF.cutoff_vn,
                    "--cutoff-utc",
                    CUTOFF.cutoff_utc,
                    "--source-rights",
                    str(root / "experiments/g1/source-rights.json"),
                ]
            )
            self.assertEqual(code, 0)
            rights_lines = [
                json.loads(line)
                for line in (out_dir / "rights-matrix.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            # 7 sources x 6 actions = 42 rows, all PENDING_RIGHTS
            self.assertEqual(len(rights_lines), 42)
            self.assertTrue(all(row["status"] == "PENDING_RIGHTS" for row in rights_lines))


class IsolationCompletenessAndAuditTest(unittest.TestCase):
    # P1-1: Real statistics, overlap, and G1-D02 samples stay strictly isolated from synthetic fixtures.
    def test_real_and_synthetic_never_mix_even_with_identical_family_key_and_hash(self):
        shared_bytes = b"%PDF-1.4\n%IDENTICAL-BYTES-REAL-AND-SYNTH\n%%EOF\n"
        shared_sha = sha256_bytes(shared_bytes)
        real_rec_1 = catalog(
            source_id="SRC-01",
            source_record_id="real-55991",
            data_origin="REAL",
            document_number="78/2025/NĐ-CP",
            issuer="CHÍNH PHỦ",
            issued_date="01/04/2025",
            domain="ADM",
            rights_ref="APPROVED:g1-real-v1:EVID-01",
        )
        real_rec_2 = catalog(
            source_id="SRC-03",
            source_record_id="real-213310",
            data_origin="REAL",
            document_number="78/2025/NĐ-CP",
            issuer="Chính phủ",
            issued_date="01-04-2025",
            domain="ADM",
            rights_ref="APPROVED:g1-real-v1:EVID-03",
        )
        synth_same_key = catalog(
            source_id="FIXTURE-SRC-01",
            source_record_id="syn-55991",
            data_origin="SYNTHETIC_FIXTURE",
            document_number="78/2025/NĐ-CP",
            issuer="CHÍNH PHỦ",
            issued_date="01/04/2025",
            domain="ADM",
            rights_ref="APPROVED:fixture:SYNTHETIC-FIXTURE-ONLY",
        )
        synth_other_num = catalog(
            source_id="FIXTURE-SRC-03",
            source_record_id="syn-999",
            data_origin="SYNTHETIC_FIXTURE",
            document_number="99/2025/TT-BTNMT",
            issuer="Bộ Tài nguyên và Môi trường",
            document_type="Thông tư",
            issued_date="10/09/2025",
            domain="ENV",
            rights_ref="APPROVED:fixture:SYNTHETIC-FIXTURE-ONLY",
        )
        arts = [
            artifact(
                source_id="SRC-01",
                source_record_id="real-55991",
                parent_id="real-55991",
                attachment_id="real-a1",
                data_origin="REAL",
                sha256=shared_sha,
                payload=shared_bytes,
                rights_ref="APPROVED:g1-real-v1:EVID-01",
            ),
            artifact(
                source_id="FIXTURE-SRC-01",
                source_record_id="syn-55991",
                parent_id="syn-55991",
                attachment_id="syn-a1",
                data_origin="SYNTHETIC_FIXTURE",
                sha256=shared_sha,
                payload=shared_bytes,
                rights_ref="APPROVED:fixture:SYNTHETIC-FIXTURE-ONLY",
            ),
            artifact(
                source_id="FIXTURE-SRC-03",
                source_record_id="syn-999",
                parent_id="syn-999",
                attachment_id="syn-a2",
                document_number="99/2025/TT-BTNMT",
                data_origin="SYNTHETIC_FIXTURE",
                rights_ref="APPROVED:fixture:SYNTHETIC-FIXTURE-ONLY",
            ),
        ]
        approved_rights = rights("SRC-01", "APPROVED") + rights("SRC-03", "APPROVED")
        complete_ledger = [
            {
                "source_id": "SRC-01",
                "partition_id": "SRC-01__2025",
                "status": "COMPLETED",
                "rights_status": "APPROVED",
                "catalog_enumeration_complete": True,
                "requests_attempted": 2,
                "blobs_written": 1,
            },
            {
                "source_id": "SRC-03",
                "partition_id": "SRC-03__2025",
                "status": "COMPLETED",
                "rights_status": "APPROVED",
                "catalog_enumeration_complete": True,
                "requests_attempted": 1,
                "blobs_written": 0,
            },
        ]
        result = reconcile_pilot_data(
            [real_rec_1, real_rec_2, synth_same_key, synth_other_num],
            arts,
            CUTOFF,
            approved_rights,
            complete_ledger,
        )

        # No MIXED families or MIXED blobs are created.
        self.assertTrue(all(row["data_origin"] != "MIXED" for row in result["document_families"]))
        self.assertTrue(all(row["data_origin"] != "MIXED" for row in result["artifacts"]))
        real_fams = [row for row in result["document_families"] if row["data_origin"] == "REAL"]
        synth_fams = [
            row for row in result["document_families"] if row["data_origin"] == "SYNTHETIC_FIXTURE"
        ]
        self.assertEqual(len(real_fams), 1)
        self.assertEqual(len(synth_fams), 2)
        self.assertNotEqual(real_fams[0]["document_family_id"], synth_fams[0]["document_family_id"])
        self.assertTrue(real_fams[0]["cross_source_overlap"])
        self.assertEqual(real_fams[0]["source_ids"], ["SRC-01", "SRC-03"])

        # Shared SHA-256 bytes stay split into distinct REAL vs SYNTHETIC_FIXTURE blob entries.
        real_blobs = [row for row in result["artifacts"] if row["data_origin"] == "REAL"]
        synth_blobs = [
            row for row in result["artifacts"] if row["data_origin"] == "SYNTHETIC_FIXTURE"
        ]
        self.assertEqual(len(real_blobs), 1)
        self.assertEqual(len(synth_blobs), 2)
        self.assertNotEqual(real_blobs[0]["artifact_id"], synth_blobs[0]["artifact_id"])

        # G1-D02 sample selection uses ONLY valid REAL records and excludes every synthetic item.
        self.assertEqual(result["pilot_selection"]["selection_origin"], "REAL")
        self.assertEqual(result["pilot_selection"]["counts"]["pilot_catalog_families"], 1)
        self.assertEqual(result["pilot_selection"]["counts"]["extraction_artifacts"], 1)
        self.assertTrue(all(row["data_origin"] == "REAL" for row in result["pilot_samples"]))

        # Direct call to select_g1_d02_pilot_samples with mixed + SYNTHETIC inputs isolates REAL.
        mixed_fake = {**real_fams[0], "document_family_id": "fam_mixed", "data_origin": "MIXED"}
        direct_sel = select_g1_d02_pilot_samples(
            [real_fams[0], synth_fams[0], synth_fams[1], mixed_fake],
            [*real_blobs, *synth_blobs],
        )
        self.assertEqual(direct_sel["selection_origin"], "REAL")
        self.assertEqual(direct_sel["counts"]["pilot_catalog_families"], 1)
        self.assertEqual(direct_sel["counts"]["extraction_artifacts"], 1)

        # Unapproved REAL records never enter real G1-D02 samples and never fall back to synthetic.
        unapproved_res = reconcile_pilot_data(
            [real_rec_1, synth_other_num],
            arts[:1] + arts[2:],
            CUTOFF,
            rights("SRC-01", "PENDING_RIGHTS"),
            [],
        )
        self.assertEqual(unapproved_res["pilot_selection"]["selection_origin"], "REAL")
        self.assertEqual(unapproved_res["pilot_selection"]["counts"]["pilot_catalog_families"], 0)
        self.assertEqual(unapproved_res["pilot_selection"]["counts"]["extraction_artifacts"], 0)

    # P1-2: Partial / incomplete partitions never lock denominator as MEASURED.
    def test_denominator_requires_complete_enumeration_across_all_required_partitions(self):
        # 1. Approved source with 1 empty PARTIAL + 1 NOT_RUN partition -> PARTIAL (observed=UNKNOWN).
        partial_ledger = [
            {
                "source_id": "SRC-01",
                "partition_id": "SRC-01__2024",
                "status": "PARTIAL",
                "rights_status": "APPROVED",
                "catalog_enumeration_complete": False,
            },
            {
                "source_id": "SRC-01",
                "partition_id": "SRC-01__2025",
                "status": "NOT_RUN",
                "rights_status": "APPROVED",
                "catalog_enumeration_complete": False,
            },
        ]
        res_partial = reconcile_pilot_data(
            [], [], CUTOFF, rights("SRC-01", "APPROVED"), partial_ledger
        )
        src1 = res_partial["denominators"]["real_sources"]["SRC-01"]
        self.assertEqual(src1["measurement_status"], "PARTIAL")
        self.assertFalse(src1["denominator_locked"])
        self.assertEqual(src1["observed"], "UNKNOWN")
        self.assertEqual(src1["progress"]["observed"], 0)
        self.assertEqual(
            src1["progress"]["incomplete_partition_ids"], ["SRC-01__2024", "SRC-01__2025"]
        )
        self.assertEqual(res_partial["denominators"]["real"]["measurement_status"], "PARTIAL")
        self.assertEqual(res_partial["denominators"]["real"]["observed"], "UNKNOWN")

        # 2. Completed partition WITHOUT catalog_enumeration_complete=True (e.g. manual sample) -> PARTIAL.
        real_rec = catalog(
            source_id="SRC-01",
            source_record_id="real-1",
            data_origin="REAL",
            rights_ref="APPROVED:g1-real-v1:EVID-01",
        )
        sample_ledger = [
            {
                "source_id": "SRC-01",
                "partition_id": "SRC-01__2025",
                "status": "COMPLETED",
                "rights_status": "APPROVED",
                "catalog_enumeration_complete": False,
            }
        ]
        res_sample = reconcile_pilot_data(
            [real_rec], [], CUTOFF, rights("SRC-01", "APPROVED"), sample_ledger
        )
        src1_sample = res_sample["denominators"]["real_sources"]["SRC-01"]
        self.assertEqual(src1_sample["measurement_status"], "PARTIAL")
        self.assertFalse(src1_sample["denominator_locked"])
        self.assertEqual(src1_sample["observed"], "UNKNOWN")
        self.assertEqual(src1_sample["progress"]["observed"], 1)

        # 3. Full enumeration complete on ALL required partitions -> MEASURED & locked.
        full_ledger = [
            {
                "source_id": "SRC-01",
                "partition_id": "SRC-01__2025",
                "status": "COMPLETE",  # legacy spelling normalized to COMPLETED
                "rights_status": "APPROVED",
                "catalog_enumeration_complete": True,
                "requests_attempted": 4,
                "blobs_written": 2,
            }
        ]
        res_full = reconcile_pilot_data(
            [real_rec],
            [],
            CUTOFF,
            rights("SRC-01", "APPROVED"),
            full_ledger,
            required_partitions_by_source={"SRC-01": ["SRC-01__2025"]},
        )
        src1_full = res_full["denominators"]["real_sources"]["SRC-01"]
        self.assertEqual(src1_full["measurement_status"], "MEASURED")
        self.assertTrue(src1_full["denominator_locked"])
        self.assertEqual(src1_full["observed"], 1)
        self.assertEqual(res_full["denominators"]["real"]["measurement_status"], "MEASURED")
        # P2-2: Legacy COMPLETE normalized to COMPLETED and requests_attempted/blobs_written preserved.
        self.assertEqual(res_full["partition_ledger"][0]["status"], "COMPLETED")
        self.assertEqual(res_full["partition_ledger"][0]["requests_attempted"], 4)
        self.assertEqual(res_full["partition_ledger"][0]["blobs_written"], 2)

        # 4. Missing required partition prevents MEASURED even when another partition is complete.
        res_missing_req = reconcile_pilot_data(
            [real_rec],
            [],
            CUTOFF,
            rights("SRC-01", "APPROVED"),
            full_ledger,
            required_partitions_by_source={"SRC-01": ["SRC-01__2025", "SRC-01__2026"]},
        )
        self.assertEqual(
            res_missing_req["denominators"]["real_sources"]["SRC-01"]["measurement_status"],
            "PARTIAL",
        )
        self.assertEqual(
            res_missing_req["denominators"]["real_sources"]["SRC-01"]["progress"][
                "incomplete_partition_ids"
            ],
            ["SRC-01__2026"],
        )

    # P2-3: Filtered execution log redacts secrets and records UTC timestamps, exit code, and digests.
    def test_execution_log_redacts_secrets_and_hashes_outputs(self):
        raw = "Authorization: Bearer secret_jwt_123\napi_key=ghp_" + ("a" * 36) + "\nOK"
        redacted = redact_sensitive_text(raw)
        self.assertNotIn("secret_jwt_123", redacted)
        self.assertNotIn("ghp_", redacted)
        self.assertIn("[REDACTED]", redacted)

        with TemporaryDirectory() as directory:
            log_dir = Path(directory) / "execution-logs"
            rec = record_execution_log(
                log_dir,
                step_name="worker-src01-replay",
                command=["python", "-m", "luatvn_ai_data_ingestion.src01_adapter"],
                started_at_utc="2026-11-26T16:00:00Z",
                finished_at_utc="2026-11-26T16:00:01Z",
                exit_code=0,
                stdout=raw,
                stderr="",
                output_digests={"bundle": "0" * 64},
            )
            self.assertEqual(rec["exit_code"], 0)
            self.assertRegex(rec["log_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(rec["record_sha256"], r"^[0-9a-f]{64}$")
            saved_log = (log_dir / rec["log_file"]).read_text(encoding="utf-8")
            self.assertNotIn("secret_jwt_123", saved_log)
            self.assertIn("[REDACTED]", saved_log)


if __name__ == "__main__":
    unittest.main()
