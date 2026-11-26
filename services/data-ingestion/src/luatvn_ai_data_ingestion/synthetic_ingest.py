"""Local G1 recovery fixture. Accepts only inline, synthetic UTF-8 artifacts."""

import hashlib
import sqlite3
import unicodedata
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from .source_rights import RightsDenied, SourceOperation, SourceRegistry


SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_objects (digest TEXT PRIMARY KEY, body BLOB NOT NULL);
CREATE TRIGGER IF NOT EXISTS keep_raw_object BEFORE UPDATE ON raw_objects
BEGIN SELECT RAISE(ABORT, 'immutable raw object'); END;
CREATE TRIGGER IF NOT EXISTS keep_raw_history BEFORE DELETE ON raw_objects
BEGIN SELECT RAISE(ABORT, 'immutable raw object'); END;
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY, source_id TEXT NOT NULL, source_url TEXT NOT NULL,
    source_revision TEXT NOT NULL, cursor INTEGER NOT NULL, digest TEXT REFERENCES raw_objects,
    document_id TEXT NOT NULL, revision TEXT NOT NULL, recovered_by INTEGER REFERENCES attempts,
    started_at REAL NOT NULL, registry_revision TEXT NOT NULL, rights_ref TEXT,
    state TEXT NOT NULL, reason TEXT
);
CREATE INDEX IF NOT EXISTS attempts_rate ON attempts(source_id, started_at) WHERE rights_ref IS NOT NULL;
CREATE INDEX IF NOT EXISTS attempts_cursor ON attempts(source_id, cursor, state);
CREATE TABLE IF NOT EXISTS revisions (
    document_id TEXT, revision TEXT, digest TEXT NOT NULL REFERENCES raw_objects,
    normalized_text TEXT NOT NULL, PRIMARY KEY(document_id, revision)
);
CREATE TABLE IF NOT EXISTS provenance (
    document_id TEXT, revision TEXT, source_id TEXT, source_url TEXT, source_revision TEXT,
    first_attempt INTEGER NOT NULL REFERENCES attempts,
    PRIMARY KEY(document_id, revision, source_id, source_url, source_revision),
    FOREIGN KEY(document_id, revision) REFERENCES revisions
);
CREATE TABLE IF NOT EXISTS checkpoints (source_id TEXT PRIMARY KEY, cursor INTEGER NOT NULL);
"""


@dataclass(frozen=True)
class Artifact:
    source_id: str
    url: str
    source_revision: str
    cursor: int
    document_id: str
    revision: str
    document_date: date
    media_type: str
    body: bytes


def _inspect(artifact: Artifact) -> tuple[str, str | None]:
    if artifact.media_type != "text/plain" or b"\x00" in artifact.body:
        return "", "UNSUPPORTED_MEDIA"
    try:
        text = artifact.body.decode("utf-8")
    except UnicodeDecodeError:
        return "", "MALFORMED_UTF8"
    normalized = unicodedata.normalize("NFC", text).strip()
    lines = normalized.splitlines()
    if len(lines) < 2 or lines[0] != f"FIXTURE {artifact.document_id} {artifact.revision}":
        return "", "IDENTITY_MISMATCH"
    if any(marker in normalized.casefold() for marker in ("<script", "ignore previous instructions")):
        return "", "UNSAFE_FIXTURE_TEXT"
    return normalized, None


def _connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = ON")
    return db


def ingest_fixture(path: Path, registry: SourceRegistry, artifact: Artifact, *, after_raw=None) -> str:
    if (not isinstance(artifact.body, bytes) or type(artifact.cursor) is not int or not 1 <= artifact.cursor < 2**63
            or any(not isinstance(value, str) or not value.strip() for value in (
                artifact.source_id, artifact.url, artifact.source_revision, artifact.document_id, artifact.revision
            ))):
        raise ValueError("invalid fixture metadata")
    with closing(_connect(path)) as db:
        db.executescript(SCHEMA)
        with db:
            db.execute("BEGIN IMMEDIATE")
            now = datetime.now(UTC)
            operation = SourceOperation(artifact.source_id, "store", "g1-fixture", "synthetic", "fixture",
                                        "text-fixture", artifact.url, artifact.document_date, len(artifact.body))
            authorized = None
            reason = None
            try:
                if len(artifact.body) > 64 * 1024:
                    raise RightsDenied("FIXTURE_SIZE_LIMIT")
                authorization = registry.authorize(operation, at=now)
                if not artifact.source_id.startswith("FIXTURE-"):
                    raise RightsDenied("SYNTHETIC_SOURCE_REQUIRED")
                count = db.execute(
                    "SELECT count(*) FROM attempts WHERE source_id=? AND rights_ref IS NOT NULL AND started_at>?",
                    (artifact.source_id, now.timestamp() - 60),
                ).fetchone()[0]
                if count >= authorization.max_actions_per_minute:
                    raise RightsDenied("RATE_LIMIT")
                authorized = authorization.evidence_ref
            except RightsDenied as error:
                reason = str(error)
            digest = None
            if authorized is not None:
                digest = hashlib.sha256(artifact.body).hexdigest()
                db.execute("INSERT INTO raw_objects VALUES (?, ?) ON CONFLICT DO NOTHING", (digest, artifact.body))
            state = "RAW_STORED" if digest is not None else "DENIED"
            attempt = db.execute(
                """INSERT INTO attempts(source_id, source_url, source_revision, cursor, digest,
                       document_id, revision, started_at, registry_revision, rights_ref, state, reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (artifact.source_id, artifact.url, artifact.source_revision, artifact.cursor, digest,
                 artifact.document_id, artifact.revision, now.timestamp(), registry.revision, authorized, state, reason),
            ).lastrowid
        if digest is None:
            return state
        if after_raw is not None:
            after_raw()

        text, reason = _inspect(artifact)
        key = (artifact.document_id, artifact.revision)
        with db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT digest FROM revisions WHERE document_id=? AND revision=?", key).fetchone()
            if prior is not None and prior[0] != digest:
                reason = reason or "REVISION_CONFLICT"
            state = "QUARANTINED" if reason else "CANDIDATE"
            if reason is None:
                db.execute("INSERT INTO revisions VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING", (*key, digest, text))
                db.execute("INSERT INTO provenance VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                           (*key, artifact.source_id, artifact.url, artifact.source_revision, attempt))
            db.execute("UPDATE attempts SET state=?, reason=? WHERE id=?", (state, reason, attempt))
            db.execute(
                """UPDATE attempts SET recovered_by=? WHERE id<? AND source_id=? AND cursor=?
                   AND source_url=? AND source_revision=? AND digest=? AND document_id=? AND revision=?
                   AND state='RAW_STORED' AND recovered_by IS NULL""",
                (attempt, attempt, artifact.source_id, artifact.cursor, artifact.url, artifact.source_revision,
                 digest, *key),
            )
            db.execute(
                """WITH RECURSIVE completed(cursor) AS (
                       SELECT coalesce((SELECT cursor FROM checkpoints WHERE source_id=:source), 0)
                       UNION ALL
                       SELECT completed.cursor + 1 FROM completed
                       WHERE EXISTS (SELECT 1 FROM attempts AS done WHERE done.source_id=:source
                           AND done.cursor=completed.cursor + 1 AND done.state IN ('CANDIDATE', 'QUARANTINED'))
                       AND NOT EXISTS (SELECT 1 FROM attempts AS inflight WHERE inflight.source_id=:source
                           AND inflight.cursor=completed.cursor + 1 AND inflight.state='RAW_STORED'
                           AND inflight.recovered_by IS NULL)
                   )
                   INSERT INTO checkpoints SELECT :source, max(cursor) FROM completed HAVING max(cursor)>0
                   ON CONFLICT(source_id) DO UPDATE SET cursor=excluded.cursor""",
                {"source": artifact.source_id},
            )
        return state
