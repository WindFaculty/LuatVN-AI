"""Tests for the rights-gated SRC-03 adapter, staging pipeline, and synthetic pilot."""

import contextlib
import io
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from luatvn_ai_data_ingestion.pilot_schema import (
    RunCutoff,
    SharedRateLimiter,
    sha256_bytes,
)
from luatvn_ai_data_ingestion.source_rights import SourceRegistry
from luatvn_ai_data_ingestion.src03_adapter import (
    FIXTURE_SOURCE_ID,
    SHARED_SYNTHETIC_PDF,
    FetchResult,
    PartitionRecordSpec,
    build_src03_synthetic_fixtures,
    build_src03_synthetic_registry,
    main as src03_main,
    parse_src03_document_html,
    parse_src03_listing_html,
    run_src03_automated_batch,
    run_src03_manual_intake,
    run_src03_partition,
    run_src03_synthetic_pilot,
)

ROOT = Path(__file__).resolve().parents[3]
CUTOFF = RunCutoff(
    run_id="G1-PILOT-SRC01-SRC03-20261126-01",
    cutoff_utc="2026-11-26T12:58:39Z",
    cutoff_vn="2026-11-26T19:58:39+07:00",
)


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def file_hashes(root):
    return {
        str(path.relative_to(root)).replace("\\", "/"): sha256_bytes(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class Src03AdapterTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.suite = build_src03_synthetic_fixtures(self.root / "suite")
        self.documents = {document.source_record_id: document for document in self.suite.documents}

    def run_partition(self, *, name, year, specs, fetcher, registry=None, source_id=FIXTURE_SOURCE_ID, limiter=None):
        return run_src03_partition(
            staging_root=self.root / name,
            registry=registry or self.suite.registry,
            cutoff=CUTOFF,
            partition_id=f"{source_id}__{year}",
            year=year,
            source_id=source_id,
            document_specs=specs,
            fetcher=fetcher,
            rate_limiter=limiter,
        )

    # 1. Live source is rights-blocked before any network or blob write.
    def test_real_registry_blocks_all_2020_to_2026_partitions(self):
        registry = SourceRegistry(ROOT / "experiments/g1/source-rights.json")
        attempted = []

        def forbidden(url):
            attempted.append(url)
            raise AssertionError(f"network access attempted: {url}")

        specs = [
            PartitionRecordSpec(
                page_url="https://vanban.chinhphu.vn/?classid=1&docid=213310&pageid=27160",
                source_record_id="213310",
                domain_candidate="ADM",
            )
        ]
        for year in range(2020, 2027):
            with self.subTest(year=year):
                result = run_src03_partition(
                    staging_root=self.root / "real-blocked",
                    registry=registry,
                    cutoff=CUTOFF,
                    partition_id=f"SRC-03__{year}",
                    year=year,
                    source_id="SRC-03",
                    document_specs=specs,
                    fetcher=forbidden,
                )
                self.assertEqual(result["status"], "BLOCKED_RIGHTS")
                self.assertEqual(result["rights_status"], "BLOCKED_RIGHTS")
                self.assertEqual(result["network"]["requests_attempted"], 0)
                self.assertEqual(result["counts"]["records_observed"], 0)
                self.assertEqual(result["counts"]["artifacts_total"], 0)

                partition = Path(result["partition_dir"])
                self.assertFalse((partition / "blobs").exists())
                self.assertFalse((partition / "quarantine").exists())
                self.assertEqual((partition / "catalog.jsonl").read_text(encoding="utf-8"), "")
                self.assertEqual((partition / "artifacts.jsonl").read_text(encoding="utf-8"), "")
                checkpoint = json.loads((partition / "checkpoint.json").read_text(encoding="utf-8"))
                self.assertEqual(checkpoint["status"], "BLOCKED_RIGHTS")
                self.assertEqual(checkpoint["rights_status"], "BLOCKED_RIGHTS")
                self.assertIn("PENDING_RIGHTS", checkpoint["rights_ref"])
                manifest = json.loads((partition / "partition-manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["rights_status"], "BLOCKED_RIGHTS")
                self.assertEqual(manifest["counts"]["records_observed"], 0)

        self.assertEqual(attempted, [])

    # 2. Parser: metadata, dates, attachment roles, and __doPostBack filtering.
    def test_parse_document_html_extracts_metadata_and_relations(self):
        document = self.documents["213310"]
        page = parse_src03_document_html(document.html, document.page_url)
        self.assertEqual(page.source_record_id, "213310")
        self.assertEqual(page.document_number, "78/2025/NĐ-CP")
        self.assertEqual(page.document_type, "Nghị định")
        self.assertEqual(page.issuer, "Chính phủ")
        self.assertEqual(page.issued_date, "01-04-2025")
        self.assertEqual(page.observed_effective_date, "01-04-2025")
        self.assertIn("Quy định chi tiết", page.title)
        self.assertEqual(page.relation_role, "catalog_entry")

        self.assertEqual(len(page.attachments), 5)
        self.assertEqual(
            {attachment.file_name for attachment in page.attachments},
            {"78ndcp-1.signed.pdf", "78-pl1.pdf", "pl2.pdf", "pl3.pdf", "pl4.pdf"},
        )
        for attachment in page.attachments:
            self.assertTrue(attachment.file_url.startswith("https://datafiles.chinhphu.vn/"))
            self.assertNotIn("javascript:", attachment.file_url)
            self.assertEqual(attachment.parent_id, "213310")
        roles = {attachment.file_name: attachment.relation_role for attachment in page.attachments}
        self.assertEqual(roles["78ndcp-1.signed.pdf"], "signed_original")
        for appendix in ("78-pl1.pdf", "pl2.pdf", "pl3.pdf", "pl4.pdf"):
            self.assertEqual(roles[appendix], "appendix")

        consolidated = parse_src03_document_html(
            self.documents["900116"].html, self.documents["900116"].page_url
        )
        self.assertEqual(consolidated.document_number, "116/VBHN-BNNMT")
        self.assertEqual(consolidated.relation_role, "consolidated")
        self.assertEqual(consolidated.related_to_document_number, "78/2025/NĐ-CP")
        self.assertEqual([a.relation_role for a in consolidated.attachments], ["consolidated"])

        corrigendum = parse_src03_document_html(
            self.documents["900012"].html, self.documents["900012"].page_url
        )
        self.assertEqual(corrigendum.relation_role, "corrigendum")
        self.assertEqual(corrigendum.related_to_document_number, "78/2025/NĐ-CP")
        self.assertEqual(
            {attachment.relation_role for attachment in corrigendum.attachments},
            {"corrigendum"},
        )

        amending = parse_src03_document_html(
            self.documents["900413"].html, self.documents["900413"].page_url
        )
        self.assertEqual(amending.relation_role, "amending")
        self.assertEqual(amending.related_to_document_number, "104/2025/NĐ-CP")
        self.assertEqual(amending.issued_date, "16-11-2026")
        self.assertEqual(amending.observed_effective_date, "01-12-2026")
        self.assertEqual([a.relation_role for a in amending.attachments], ["amending"])

        pre_2020 = parse_src03_document_html(
            self.documents["900045"].html, self.documents["900045"].page_url
        )
        self.assertEqual(pre_2020.relation_role, "pre_2020_reference")
        self.assertEqual(pre_2020.issued_date, "20-11-2019")

        missing_date = parse_src03_document_html(
            self.documents["900205"].html, self.documents["900205"].page_url
        )
        self.assertEqual(missing_date.issued_date, "")
        self.assertEqual(missing_date.observed_effective_date, "")

    # 3. Interruption persists completed records; resume completes without duplicates.
    def test_checkpoint_interruption_and_resume_without_duplicates(self):
        specs = self.suite.partitions[2025]
        first_document_requests = 1 + len(self.documents["213310"].attachments)
        calls = {"count": 0}

        def interrupting_fetcher(url):
            if calls["count"] >= first_document_requests:
                raise RuntimeError("synthetic interruption")
            calls["count"] += 1
            return self.suite.fetcher(url)

        with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
            self.run_partition(name="resume", year=2025, specs=specs, fetcher=interrupting_fetcher)

        partition = self.root / "resume" / f"{FIXTURE_SOURCE_ID}__2025"
        checkpoint = json.loads((partition / "checkpoint.json").read_text(encoding="utf-8"))
        self.assertEqual(checkpoint["status"], "INTERRUPTED")
        self.assertEqual(checkpoint["completed_record_ids"], ["213310"])
        partial_catalog = read_jsonl(partition / "catalog.jsonl")
        self.assertEqual([row["source_record_id"] for row in partial_catalog], ["213310"])

        resumed = self.run_partition(name="resume", year=2025, specs=specs, fetcher=self.suite.fetcher)
        self.assertEqual(resumed["status"], "COMPLETED")

        catalog = read_jsonl(partition / "catalog.jsonl")
        artifacts = read_jsonl(partition / "artifacts.jsonl")
        self.assertEqual(len(catalog), 3)
        self.assertEqual(len({row["source_record_id"] for row in catalog}), 3)
        self.assertEqual(len(artifacts), 8)
        self.assertEqual(len({row["file_url"] for row in artifacts}), 8)
        self.assertEqual(len(list((partition / "blobs").rglob("*.bin"))), 8)

        fresh = self.run_partition(name="fresh", year=2025, specs=specs, fetcher=self.suite.fetcher)
        fresh_partition = Path(fresh["partition_dir"])
        self.assertEqual(
            (partition / "catalog.jsonl").read_bytes(),
            (fresh_partition / "catalog.jsonl").read_bytes(),
        )
        self.assertEqual(
            (partition / "artifacts.jsonl").read_bytes(),
            (fresh_partition / "artifacts.jsonl").read_bytes(),
        )

    # 4. HTTP/TLS/CAPTCHA/429 stops and shared chinhphu.vn rate bucket.
    def test_network_stop_policy_and_shared_rate_limiter(self):
        specs = self.suite.partitions[2020]
        scenarios = {
            "http-403": (FetchResult(status_code=403, body=b"forbidden"), "STOP_HTTP_403", 1),
            "captcha": (
                FetchResult(status_code=200, body=b"<html>Please verify you are human. CAPTCHA</html>"),
                "STOP_CAPTCHA",
                1,
            ),
            "tls": (
                FetchResult(status_code=None, tls_error="CERTIFICATE_VERIFY_FAILED"),
                "STOP_TLS_ERROR",
                1,
            ),
            "http-429": (
                FetchResult(status_code=429, headers={"Retry-After": "5"}, body=b"rate limited"),
                "STOP_HTTP_429",
                3,
            ),
        }
        for name, (response, expected_code, expected_requests) in scenarios.items():
            with self.subTest(name=name):
                result = self.run_partition(
                    name=f"stop-{name}",
                    year=2020,
                    specs=specs,
                    fetcher=lambda url, response=response: response,
                )
                self.assertEqual(result["status"], "STOPPED")
                self.assertEqual(result["network"]["stop_reason"], expected_code)
                self.assertEqual(result["network"]["requests_attempted"], expected_requests)
                partition = Path(result["partition_dir"])
                self.assertFalse((partition / "blobs").exists())
                errors = read_jsonl(partition / "errors.jsonl")
                self.assertTrue(any(row["error_type"] == expected_code for row in errors))

        # 429 Retry-After is retried within budget, then the partition completes.
        target = specs[1]
        retried = {"page_429": False}

        def retry_once_fetcher(url):
            if url == target.page_url and not retried["page_429"]:
                retried["page_429"] = True
                return FetchResult(status_code=429, headers={"Retry-After": "5"}, body=b"rate limited")
            return self.suite.fetcher(url)

        result = self.run_partition(
            name="retry-429", year=2020, specs=[target], fetcher=retry_once_fetcher
        )
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["network"]["requests_attempted"], 3)

        # Shared infrastructure cap spans two distinct sources.
        registry = build_src03_synthetic_registry(
            self.root / "shared-rights.json",
            source_ids=[FIXTURE_SOURCE_ID, "FIXTURE-SRC-03-B"],
        )
        limiter = SharedRateLimiter(
            per_source_max_per_minute=20, shared_infra_max_per_minute=2
        )
        single = [PartitionRecordSpec(
            page_url=self.documents["900205"].page_url,
            source_record_id="900205",
            domain_candidate="EDU",
        )]
        first = run_src03_partition(
            staging_root=self.root / "shared-a",
            registry=registry,
            cutoff=CUTOFF,
            partition_id=f"{FIXTURE_SOURCE_ID}__2025",
            year=2025,
            source_id=FIXTURE_SOURCE_ID,
            document_specs=single,
            fetcher=self.suite.fetcher,
            rate_limiter=limiter,
        )
        self.assertEqual(first["status"], "COMPLETED")
        self.assertEqual(first["network"]["requests_attempted"], 2)

        attempted = []

        def tracking_fetcher(url):
            attempted.append(url)
            return self.suite.fetcher(url)

        second = run_src03_partition(
            staging_root=self.root / "shared-b",
            registry=registry,
            cutoff=CUTOFF,
            partition_id="FIXTURE-SRC-03-B__2025",
            year=2025,
            source_id="FIXTURE-SRC-03-B",
            document_specs=single,
            fetcher=tracking_fetcher,
            rate_limiter=limiter,
        )
        self.assertEqual(second["status"], "STOPPED")
        self.assertEqual(second["network"]["stop_reason"], "SHARED_INFRA_RATE_LIMIT")
        self.assertEqual(second["network"]["requests_attempted"], 0)
        self.assertEqual(attempted, [])

    # 5. Quarantine evidence plus pre-2020 / post-cutoff / missing-date boundaries.
    def test_quarantine_and_window_boundary_rules(self):
        pilot = run_src03_synthetic_pilot(self.root / "pilot", CUTOFF)
        self.assertEqual(pilot["aggregate"]["complete"], 4)

        def catalog(year):
            return read_jsonl(
                self.root / "pilot" / f"{FIXTURE_SOURCE_ID}__{year}" / "catalog.jsonl"
            )

        def artifacts(year):
            return read_jsonl(
                self.root / "pilot" / f"{FIXTURE_SOURCE_ID}__{year}" / "artifacts.jsonl"
            )

        artifacts_2024 = artifacts(2024)
        quarantined = [row for row in artifacts_2024 if row["status"] == "QUARANTINED"]
        self.assertEqual(
            {row["quarantine_reason"] for row in quarantined},
            {"EMPTY_CORRUPT_ARTIFACT", "CHECKSUM_MISMATCH"},
        )
        quarantine_files = list(
            (self.root / "pilot" / f"{FIXTURE_SOURCE_ID}__2024" / "quarantine").rglob("*.bin")
        )
        self.assertEqual(len(quarantine_files), 2)
        stored_2024 = [row for row in artifacts_2024 if row["status"] == "STORED"]
        spreadsheet = [row for row in stored_2024 if row["file_type"] == "xlsx"]
        self.assertEqual(len(spreadsheet), 1)
        self.assertEqual(spreadsheet[0]["relation_role"], "appendix")
        self.assertTrue(
            spreadsheet[0]["detected_mime"].endswith("spreadsheetml.sheet")
        )

        catalog_2025 = catalog(2025)
        by_id_2025 = {row["source_record_id"]: row for row in catalog_2025}
        self.assertIn("MISSING_ISSUED_DATE", by_id_2025["900205"]["date_reconciliation_flag"])
        self.assertFalse(by_id_2025["900205"]["eligible_for_pilot_denominator"])
        self.assertEqual(by_id_2025["900205"]["status"], "NEEDS_DATE_RECONCILIATION")
        self.assertTrue(by_id_2025["213310"]["eligible_for_pilot_denominator"])
        self.assertFalse(any(row["legal_status_verified"] for row in catalog_2025))

        shared = [row for row in artifacts(2025) if row["file_url"].endswith("78ndcp-1.signed.pdf")]
        self.assertEqual(len(shared), 1)
        self.assertEqual(shared[0]["sha256"], sha256_bytes(SHARED_SYNTHETIC_PDF))
        self.assertTrue(
            (
                self.root
                / "pilot"
                / f"{FIXTURE_SOURCE_ID}__2025"
                / shared[0]["stored_blob_path"]
            ).exists()
        )

        by_id_2020 = {row["source_record_id"]: row for row in catalog(2020)}
        self.assertTrue(by_id_2020["900045"]["is_pre_2020_reference"])
        self.assertFalse(by_id_2020["900045"]["eligible_for_pilot_denominator"])
        self.assertEqual(by_id_2020["900045"]["status"], "EXCLUDED_PRE_2020")
        self.assertTrue(by_id_2020["900059"]["eligible_for_pilot_denominator"])

        by_id_2026 = {row["source_record_id"]: row for row in catalog(2026)}
        self.assertEqual(by_id_2026["900999"]["status"], "EXCLUDED_POST_CUTOFF")
        self.assertIn(
            "POST_CUTOFF_ISSUED_DATE",
            by_id_2026["900999"]["date_reconciliation_flag"],
        )
        self.assertFalse(by_id_2026["900999"]["eligible_for_pilot_denominator"])
        self.assertEqual(by_id_2026["900413"]["observed_effective_date"], "01-12-2026")
        self.assertEqual(by_id_2026["900413"]["relation_role"], "amending")
        self.assertEqual(by_id_2026["900413"]["related_to_document_number"], "104/2025/NĐ-CP")
        self.assertFalse(any(row["legal_status_verified"] for row in catalog(2026)))

    # 6. Deterministic replay into two fresh staging roots.
    def test_synthetic_pilot_is_deterministic(self):
        first = run_src03_synthetic_pilot(self.root / "run-a", CUTOFF)
        second = run_src03_synthetic_pilot(self.root / "run-b", CUTOFF)
        self.assertEqual(first["aggregate"], second["aggregate"])
        self.assertEqual(first["aggregate"]["complete"], 4)
        self.assertEqual(first["aggregate"]["records_observed"], 10)
        self.assertEqual(first["aggregate"]["artifacts_total"], 19)
        self.assertEqual(first["aggregate"]["artifacts_quarantined"], 2)
        self.assertEqual(
            file_hashes(self.root / "run-a"), file_hashes(self.root / "run-b")
        )
        self.assertEqual(len(file_hashes(self.root / "run-a")), len(file_hashes(self.root / "run-b")))

    # 7. CLI writes the worker manifest for the real blocked and synthetic partitions.
    def test_cli_writes_worker_manifest(self):
        import contextlib
        import io

        from luatvn_ai_data_ingestion.src03_adapter import main

        run_dir = self.root / "run"
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(
                [
                    "--run-dir",
                    str(run_dir),
                    "--cutoff-vn",
                    CUTOFF.cutoff_vn,
                    "--cutoff-utc",
                    CUTOFF.cutoff_utc,
                    "--rights",
                    str(ROOT / "experiments/g1/source-rights.json"),
                ]
            )
        self.assertEqual(exit_code, 0)
        manifest_path = run_dir / "staging" / "SRC-03" / "worker-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["worker"], "worker-src03")
        self.assertEqual(manifest["aggregate"]["real_partitions_total"], 7)
        self.assertEqual(manifest["aggregate"]["real_partitions_blocked"], 7)
        self.assertEqual(manifest["aggregate"]["real_network_requests"], 0)
        self.assertEqual(manifest["aggregate"]["real_blobs_written"], 0)
        self.assertEqual(manifest["aggregate"]["synthetic_partitions_complete"], 4)
        self.assertEqual(manifest["aggregate"]["synthetic_counts"]["records_observed"], 10)
        self.assertEqual(manifest["aggregate"]["synthetic_counts"]["artifacts_quarantined"], 2)
        self.assertEqual(len(manifest["quarantine_evidence"]), 2)
        for summary in manifest["synthetic_partitions"]:
            self.assertEqual(summary["status"], "COMPLETED")
        for summary in manifest["real_partitions"]:
            self.assertEqual(summary["status"], "BLOCKED_RIGHTS")
            self.assertEqual(summary["network"]["requests_attempted"], 0)

    # 8. P0-1: Per-operation rights checks (page URL, attachment URL, redirect, date, expiry, size).
    def test_per_operation_rights_enforce_url_redirect_date_expiry_and_size(self):
        doc = self.documents["213310"]
        spec = [
            PartitionRecordSpec(
                page_url=doc.page_url,
                source_record_id=doc.source_record_id,
                domain_candidate="ADM",
                issued_date_hint="01-04-2025",
            )
        ]
        att_urls = [att.file_url for att in doc.attachments]

        # 8a. Attachment URL omitted from approved scope -> blocked before fetching attachment.
        reg_page_only = build_src03_synthetic_registry(
            self.root / "reg-page-only.json",
            urls=[doc.page_url],
        )
        fetched = []

        def tracking_fetcher(url):
            fetched.append(url)
            return self.suite.fetcher(url)

        res_att = self.run_partition(
            name="deny-att",
            year=2025,
            specs=spec,
            fetcher=tracking_fetcher,
            registry=reg_page_only,
        )
        self.assertEqual(res_att["status"], "BLOCKED_RIGHTS")
        self.assertEqual(fetched, [doc.page_url])
        self.assertEqual(list((self.root / "deny-att").rglob("*.bin")), [])

        # 8b. Redirect to unapproved host blocks before storing.
        def redirect_fetcher(url):
            base = self.suite.fetcher(url)
            if url != doc.page_url:
                return FetchResult(
                    url=url,
                    status_code=200,
                    body=base.body,
                    declared_mime=base.declared_mime,
                    final_url="https://evil.example/file.pdf",
                    redirect_urls=("https://evil.example/file.pdf",),
                )
            return base

        res_redir = self.run_partition(
            name="deny-redir",
            year=2025,
            specs=spec,
            fetcher=redirect_fetcher,
        )
        self.assertEqual(res_redir["status"], "BLOCKED_RIGHTS")
        self.assertEqual(list((self.root / "deny-redir").rglob("*.bin")), [])

        # 8c. Actual blob size exceeding max_bytes_per_item blocks before write.
        reg_small = build_src03_synthetic_registry(
            self.root / "reg-small.json",
            urls=[doc.page_url, *att_urls],
            max_bytes_per_item=len(doc.html.encode("utf-8")) + 10,
        )
        big_pdf = b"%PDF-1.4\n" + (b"X" * 10000) + b"\n%%EOF\n"

        def big_fetcher(url):
            base = self.suite.fetcher(url)
            if url == doc.page_url:
                return base
            return FetchResult(url=url, status_code=200, body=big_pdf, declared_mime="application/pdf")

        res_size = self.run_partition(
            name="deny-size",
            year=2025,
            specs=spec,
            fetcher=big_fetcher,
            registry=reg_small,
        )
        self.assertEqual(res_size["status"], "BLOCKED_RIGHTS")
        self.assertEqual(list((self.root / "deny-size").rglob("*.bin")), [])

        # 8d. Parsed issued_date outside [document_from, document_through] blocks before attachments.
        reg_date = build_src03_synthetic_registry(
            self.root / "reg-date.json",
            urls=[doc.page_url, *att_urls],
            document_from="2025-01-01",
            document_through="2025-03-31",
        )
        res_date = run_src03_partition(
            staging_root=self.root / "deny-date",
            registry=reg_date,
            cutoff=CUTOFF,
            partition_id=f"{FIXTURE_SOURCE_ID}__2025",
            year=2025,
            source_id=FIXTURE_SOURCE_ID,
            document_specs=[PartitionRecordSpec(page_url=doc.page_url, source_record_id=doc.source_record_id)],
            fetcher=self.suite.fetcher,
            probe_document_date=datetime(2025, 1, 15, tzinfo=timezone.utc).date(),
        )
        self.assertEqual(res_date["status"], "BLOCKED_RIGHTS")
        self.assertEqual(list((self.root / "deny-date").rglob("*.bin")), [])

        # 8e. Approval window expiring mid-run blocks immediately.
        reg_exp = build_src03_synthetic_registry(
            self.root / "reg-exp.json",
            urls=[doc.page_url, *att_urls],
            approved_at="2026-11-26T00:00:00Z",
            expires_at="2026-11-26T13:00:00Z",
        )
        ticks = iter(
            [
                datetime(2026, 11, 26, 12, 58, 0, tzinfo=timezone.utc),  # preflight
                datetime(2026, 11, 26, 12, 59, 0, tzinfo=timezone.utc),  # page pre-fetch
                datetime(2026, 11, 26, 12, 59, 10, tzinfo=timezone.utc), # page post-fetch
                datetime(2026, 11, 26, 13, 0, 1, tzinfo=timezone.utc),   # expired!
            ]
        )
        res_exp = run_src03_partition(
            staging_root=self.root / "deny-exp",
            registry=reg_exp,
            cutoff=CUTOFF,
            partition_id=f"{FIXTURE_SOURCE_ID}__2025",
            year=2025,
            source_id=FIXTURE_SOURCE_ID,
            document_specs=spec,
            fetcher=self.suite.fetcher,
            at_fn=lambda: next(ticks, datetime(2026, 11, 26, 13, 5, 0, tzinfo=timezone.utc)),
        )
        self.assertEqual(res_exp["status"], "BLOCKED_RIGHTS")
        self.assertEqual(list((self.root / "deny-exp").rglob("*.bin")), [])

    # 9. P0-2: Verified manual-intake CLI and automated pagination batch path.
    def test_manual_intake_cli_and_automated_pagination_batch(self):
        doc = self.documents["213310"]
        intake_dir = self.root / "manual-intake" / "SRC-03"
        (intake_dir / "pages").mkdir(parents=True, exist_ok=True)
        (intake_dir / "files").mkdir(parents=True, exist_ok=True)
        html_bytes = doc.html.encode("utf-8")
        (intake_dir / "pages" / "213310.html").write_bytes(html_bytes)
        att_entries = []
        for idx, att in enumerate(doc.attachments):
            rel = f"files/att_{idx}.pdf"
            (intake_dir / rel).write_bytes(att.body)
            att_entries.append(
                {
                    "file_url": att.file_url,
                    "local_path": rel,
                    "declared_mime": att.declared_mime,
                    "expected_sha256": sha256_bytes(att.body),
                }
            )
        intake_manifest = {
            "schema_version": "1.0",
            "source_id": "SRC-03",
            "data_class": "public",
            "items": [
                {
                    "partition_year": 2025,
                    "source_record_id": "213310",
                    "page_url": doc.page_url,
                    "html_path": "pages/213310.html",
                    "html_sha256": sha256_bytes(html_bytes),
                    "domain_candidate": "ADM",
                    "issued_date": "01-04-2025",
                    "attachments": att_entries,
                }
            ],
        }
        intake_manifest_path = intake_dir / "intake-manifest.json"
        intake_manifest_path.write_text(json.dumps(intake_manifest, ensure_ascii=False), encoding="utf-8")

        manual_reg_path = self.root / "src03-manual-rights.json"
        build_src03_synthetic_registry(
            manual_reg_path,
            source_ids=("SRC-03",),
            urls=[doc.page_url, *[a.file_url for a in doc.attachments]],
            actions=("manual_download", "store"),
            data_class="public",
        )
        run_ok = self.root / "cli-manual-ok"
        with contextlib.redirect_stdout(io.StringIO()):
            code_ok = src03_main(
                [
                    "--mode",
                    "manual-intake",
                    "--run-dir",
                    str(run_ok),
                    "--cutoff-vn",
                    CUTOFF.cutoff_vn,
                    "--cutoff-utc",
                    CUTOFF.cutoff_utc,
                    "--rights",
                    str(manual_reg_path),
                    "--intake-manifest",
                    str(intake_manifest_path),
                ]
            )
        self.assertEqual(code_ok, 0)
        part_manifest = json.loads(
            (run_ok / "staging" / "SRC-03" / "real" / "SRC-03__2025" / "partition-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(part_manifest["status"], "COMPLETED")
        self.assertEqual(part_manifest["access_action"], "manual_download")
        self.assertEqual(part_manifest["network"]["requests_attempted"], 0)
        self.assertFalse(part_manifest["catalog_enumeration_complete"])
        self.assertEqual(part_manifest["counts"]["records_observed"], 1)
        self.assertEqual(part_manifest["counts"]["artifacts_stored"], 5)

        # Automated listing pagination batch
        doc2 = self.documents["900059"]
        list_p1 = "https://vanban.chinhphu.vn/?pageid=27160&p=1"
        list_p2 = "https://vanban.chinhphu.vn/?pageid=27160&p=2"
        html_p1 = (
            f'<html><body><a href="{doc.page_url}">78</a>'
            f'<a href="{list_p2}">Tiếp</a></body></html>'
        )
        html_p2 = f'<html><body><a href="{doc2.page_url}">59</a></body></html>'
        parsed_list = parse_src03_listing_html(html_p1, base_url=list_p1)
        self.assertEqual(parsed_list["document_urls"], [doc.page_url])
        self.assertEqual(parsed_list["next_page_url"], list_p2)

        auto_reg_path = self.root / "src03-auto-rights.json"
        build_src03_synthetic_registry(
            auto_reg_path,
            source_ids=("SRC-03",),
            urls=[
                list_p1,
                list_p2,
                doc.page_url,
                *[a.file_url for a in doc.attachments],
                doc2.page_url,
                *[a.file_url for a in doc2.attachments],
            ],
            actions=("automated_access", "store"),
            data_class="public",
        )
        batch_spec_path = self.root / "src03-batch-spec.json"
        batch_spec_path.write_text(
            json.dumps(
                {
                    "source_id": "SRC-03",
                    "data_class": "public",
                    "partitions": [
                        {
                            "year": 2025,
                            "catalog_enumeration_complete": True,
                            "listing_urls": [list_p1],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        def auto_fetcher(url):
            if url == list_p1:
                return FetchResult(url=url, final_url=url, status_code=200, body=html_p1.encode("utf-8"))
            if url == list_p2:
                return FetchResult(url=url, final_url=url, status_code=200, body=html_p2.encode("utf-8"))
            return self.suite.fetcher(url)

        auto_res = run_src03_automated_batch(
            run_dir=self.root / "auto-run",
            cutoff=CUTOFF,
            registry_path=auto_reg_path,
            batch_spec_path=batch_spec_path,
            fetcher=auto_fetcher,
        )
        self.assertEqual(auto_res["status"], "COMPLETED")
        self.assertTrue(auto_res["results"]["SRC-03__2025"]["catalog_enumeration_complete"])
        self.assertEqual(auto_res["results"]["SRC-03__2025"]["counts"]["records_observed"], 2)


if __name__ == "__main__":
    unittest.main()
