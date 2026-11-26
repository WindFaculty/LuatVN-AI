"""Measure real G1 5-capability storage & indexing sizing on isolated local PostgreSQL 18.6."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import secrets
import shutil
import socket
import subprocess
import time
from pathlib import Path
from statistics import mean
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]


def percentile(values: list[float], q: float) -> float:
    s = sorted(values)
    idx = min(len(s) - 1, max(0, int((q * len(s)) + 0.999999) - 1))
    return round(s[idx], 2)


def measure_all(client: list[str], env: dict[str, str], work: Path, chunks_path: Path, graph_path: Path, catalog_counts: dict, prev_dir: Path) -> dict:
    def query(sql: str, *, database: str = "postgres") -> str:
        res = subprocess.run([*client[:-1], database, "-v", "ON_ERROR_STOP=1", "-Atc", sql], env=env, check=True, capture_output=True, encoding="utf-8")
        return res.stdout.strip()

    # 1. Load normalized chunks -> relational + B-tree + FTS GIN
    rows_csv = work / "chunks.csv"
    chunk_count = 0
    with chunks_path.open(encoding="utf-8") as src, rows_csv.open("w", newline="", encoding="utf-8") as dst:
        w = csv.writer(dst)
        for line in src:
            row = json.loads(line)
            if row["review_state"] != "PENDING_REVIEW":
                raise ValueError("chunks must be PENDING_REVIEW")
            w.writerow((row["artifact_sha256"], row["unit_kind"], row["unit"], row["offset"], row["text"]))
            chunk_count += 1

    query("""CREATE TABLE public.g1_chunk (
        artifact_sha256 text NOT NULL, unit_kind text NOT NULL, unit integer NOT NULL,
        start_offset integer NOT NULL, content text NOT NULL
    )""")
    t0 = time.perf_counter()
    with rows_csv.open("rb") as fh:
        subprocess.run([*client, "-v", "ON_ERROR_STOP=1", "-c", "\\copy public.g1_chunk FROM STDIN WITH (FORMAT csv)"], stdin=fh, env=env, check=True, capture_output=True)
    query("CREATE INDEX idx_chunk_pk ON public.g1_chunk (artifact_sha256, unit_kind, unit, start_offset)")
    rel_load_s = round(time.perf_counter() - t0, 3)

    t1 = time.perf_counter()
    query("CREATE INDEX idx_chunk_fts_simple ON public.g1_chunk USING GIN (to_tsvector('simple', content))")
    fts_build_s = round(time.perf_counter() - t1, 3)

    t2 = time.perf_counter()
    fts_hits = int(query("SELECT count(*) FROM public.g1_chunk WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', 'doanh nghiệp hiệu lực')"))
    fts_query_ms = round((time.perf_counter() - t2) * 1000, 2)

    rel_table_b, btree_b, fts_b, content_b = map(int, query("""
        SELECT pg_table_size('public.g1_chunk'),
               pg_relation_size('idx_chunk_pk'),
               pg_relation_size('idx_chunk_fts_simple'),
               sum(octet_length(content))
        FROM public.g1_chunk
    """).split("|"))

    # Backup + restore integrity
    dump_file = work / "g1_sizing.dump"
    conn_args = client[3:-2]
    tb = time.perf_counter()
    subprocess.run(["pg_dump", *conn_args, "-w", "-Fc", "--table=public.g1_chunk", "-f", str(dump_file), "postgres"], env=env, check=True)
    backup_s = round(time.perf_counter() - tb, 3)
    query("CREATE DATABASE g1_restore_check")
    tr = time.perf_counter()
    subprocess.run(["pg_restore", *conn_args, "-w", "--exit-on-error", "-d", "g1_restore_check", str(dump_file)], env=env, check=True)
    restore_s = round(time.perf_counter() - tr, 3)

    fp_sql = "SELECT count(*) || '|' || md5(string_agg(md5(g1_chunk::text), '' ORDER BY artifact_sha256, unit_kind, unit, start_offset)) FROM public.g1_chunk"
    assert query(fp_sql) == query(fp_sql, database="g1_restore_check"), "Restore integrity mismatch!"

    # 2. Load graph candidate nodes/edges -> relational graph baseline + 2-hop CTE benchmark
    graph_rows = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes_csv = work / "nodes.csv"
    edges_csv = work / "edges.csv"
    n_cnt = e_cnt = 0
    with nodes_csv.open("w", newline="", encoding="utf-8") as nf, edges_csv.open("w", newline="", encoding="utf-8") as ef:
        nw, ew = csv.writer(nf), csv.writer(ef)
        for g in graph_rows:
            if g["unit"] == "node":
                nw.writerow((g["id"], g["family_id"], g["domain"], g["layer"], g["type"], g["source_id"], g["review_state"]))
                n_cnt += 1
            else:
                ew.writerow((g["id"], g["family_id"], g["domain"], g["layer"], g["type"], g["source_id"], g["target_id"], g["review_state"]))
                e_cnt += 1

    query("CREATE TABLE public.g1_graph_node (id text PRIMARY KEY, family_id text, domain text, layer text, node_type text, node_key text, review_state text)")
    query("CREATE TABLE public.g1_graph_edge (id text PRIMARY KEY, family_id text, domain text, layer text, edge_type text, src_key text, tgt_key text, review_state text)")
    with nodes_csv.open("rb") as fh:
        subprocess.run([*client, "-v", "ON_ERROR_STOP=1", "-c", "\\copy public.g1_graph_node FROM STDIN WITH (FORMAT csv)"], stdin=fh, env=env, check=True, capture_output=True)
    with edges_csv.open("rb") as fh:
        subprocess.run([*client, "-v", "ON_ERROR_STOP=1", "-c", "\\copy public.g1_graph_edge FROM STDIN WITH (FORMAT csv)"], stdin=fh, env=env, check=True, capture_output=True)
    query("CREATE INDEX idx_graph_src_tgt ON public.g1_graph_edge (src_key, tgt_key)")
    t3 = time.perf_counter()
    hop_cnt = int(query("""
        WITH RECURSIVE reach(k, depth) AS (
            SELECT src_key, 1 FROM public.g1_graph_edge
            UNION ALL
            SELECT e.tgt_key, r.depth + 1 FROM reach r JOIN public.g1_graph_edge e ON e.src_key = r.k WHERE r.depth < 2
        ) SELECT count(*) FROM reach
    """))
    graph_2hop_ms = round((time.perf_counter() - t3) * 1000, 2)
    graph_total_b = int(query("SELECT pg_total_relation_size('public.g1_graph_node') + pg_total_relation_size('public.g1_graph_edge')"))

    # 3. Object raw blob stats from reconciled artifact manifest + source catalog
    art_rows = [json.loads(l) for l in (prev_dir / "reconciled/artifact-manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    blob_sizes = [float(a["size_bytes"]) for a in art_rows]
    occ_bytes = sum(o["size_bytes"] for a in art_rows for o in a["occurrences"])
    dedup_bytes = sum(a["size_bytes"] for a in art_rows)
    by_ext = {}
    for ext in sorted({a["file_type"] for a in art_rows}):
        vals = [float(a["size_bytes"]) for a in art_rows if a["file_type"] == ext]
        by_ext[ext] = {"count": len(vals), "bytes": int(sum(vals)), "mean": round(mean(vals), 1), "p50": percentile(vals, 0.5), "p90": percentile(vals, 0.9)}

    # 4. Vector payload lower bounds (ann overhead explicitly deferred to G2 POC-03)
    vec_lower_bounds = {}
    for dims in (768, 1024, 1536):
        vec_lower_bounds[f"dim_{dims}"] = {
            "fp32_bytes": chunk_count * dims * 4,
            "fp16_bytes": chunk_count * dims * 2,
            "int8_bytes": chunk_count * dims * 1,
        }

    # 5. Projections anchored to SRC-03 observed catalog (48,101 all-time docs) & 45-family empirical bytes/doc
    mean_raw_per_family = dedup_bytes / 45.0
    mean_norm_per_family = content_b / 45.0
    mean_chunks_per_family = chunk_count / 45.0

    src03_total = catalog_counts["src03_vanban_chinhphu"]["all_time_portal_total"]
    scenarios = {}
    for label, docs_n, rev_mult, index_oh, backup_copies, headroom in (
        ("low_core_acts_2020_to_2026_estimate", 4000, 1.15, 1.35, 1, 1.25),
        ("base_src03_recent_plus_multi_agency_estimate", 18000, 1.30, 1.50, 2, 1.35),
        ("high_full_national_48k_plus_multi_source", src03_total, 1.50, 1.65, 2, 1.50),
    ):
        raw_est = int(docs_n * mean_raw_per_family * rev_mult)
        norm_est = int(docs_n * mean_norm_per_family * rev_mult)
        chunks_est = int(docs_n * mean_chunks_per_family * rev_mult)
        vec_1024_fp16 = chunks_est * 1024 * 2
        rel_fts_est = int(norm_est * index_oh)
        graph_est = int((docs_n / 18.0) * max(1, graph_total_b) * 1.2)
        active_total = raw_est + rel_fts_est + int(vec_1024_fp16 * 1.35) + graph_est
        with_backup_and_headroom = int((active_total + backup_copies * (raw_est + int(norm_est * 0.2))) * headroom)
        scenarios[label] = {
            "assumed_unique_families": docs_n,
            "revision_multiplier": rev_mult,
            "estimated_chunks": chunks_est,
            "raw_object_gib": round(raw_est / (1024**3), 2),
            "relational_and_fts_gib": round(rel_fts_est / (1024**3), 2),
            "vector_1024_fp16_with_hnsw_estimate_gib": round((vec_1024_fp16 * 1.35) / (1024**3), 2),
            "graph_tables_gib": round(graph_est / (1024**3), 3),
            "total_with_backup_and_headroom_gib": round(with_backup_and_headroom / (1024**3), 2),
        }

    disk = shutil.disk_usage(ROOT)
    return {
        "server_version": query("SHOW server_version"),
        "hardware_verified": {
            "os": f"{platform.system()} {platform.release()} ({platform.version()})",
            "architecture": platform.machine(),
            "cpu_logical_cores": os.cpu_count(),
            "disk_free_gib": round(disk.free / (1024**3), 2),
        },
        "object_storage_observed": {
            "unique_families": 45,
            "unique_blobs": len(art_rows),
            "total_occurrences_bytes": occ_bytes,
            "dedup_unique_blob_bytes": dedup_bytes,
            "blob_bytes_mean": round(mean(blob_sizes), 1),
            "blob_bytes_p50": percentile(blob_sizes, 0.5),
            "blob_bytes_p90": percentile(blob_sizes, 0.9),
            "by_format": by_ext,
        },
        "relational_and_fts_observed": {
            "chunks": chunk_count,
            "normalized_content_bytes": content_b,
            "table_heap_bytes": rel_table_b,
            "btree_index_bytes": btree_b,
            "fts_gin_index_bytes": fts_b,
            "fts_build_seconds": fts_build_s,
            "fts_sample_query_hits": fts_hits,
            "fts_sample_query_ms": fts_query_ms,
            "load_and_btree_seconds": rel_load_s,
            "backup_dump_bytes": dump_file.stat().st_size,
            "backup_seconds": backup_s,
            "restore_seconds": restore_s,
            "restore_integrity": "PASS",
        },
        "graph_tables_observed": {
            "nodes": n_cnt,
            "edges": e_cnt,
            "total_relation_and_index_bytes": graph_total_b,
            "bounded_2hop_reachable_pairs": hop_cnt,
            "bounded_2hop_cte_ms": graph_2hop_ms,
        },
        "vector_payload_lower_bound": {
            "chunks": chunk_count,
            "ann_overhead_note": "Payload raw math only; HNSW/IVFFlat index overhead & filter RAM deferred to G2 POC-03.",
            "matrix": vec_lower_bounds,
        },
        "corpus_projections_from_observed_baseline": scenarios,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--catalog-counts", type=Path, required=True)
    parser.add_argument("--prev-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    catalog_counts = json.loads(args.catalog_counts.read_text(encoding="utf-8"))
    with TemporaryDirectory(prefix="luatvn-g1-sizing-") as directory:
        work = Path(directory)
        data = work / "pgdata"
        password = secrets.token_urlsafe(32)
        pwfile = work / "pw"
        pwfile.write_text(password + "\n", encoding="utf-8")
        try:
            subprocess.run(["initdb", "-D", str(data), "-U", "fixture_admin", "--encoding=UTF8", "--no-locale", "--auth=scram-sha-256", f"--pwfile={pwfile}"], check=True)
        finally:
            pwfile.unlink()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = str(sock.getsockname()[1])
        control = ["pg_ctl", "-D", str(data)]
        log = work / "pg.log"
        with (data / "postgresql.conf").open("a", encoding="utf-8") as cfg:
            cfg.write(f"\nlisten_addresses = '127.0.0.1'\nport = {port}\nunix_socket_directories = ''\n")
        try:
            subprocess.run([*control, "-l", str(log), "-w", "start"], check=True)
            client = ["psql", "-X", "-w", "-h", "127.0.0.1", "-p", port, "-U", "fixture_admin", "-d", "postgres"]
            env = {**os.environ, "PGPASSWORD": password, "PGCLIENTENCODING": "UTF8"}
            for script in ("docs/g0/examples/temporal-example.test.sql", "experiments/g1/temporal-fixture.sql"):
                subprocess.run([*client, "-v", "ON_ERROR_STOP=1", "-f", script], env=env, cwd=ROOT, check=True)
            report = measure_all(client, env, work, args.chunks, args.graph, catalog_counts, args.prev_dir)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"PASS sizing: chunks={report['relational_and_fts_observed']['chunks']} graph_nodes={report['graph_tables_observed']['nodes']} graph_edges={report['graph_tables_observed']['edges']} projections={list(report['corpus_projections_from_observed_baseline'].keys())}")
        finally:
            if subprocess.run([*control, "status"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                subprocess.run([*control, "-w", "stop", "-m", "fast"], check=True)


if __name__ == "__main__":
    main()
