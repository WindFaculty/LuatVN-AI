import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from luatvn_ai_data_ingestion.pilot_schema import RunCutoff, SharedRateLimiter
from luatvn_ai_data_ingestion.source_rights import SourceRegistry
from luatvn_ai_data_ingestion.src01_adapter import (
    FIXTURE_SOURCE_ID,
    FetchResponse,
    build_fixture_registry_payload,
    build_src01_synthetic_fixtures,
    main as src01_main,
    parse_src01_document_html,
    parse_src01_listing_html,
    run_src01_automated_batch,
    run_src01_manual_intake,
    run_src01_partition,
    run_src01_synthetic_pilot,
)

ROOT = Path(__file__).resolve().parents[3]
CUTOFF = RunCutoff(
    run_id="G1-PILOT-SRC01-SRC03-20261126-01",
    cutoff_utc="2026-11-26T12:58:39Z",
    cutoff_vn="2026-11-26T19:58:39+07:00",
)


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def read_jsonl(path):
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def hash_tree(root):
    root = Path(root)
    return {
        path.relative_to(root).as_posix(): sha256_bytes(path.read_bytes())
        for path in root.rglob("*")
        if path.is_file()
    }


class Src01AdapterTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.fixtures = build_src01_synthetic_fixtures()

    def registry(self, sources=(FIXTURE_SOURCE_ID,), name="rights.json"):
        payload = build_fixture_registry_payload(
            source_ids=sources,
            urls=[*self.fixtures["page_urls"], *self.fixtures["attachment_urls"]],
        )
        path = self.root / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return SourceRegistry(path)

    def fixture_documents(self, year):
        return [
            document
            for document in self.fixtures["documents"]
            if document["partition_year"] == year
        ]

    def run_fixture_partition(
        self,
        year,
        root,
        *,
        registry=None,
        fetcher=None,
        source_id=FIXTURE_SOURCE_ID,
        rate_limiter=None,
        sleep_func=None,
        documents=None,
    ):
        documents = documents if documents is not None else self.fixture_documents(year)
        return run_src01_partition(
            registry=registry or self.registry(),
            cutoff=CUTOFF,
            source_id=source_id,
            year=year,
            staging_dir=root,
            documents=documents,
            fetcher=fetcher or self.fixtures["blobs"].__getitem__,
            rate_limiter=rate_limiter,
            probe_url=documents[0]["page_url"],
            observed_at=CUTOFF.cutoff_vn,
            sleep_func=sleep_func,
        )

    # 1. Real registry blocks SRC-01 for every partition with zero fetches/blobs.
    def test_real_registry_blocks_all_partitions_without_fetch_or_blob(self):
        live = SourceRegistry(ROOT / "experiments/g1/source-rights.json")
        calls = []

        def fetcher(url):
            calls.append(url)
            return FetchResponse(status_code=200, body=b"should never be fetched")

        staging = self.root / "real-blocked"
        for year in range(2020, 2027):
            with self.subTest(year=year):
                result = run_src01_partition(
                    registry=live,
                    cutoff=CUTOFF,
                    source_id="SRC-01",
                    year=year,
                    staging_dir=staging,
                    documents=[{"page_url": f"https://congbao.chinhphu.vn/van-ban/test-{year}/1.htm"}],
                    fetcher=fetcher,
                )
                self.assertEqual(result["status"], "BLOCKED_RIGHTS")
                self.assertEqual(result["rights_status"], "BLOCKED_RIGHTS")
                self.assertEqual(result["fetch_attempts"], 0)
                partition = Path(result["partition_dir"])
                self.assertEqual((partition / "catalog.jsonl").read_text(encoding="utf-8"), "")
                self.assertEqual((partition / "artifacts.jsonl").read_text(encoding="utf-8"), "")
                manifest = read_json(partition / "partition-manifest.json")
                self.assertEqual(manifest["rights_status"], "BLOCKED_RIGHTS")
                self.assertEqual(manifest["counts"]["documents_observed"], 0)
                self.assertEqual(manifest["counts"]["artifacts_total"], 0)
                checkpoint = read_json(partition / "checkpoint.json")
                self.assertEqual(checkpoint["rights_status"], "BLOCKED_RIGHTS")
                self.assertEqual(checkpoint["status"], "BLOCKED_RIGHTS")

        self.assertEqual(calls, [])
        self.assertEqual(list(staging.rglob("*.bin")), [])

    # 2. Parser separates dates, keeps continuation issues and exact CDN links.
    def test_parser_reads_detail_rows_from_public_layout(self):
        html = """
        <div class="document--focus">
            <div class="table">
                <div class="row">
                    <span class="name">Số, ký hiệu</span>
                    <div class="value"><span class="child-value">1/2026/N&#272;-CP</span></div>
                </div>
                <div class="row">
                    <span class="name">Ngày ban hành</span>
                    <div class="value"><span class="child-value">16/11/2026</span></div>
                </div>
            </div>
        </div>
        <div class="row"><span class="name">Ngày ban hành</span><div class="value">01/01/1900</div></div>
        <a href="/van-ban/nghi-dinh-so-1-2026-nd-cp-123456/340.htm">588</a>
        <a href="/cong-bao/588-47615.htm">588</a>
        """
        parsed = parse_src01_document_html(
            html, page_url="https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-1-2026-nd-cp-123456.htm",
        )
        self.assertEqual(parsed["source_record_id"], "123456")
        self.assertEqual(parsed["document_number"], "1/2026/NĐ-CP")
        self.assertEqual(parsed["issued_date"], "16/11/2026")
        self.assertEqual(parsed["gazette_issue"], "588")
        self.assertEqual(parsed["continuation_issues"], ["588"])

    def test_parser_extracts_multi_issue_gazette_and_cdn_attachments(self):
        document = next(
            item for item in self.fixtures["documents"] if item["source_record_id"] == "55991"
        )
        parsed = parse_src01_document_html(document["html"], page_url=document["page_url"])

        self.assertEqual(parsed["document_number"], "78/2025/NĐ-CP")
        self.assertEqual(parsed["document_type"], "Nghị định")
        self.assertEqual(parsed["issuer"], "CHÍNH PHỦ")
        self.assertEqual(parsed["issued_date"], "01/04/2025")
        self.assertEqual(parsed["gazette_published_date"], "03/04/2025")
        self.assertEqual(parsed["observed_effective_date"], "01/04/2025")
        self.assertNotEqual(parsed["issued_date"], parsed["gazette_published_date"])
        self.assertEqual(parsed["gazette_issue"], "649+650/2025")
        self.assertEqual(parsed["gazette_page"], "1-52")
        self.assertIn("78/2025/NĐ-CP", parsed["title"])
        self.assertEqual(
            parsed["continuation_issues"], ["649 + 650", "651 + 652", "653 + 654"]
        )
        self.assertEqual(
            [link["url"].rsplit("/", 1)[-1] for link in parsed["continuation_links"]],
            ["56011.htm", "55988.htm", "55991.htm"],
        )
        self.assertEqual(len(parsed["attachments"]), 6)
        self.assertEqual(
            sorted({item["file_type"] for item in parsed["attachments"]}), ["doc", "pdf"]
        )
        for attachment in parsed["attachments"]:
            self.assertTrue(
                attachment["file_url"].startswith(
                    "https://g7.cdnchinhphu.vn/api/download/stream?Url="
                )
            )
            self.assertTrue(attachment["file_url"].endswith((".pdf", ".doc")))
            self.assertEqual(attachment["parent_id"], "44704")
            self.assertTrue(attachment["attachment_id"].startswith("att-55991-"))
        self.assertEqual(parsed["source_record_id"], "55991")

    # 3. Interrupted run preserves completed rows; resume converges on the clean run.
    def test_checkpoint_interruption_and_resume_are_identical(self):
        clean_root = self.root / "clean"
        clean = self.run_fixture_partition(2025, clean_root)
        self.assertEqual(clean["status"], "COMPLETED")
        partition = clean_root / "FIXTURE-SRC-01__2025"
        clean_hashes = hash_tree(partition)

        interrupted_root = self.root / "interrupted"
        calls = {"count": 0}

        def flaky_fetcher(url):
            calls["count"] += 1
            if calls["count"] == 8:
                raise RuntimeError("simulated interruption")
            return self.fixtures["blobs"][url]

        with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
            self.run_fixture_partition(2025, interrupted_root, fetcher=flaky_fetcher)
        interrupted_partition = interrupted_root / "FIXTURE-SRC-01__2025"
        interrupted_rows = read_jsonl(interrupted_partition / "catalog.jsonl")
        self.assertEqual([row["source_record_id"] for row in interrupted_rows], ["55991"])
        self.assertNotIn(
            "56000", [row["source_record_id"] for row in interrupted_rows]
        )

        resumed = self.run_fixture_partition(2025, interrupted_root)
        self.assertEqual(resumed["status"], "COMPLETED")
        self.assertEqual(hash_tree(interrupted_partition), clean_hashes)

        catalog = read_jsonl(interrupted_partition / "catalog.jsonl")
        artifacts = read_jsonl(interrupted_partition / "artifacts.jsonl")
        self.assertEqual(len(catalog), 3)
        self.assertEqual(len({row["source_record_id"] for row in catalog}), 3)
        self.assertEqual(len(artifacts), len({row["attachment_id"] for row in artifacts}))
        manifest = read_json(interrupted_partition / "partition-manifest.json")
        self.assertEqual(manifest["counts"]["documents_observed"], 3)
        self.assertEqual(manifest["counts"]["artifacts_total"], 10)

    # 4. Network stop policy and shared chinhphu.vn rate bucket.
    def test_network_stops_and_shared_rate_limit(self):
        document = next(
            item for item in self.fixtures["documents"] if item["source_record_id"] == "50059"
        )
        without_html = {key: value for key, value in document.items() if key != "html"}
        scenarios = {
            "403": (FetchResponse(status_code=403, body=b"Forbidden"), "STOP_HTTP_403"),
            "captcha": (
                FetchResponse(status_code=200, body=b"<html>Please verify you are human</html>"),
                "STOP_CAPTCHA",
            ),
            "tls": (
                FetchResponse(status_code=None, tls_error="CERTIFICATE_VERIFY_FAILED"),
                "STOP_TLS_ERROR",
            ),
            "429": (
                FetchResponse(status_code=429, body=b"", retry_after="120"),
                "STOP_HTTP_429",
            ),
            "retry-budget": (FetchResponse(status_code=500, body=b"error"), "STOP_RETRY_BUDGET_EXHAUSTED"),
        }
        for name, (response, expected_status) in scenarios.items():
            with self.subTest(name=name):
                root = self.root / name
                result = self.run_fixture_partition(
                    2020,
                    root,
                    documents=[without_html],
                    fetcher=lambda url, response=response: response,
                    sleep_func=lambda wait: None,
                )
                self.assertEqual(result["status"], expected_status)
                self.assertEqual(result["rights_status"], "APPROVED")
                partition = root / "FIXTURE-SRC-01__2020"
                self.assertEqual(read_jsonl(partition / "catalog.jsonl"), [])
                errors = read_jsonl(partition / "errors.jsonl")
                self.assertEqual([row["code"] for row in errors], [expected_status])
                checkpoint = read_json(partition / "checkpoint.json")
                self.assertEqual(checkpoint["status"], expected_status)

        dual_registry = self.registry(
            sources=(FIXTURE_SOURCE_ID, "FIXTURE-SRC-99"), name="dual-rights.json"
        )
        limiter = SharedRateLimiter(
            per_source_max_per_minute=10,
            shared_infra_max_per_minute=1,
            clock=lambda: 1000.0,
        )
        limiter.acquire("FIXTURE-SRC-99")
        fetched = []

        def unexpected_fetch(url):
            fetched.append(url)
            return b""

        result = run_src01_partition(
            registry=dual_registry,
            cutoff=CUTOFF,
            source_id=FIXTURE_SOURCE_ID,
            year=2020,
            staging_dir=self.root / "shared-rate",
            documents=[document],
            fetcher=unexpected_fetch,
            rate_limiter=limiter,
            probe_url=document["page_url"],
            observed_at=CUTOFF.cutoff_vn,
        )
        self.assertEqual(result["status"], "SHARED_INFRA_RATE_LIMIT")
        self.assertEqual(result["fetch_attempts"], 0)
        self.assertEqual(fetched, [])

    # 5. Quarantine, boundary, date reconciliation and shared hash evidence.
    def test_quarantine_boundaries_and_shared_hash(self):
        run_dir = self.root / "pilot"
        pilot = run_src01_synthetic_pilot(run_dir=run_dir, cutoff=CUTOFF)
        self.assertEqual(pilot["status"], "COMPLETED")
        root = run_dir / "staging" / "SRC-01" / "synthetic"

        catalogs = []
        artifacts = []
        for partition_id in ("FIXTURE-SRC-01__2020", "FIXTURE-SRC-01__2025", "FIXTURE-SRC-01__2026"):
            partition = root / partition_id
            catalogs.extend(read_jsonl(partition / "catalog.jsonl"))
            artifacts.extend(read_jsonl(partition / "artifacts.jsonl"))

        by_number = {row["document_number"]: row for row in catalogs}
        self.assertTrue(by_number["91/2015/QH13"]["is_pre_2020_reference"])
        self.assertFalse(by_number["91/2015/QH13"]["eligible_for_pilot_denominator"])
        self.assertEqual(by_number["91/2015/QH13"]["year"], 2015)
        self.assertFalse(by_number["414/2026/NĐ-CP"]["eligible_for_pilot_denominator"])
        self.assertIn(
            "POST_CUTOFF_ISSUED_DATE", by_number["414/2026/NĐ-CP"]["date_reconciliation_flag"]
        )
        self.assertTrue(by_number["59/2020/QH14"]["eligible_for_pilot_denominator"])
        self.assertIn(
            "GAZETTE_BEFORE_ISSUED_DATE",
            by_number["101/2025/QĐ-TTg"]["date_reconciliation_flag"],
        )
        self.assertEqual(by_number["99/2025/TT-BTNMT"]["gazette_page"], "")
        for row in catalogs:
            self.assertFalse(row["legal_status_verified"])
            self.assertEqual(row["data_origin"], "SYNTHETIC_FIXTURE")

        quarantined = [row for row in artifacts if row["status"] == "QUARANTINED"]
        reasons = {row["quarantine_reason"] for row in quarantined}
        self.assertTrue(any(reason.startswith("TRUNCATED_OR_CORRUPT_PDF") for reason in reasons))
        self.assertTrue(any(reason.startswith("MIME_MISMATCH") for reason in reasons))
        self.assertEqual(len(quarantined), 2)
        for row in quarantined:
            partition = root / row["partition_id"]
            quarantine_path = partition / "quarantine" / f"{row['sha256']}.bin"
            self.assertTrue(quarantine_path.exists())
            self.assertEqual(sha256_bytes(quarantine_path.read_bytes()), row["sha256"])
            self.assertEqual(row["stored_blob_path"], "")

        stored = [row for row in artifacts if row["status"] == "STORED"]
        self.assertEqual(len(stored), 14)
        for row in stored:
            blob = root / row["partition_id"] / row["stored_blob_path"]
            self.assertTrue(blob.exists())
            self.assertEqual(sha256_bytes(blob.read_bytes()), row["sha256"])

        shared = next(row for row in artifacts if row["attachment_id"] == "att-55991-649-650-pdf")
        self.assertEqual(shared["sha256"], self.fixtures["shared_pdf_sha256"])
        self.assertEqual(
            shared["stored_blob_path"],
            f"blobs/{shared['sha256'][:2]}/{shared['sha256']}.bin",
        )
        self.assertTrue((root / shared["partition_id"] / shared["stored_blob_path"]).exists())

        manifest = read_json(run_dir / "staging" / "SRC-01" / "worker-manifest.json")
        self.assertTrue(manifest["validation"]["real_partitions_blocked"])
        self.assertTrue(manifest["validation"]["synthetic_all_completed"])
        self.assertEqual(manifest["validation"]["synthetic_quarantined"], 2)
        self.assertEqual(
            manifest["validation"]["shared_hash_sha256"], self.fixtures["shared_pdf_sha256"]
        )

    # 6. Synthetic pilot is deterministic across independent run directories.
    def test_synthetic_pilot_is_deterministic(self):
        first = run_src01_synthetic_pilot(run_dir=self.root / "first", cutoff=CUTOFF)
        second = run_src01_synthetic_pilot(run_dir=self.root / "second", cutoff=CUTOFF)
        self.assertEqual(first["status"], "COMPLETED")
        self.assertEqual(second["status"], "COMPLETED")

        first_root = self.root / "first" / "staging" / "SRC-01"
        second_root = self.root / "second" / "staging" / "SRC-01"
        self.assertEqual(hash_tree(first_root), hash_tree(second_root))

        for partition_id in ("FIXTURE-SRC-01__2020", "FIXTURE-SRC-01__2025", "FIXTURE-SRC-01__2026"):
            first_catalog = read_jsonl(first_root / "synthetic" / partition_id / "catalog.jsonl")
            second_catalog = read_jsonl(second_root / "synthetic" / partition_id / "catalog.jsonl")
            self.assertEqual(
                [row["source_record_id"] for row in first_catalog],
                [row["source_record_id"] for row in second_catalog],
            )
            first_artifacts = read_jsonl(first_root / "synthetic" / partition_id / "artifacts.jsonl")
            second_artifacts = read_jsonl(second_root / "synthetic" / partition_id / "artifacts.jsonl")
            self.assertEqual(
                [row["sha256"] for row in first_artifacts],
                [row["sha256"] for row in second_artifacts],
            )
            self.assertEqual(len(first_catalog), len(second_catalog))
            self.assertEqual(len(first_artifacts), len(second_artifacts))

    # 7. P0-1: Per-operation rights checks (page URL, file URL, redirect, date, expiry, size).
    def test_per_operation_rights_enforce_url_redirect_date_expiry_and_size(self):
        doc_50059 = next(
            item for item in self.fixtures["documents"] if item["source_record_id"] == "50059"
        )
        page_url = doc_50059["page_url"]
        att_urls = doc_50059["attachment_urls"]

        # 7a. Attachment URL omitted from approved scope.url must block before fetching that file.
        payload_no_att = build_fixture_registry_payload(
            source_ids=(FIXTURE_SOURCE_ID,),
            urls=[page_url],
        )
        reg_no_att_path = self.root / "reg-no-att.json"
        reg_no_att_path.write_text(json.dumps(payload_no_att), encoding="utf-8")
        reg_no_att = SourceRegistry(reg_no_att_path)
        fetched_urls = []

        def tracking_fetcher(url):
            fetched_urls.append(url)
            return self.fixtures["blobs"][url]

        res_no_att = self.run_fixture_partition(
            2020,
            self.root / "deny-att",
            registry=reg_no_att,
            documents=[doc_50059],
            fetcher=tracking_fetcher,
        )
        self.assertEqual(res_no_att["status"], "BLOCKED_RIGHTS")
        self.assertEqual(fetched_urls, [])
        self.assertEqual(list((self.root / "deny-att").rglob("*.bin")), [])

        # 7b. Redirect to an unapproved final URL must block before storing blob.
        def redirecting_fetcher(url):
            return FetchResponse(
                status_code=200,
                body=self.fixtures["blobs"][url],
                final_url="https://unapproved.example/leak.pdf",
                redirect_urls=("https://unapproved.example/leak.pdf",),
            )

        res_redir = self.run_fixture_partition(
            2020,
            self.root / "deny-redirect",
            documents=[doc_50059],
            fetcher=redirecting_fetcher,
        )
        self.assertEqual(res_redir["status"], "BLOCKED_RIGHTS")
        self.assertEqual(list((self.root / "deny-redirect").rglob("*.bin")), [])

        # 7c. Oversized attachment payload exceeds max_bytes_per_item -> blocked before write.
        payload_tiny = build_fixture_registry_payload(
            source_ids=(FIXTURE_SOURCE_ID,),
            urls=[page_url, *att_urls],
            max_bytes_per_item=len(doc_50059["html"].encode("utf-8")) + 10,
        )
        reg_tiny_path = self.root / "reg-tiny.json"
        reg_tiny_path.write_text(json.dumps(payload_tiny), encoding="utf-8")
        oversized_pdf = b"%PDF-1.4\n" + (b"A" * 5000) + b"\n%%EOF\n"
        res_size = self.run_fixture_partition(
            2020,
            self.root / "deny-size",
            registry=SourceRegistry(reg_tiny_path),
            documents=[doc_50059],
            fetcher=lambda url: FetchResponse(status_code=200, body=oversized_pdf, final_url=url),
        )
        self.assertEqual(res_size["status"], "BLOCKED_RIGHTS")
        self.assertEqual(list((self.root / "deny-size").rglob("*.bin")), [])

        # 7d. Document issued_date outside [document_from, document_through] blocked before fetch.
        payload_narrow_date = build_fixture_registry_payload(
            source_ids=(FIXTURE_SOURCE_ID,),
            urls=[page_url, *att_urls],
            document_from="2020-01-01",
            document_through="2020-05-01",
        )
        reg_date_path = self.root / "reg-date.json"
        reg_date_path.write_text(json.dumps(payload_narrow_date), encoding="utf-8")
        res_date = self.run_fixture_partition(
            2020,
            self.root / "deny-date",
            registry=SourceRegistry(reg_date_path),
            documents=[doc_50059],  # issued 17/06/2020
            fetcher=tracking_fetcher,
        )
        self.assertEqual(res_date["status"], "BLOCKED_RIGHTS")
        self.assertEqual(fetched_urls, [])

        # 7e. Approval expiring mid-run via at_fn blocks subsequent operations.
        payload_exp = build_fixture_registry_payload(
            source_ids=(FIXTURE_SOURCE_ID,),
            urls=[page_url, *att_urls],
            approved_at="2026-11-26T00:00:00Z",
            expires_at="2026-11-26T13:00:00Z",
        )
        reg_exp_path = self.root / "reg-exp.json"
        reg_exp_path.write_text(json.dumps(payload_exp), encoding="utf-8")
        ticks = iter(
            [
                datetime(2026, 11, 26, 12, 58, 0, tzinfo=timezone.utc),  # preflight ok
                datetime(2026, 11, 26, 12, 59, 0, tzinfo=timezone.utc),  # page store ok
                datetime(2026, 11, 26, 13, 0, 1, tzinfo=timezone.utc),   # expired on attachment!
            ]
        )
        res_exp = run_src01_partition(
            registry=SourceRegistry(reg_exp_path),
            cutoff=CUTOFF,
            source_id=FIXTURE_SOURCE_ID,
            year=2020,
            staging_dir=self.root / "deny-expiry",
            documents=[doc_50059],
            fetcher=self.fixtures["blobs"].__getitem__,
            probe_url=page_url,
            at_fn=lambda: next(ticks, datetime(2026, 11, 26, 13, 5, 0, tzinfo=timezone.utc)),
        )
        self.assertEqual(res_exp["status"], "BLOCKED_RIGHTS")
        self.assertEqual(list((self.root / "deny-expiry").rglob("*.bin")), [])

    # 8. P0-1: Cross-process SharedRateLimiter enforces per-source and shared infra caps.
    def test_cross_process_shared_rate_limiter_enforces_source_and_infra_caps(self):
        db_path = self.root / "shared-rate.sqlite"
        worker_code = "\n".join(
            [
                "import json, sys",
                "from luatvn_ai_data_ingestion.pilot_schema import NetworkPolicyStop, SharedRateLimiter",
                "db, src, attempts = sys.argv[1], sys.argv[2], int(sys.argv[3])",
                "lim = SharedRateLimiter(",
                "    per_source_max_per_minute=2,",
                "    shared_infra_max_per_minute=3,",
                "    state_path=db,",
                "    clock=lambda: 1700000000.0,",
                ")",
                "out = []",
                "for _ in range(attempts):",
                "    try:",
                "        lim.acquire(src, 'chinhphu.vn')",
                "        out.append('OK')",
                "    except NetworkPolicyStop as e:",
                "        out.append(e.code)",
                "print(json.dumps(out))",
            ]
        )
        env = {**os.environ, "PYTHONPATH": str(ROOT / "services" / "data-ingestion" / "src")}
        p1 = subprocess.run(
            [sys.executable, "-c", worker_code, str(db_path), "SRC-01", "3"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        p2 = subprocess.run(
            [sys.executable, "-c", worker_code, str(db_path), "SRC-03", "3"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        res1 = json.loads(p1.stdout)
        res2 = json.loads(p2.stdout)
        self.assertEqual(res1, ["OK", "OK", "SOURCE_RATE_LIMIT"])
        self.assertEqual(res2, ["OK", "SHARED_INFRA_RATE_LIMIT", "SHARED_INFRA_RATE_LIMIT"])

    # 9. P0-2: Verified manual-intake CLI and automated pagination batch path.
    def test_manual_intake_cli_and_automated_pagination_batch(self):
        doc_55991 = next(
            item for item in self.fixtures["documents"] if item["source_record_id"] == "55991"
        )
        intake_dir = self.root / "manual-intake" / "SRC-01"
        (intake_dir / "pages").mkdir(parents=True, exist_ok=True)
        (intake_dir / "files").mkdir(parents=True, exist_ok=True)
        html_bytes = doc_55991["html"].encode("utf-8")
        (intake_dir / "pages" / "55991.html").write_bytes(html_bytes)
        att_entries = []
        for idx, file_url in enumerate(doc_55991["attachment_urls"]):
            payload = self.fixtures["blobs"][file_url]
            rel = f"files/att_{idx}.bin"
            (intake_dir / rel).write_bytes(payload)
            att_entries.append(
                {
                    "file_url": file_url,
                    "local_path": rel,
                    "expected_sha256": sha256_bytes(payload),
                }
            )
        intake_manifest = {
            "schema_version": "1.0",
            "source_id": "SRC-01",
            "data_class": "public",
            "items": [
                {
                    "partition_year": 2025,
                    "source_record_id": "55991",
                    "page_url": doc_55991["page_url"],
                    "html_path": "pages/55991.html",
                    "html_sha256": sha256_bytes(html_bytes),
                    "domain_candidate": "ADM",
                    "relation_role": "gazette_publication",
                    "issued_date": "01/04/2025",
                    "attachments": att_entries,
                }
            ],
        }
        intake_manifest_path = intake_dir / "intake-manifest.json"
        intake_manifest_path.write_text(json.dumps(intake_manifest, ensure_ascii=False), encoding="utf-8")

        # 9a. Fail-closed with live PENDING_RIGHTS registry via CLI.
        run_blocked = self.root / "cli-manual-blocked"
        with contextlib.redirect_stdout(io.StringIO()):
            code_blocked = src01_main(
                [
                    "--mode",
                    "manual-intake",
                    "--run-dir",
                    str(run_blocked),
                    "--cutoff-vn",
                    CUTOFF.cutoff_vn,
                    "--cutoff-utc",
                    CUTOFF.cutoff_utc,
                    "--registry",
                    str(ROOT / "experiments/g1/source-rights.json"),
                    "--intake-manifest",
                    str(intake_manifest_path),
                ]
            )
        self.assertEqual(code_blocked, 0)
        self.assertEqual(list((run_blocked / "staging" / "SRC-01" / "real").rglob("*.bin")), [])

        # 9b. Succeeds with approved manual_download + store registry via CLI.
        manual_reg_payload = build_fixture_registry_payload(
            source_ids=("SRC-01",),
            urls=[doc_55991["page_url"], *doc_55991["attachment_urls"]],
            actions=("manual_download", "store"),
            data_class="public",
            revision="g1-manual-test-v1",
        )
        manual_reg_path = self.root / "manual-rights.json"
        manual_reg_path.write_text(json.dumps(manual_reg_payload), encoding="utf-8")
        run_ok = self.root / "cli-manual-ok"
        with contextlib.redirect_stdout(io.StringIO()):
            code_ok = src01_main(
                [
                    "--mode",
                    "manual-intake",
                    "--run-dir",
                    str(run_ok),
                    "--cutoff-vn",
                    CUTOFF.cutoff_vn,
                    "--cutoff-utc",
                    CUTOFF.cutoff_utc,
                    "--registry",
                    str(manual_reg_path),
                    "--intake-manifest",
                    str(intake_manifest_path),
                ]
            )
        self.assertEqual(code_ok, 0)
        part_dir = run_ok / "staging" / "SRC-01" / "real" / "SRC-01__2025"
        manifest = read_json(part_dir / "partition-manifest.json")
        self.assertEqual(manifest["status"], "COMPLETED")
        self.assertEqual(manifest["access_action"], "manual_download")
        self.assertEqual(manifest["network"]["requests_attempted"], 0)
        self.assertFalse(manifest["catalog_enumeration_complete"])
        self.assertEqual(manifest["counts"]["documents_observed"], 1)
        self.assertEqual(manifest["counts"]["stored_blobs"], 6)

        # 9c. Automated pagination batch discovers 2 pages -> 2 documents & marks enumeration complete.
        doc_50059 = next(
            item for item in self.fixtures["documents"] if item["source_record_id"] == "50059"
        )
        doc_57011 = next(
            item for item in self.fixtures["documents"] if item["source_record_id"] == "57011"
        )
        list_p1 = "https://congbao.chinhphu.vn/van-ban?page=1"
        list_p2 = "https://congbao.chinhphu.vn/van-ban?page=2"
        html_p1 = (
            f'<html><body><a href="{doc_50059["page_url"]}">59</a>'
            f'<a rel="next" href="{list_p2}">Tiếp</a></body></html>'
        )
        html_p2 = f'<html><body><a href="{doc_57011["page_url"]}">413</a></body></html>'
        parsed_list = parse_src01_listing_html(html_p1, base_url=list_p1)
        self.assertEqual(parsed_list["document_urls"], [doc_50059["page_url"]])
        self.assertEqual(parsed_list["next_page_url"], list_p2)

        auto_reg_payload = build_fixture_registry_payload(
            source_ids=("SRC-01",),
            urls=[
                list_p1,
                list_p2,
                doc_50059["page_url"],
                *doc_50059["attachment_urls"],
                doc_57011["page_url"],
                *doc_57011["attachment_urls"],
            ],
            actions=("automated_access", "store"),
            data_class="public",
            revision="g1-auto-test-v1",
        )
        auto_reg_path = self.root / "auto-rights.json"
        auto_reg_path.write_text(json.dumps(auto_reg_payload), encoding="utf-8")
        batch_spec = {
            "source_id": "SRC-01",
            "data_class": "public",
            "partitions": [
                {
                    "year": 2025,
                    "catalog_enumeration_complete": True,
                    "listing_urls": [list_p1],
                }
            ],
        }
        batch_spec_path = self.root / "batch-spec.json"
        batch_spec_path.write_text(json.dumps(batch_spec), encoding="utf-8")
        mock_pages = {
            list_p1: html_p1.encode("utf-8"),
            list_p2: html_p2.encode("utf-8"),
            doc_50059["page_url"]: doc_50059["html"].encode("utf-8"),
            doc_57011["page_url"]: doc_57011["html"].encode("utf-8"),
            **self.fixtures["blobs"],
        }
        auto_res = run_src01_automated_batch(
            run_dir=self.root / "auto-run",
            cutoff=CUTOFF,
            registry_path=auto_reg_path,
            batch_spec_path=batch_spec_path,
            fetcher=lambda url: FetchResponse(status_code=200, body=mock_pages[url], final_url=url),
        )
        self.assertEqual(auto_res["status"], "COMPLETED")
        part_res = auto_res["results"]["SRC-01__2025"]
        self.assertTrue(part_res["catalog_enumeration_complete"])
        self.assertEqual(part_res["counts"]["documents_observed"], 2)


if __name__ == "__main__":
    unittest.main()
