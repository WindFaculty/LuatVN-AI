"""Replay G0 and G1 SQL and optionally measure a local chunk snapshot."""

import argparse
import csv
import json
import os
import secrets
import socket
import subprocess
import time
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[2]


def measure_chunks(client: list[str], env: dict[str, str], work: Path, chunks: Path) -> dict:
    rows_file = work / "chunks.csv"
    count = 0
    with chunks.open(encoding="utf-8") as source, rows_file.open("w", newline="", encoding="utf-8") as target:
        writer = csv.writer(target)
        for line in source:
            row = json.loads(line)
            if row["review_state"] != "PENDING_REVIEW":
                raise ValueError("sizing expects the G1 candidate snapshot")
            writer.writerow((row["artifact_sha256"], row["unit_kind"], row["unit"], row["offset"], row["text"]))
            count += 1
    if not count:
        raise ValueError("sizing requires at least one observed chunk")

    def query(sql: str, *, database: str = "postgres") -> str:
        result = subprocess.run(
            [*client[:-1], database, "-v", "ON_ERROR_STOP=1", "-Atc", sql],
            env=env, check=True, capture_output=True, encoding="utf-8",
        )
        return result.stdout.strip()

    query("""CREATE TABLE public.g1_chunk (
        artifact_sha256 text NOT NULL, unit_kind text NOT NULL, unit integer NOT NULL,
        start_offset integer NOT NULL, content text NOT NULL
    )""")
    started = time.perf_counter()
    with rows_file.open("rb") as data:
        proc = subprocess.run(
            [*client, "-v", "ON_ERROR_STOP=1", "-c", "\\copy public.g1_chunk FROM STDIN WITH (FORMAT csv)"],
            stdin=data, env=env, check=True, capture_output=True,
        )
    if proc.stdout.strip() != f"COPY {count}".encode():
        raise ValueError("PostgreSQL loaded an unexpected number of chunks")
    query("CREATE INDEX ON public.g1_chunk (artifact_sha256, unit_kind, unit, start_offset)")
    load_seconds = time.perf_counter() - started
    table_bytes, indexes_bytes, total_bytes, content_bytes = map(int, query("""
        SELECT pg_table_size('public.g1_chunk'), pg_indexes_size('public.g1_chunk'),
               pg_total_relation_size('public.g1_chunk'), sum(octet_length(content))
        FROM public.g1_chunk
    """).split("|"))

    # Include the row fields in the checksum, not only the total size.
    fingerprint_sql = """
        SELECT count(*) || '|' || md5(string_agg(md5(g1_chunk::text), '' ORDER BY
            artifact_sha256, unit_kind, unit, start_offset))
        FROM public.g1_chunk
    """
    expected = query(fingerprint_sql)
    backup = work / "chunks.dump"
    connection = client[3:-2]
    started = time.perf_counter()
    subprocess.run(
        ["pg_dump", *connection, "-w", "-Fc", "--table=public.g1_chunk", "-f", str(backup), "postgres"],
        env=env, check=True,
    )
    backup_seconds = time.perf_counter() - started
    query("CREATE DATABASE g1_restore")
    started = time.perf_counter()
    subprocess.run(
        ["pg_restore", *connection, "-w", "--exit-on-error", "-d", "g1_restore", str(backup)],
        env=env, check=True,
    )
    restore_seconds = time.perf_counter() - started
    if query(fingerprint_sql, database="g1_restore") != expected:
        raise ValueError("restored chunk count or content differs")
    return {
        "server_version": query("SHOW server_version"), "chunks": count, "chunk_content_bytes": content_bytes,
        "chunk_table_bytes": table_bytes, "chunk_indexes_bytes": indexes_bytes,
        "total_relation_bytes": total_bytes, "backup_bytes": backup.stat().st_size,
        "load_and_index_seconds": round(load_seconds, 3), "backup_seconds": round(backup_seconds, 3),
        "restore_seconds": round(restore_seconds, 3), "restore": "PASS",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", type=Path)
    parser.add_argument("--sizing-output", type=Path)
    args = parser.parse_args()
    if (args.chunks is None) != (args.sizing_output is None):
        parser.error("--chunks and --sizing-output are required together")

    with TemporaryDirectory(prefix="luatvn-g1-postgres-") as directory:
        work = Path(directory)
        data = work / "pgdata"
        password = secrets.token_urlsafe(32)
        bootstrap = work / "bootstrap"
        bootstrap.write_text(password + "\n", encoding="utf-8")
        try:
            subprocess.run(["initdb", "-D", str(data), "-U", "fixture_admin", "--encoding=UTF8",
                            "--no-locale", "--auth=scram-sha-256", f"--pwfile={bootstrap}"], check=True)
        finally:
            bootstrap.unlink()

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = str(listener.getsockname()[1])

        control = ["pg_ctl", "-D", str(data)]
        log = work / "postgres.log"
        with (data / "postgresql.conf").open("a", encoding="utf-8") as config:
            config.write(f"\nlisten_addresses = '127.0.0.1'\nport = {port}\nunix_socket_directories = ''\n")
        try:
            result = subprocess.run([*control, "-l", str(log), "-w", "start"])
            if result.returncode and log.exists():
                print(log.read_text(encoding="utf-8", errors="replace"), flush=True)
            result.check_returncode()
            client = ["psql", "-X", "-w", "-h", "127.0.0.1", "-p", port, "-U", "fixture_admin", "-d", "postgres"]
            env = {**os.environ, "PGPASSWORD": password, "PGCLIENTENCODING": "UTF8"}
            subprocess.run([*client, "-Atc", "SHOW server_version"], env=env, check=True)
            for script in ("docs/g0/examples/temporal-example.test.sql", "experiments/g1/temporal-fixture.sql"):
                subprocess.run([*client, "-v", "ON_ERROR_STOP=1", "-f", script], env=env, cwd=ROOT, check=True)
            if args.chunks:
                report = measure_chunks(client, env, work, args.chunks)
                args.sizing_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                print(f"PASS: restored {report['chunks']} chunk rows")
        finally:
            status = subprocess.run([*control, "status"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if status.returncode == 0:
                subprocess.run([*control, "-w", "stop", "-m", "fast"], check=True)


if __name__ == "__main__":
    main()
