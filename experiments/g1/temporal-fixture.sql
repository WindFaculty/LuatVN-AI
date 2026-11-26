\set ON_ERROR_STOP on
\ir ../../services/legal-knowledge/migrations/g1/001_temporal_candidate.sql
SET search_path TO g1_temporal, public;

INSERT INTO provision VALUES ('article', 'family-a', NULL), ('article-5a', 'family-a', NULL);
INSERT INTO provision VALUES ('clause-2', 'family-a', 'article-5a'), ('clause-2a', 'family-a', 'article-5a');
INSERT INTO provision_version VALUES ('v1', 'clause-2a', '2a', 'First version'),
    ('v2', 'clause-2a', '2b', 'Renamed label'), ('missing', 'clause-2', '2', 'Unreviewed');
INSERT INTO anchor VALUES ('a1', 'v1', repeat('a', 64), 'https://fixture.test/a', 'page 1', 'First version'),
    ('a2', 'v2', repeat('b', 64), 'https://fixture.test/b', 'page 2', 'Renamed label');
INSERT INTO assertion VALUES
    ('old', 'clause-2a', 'v1', 'a1', 'fixture', '[2020-01-01,)', '[2020-01-01 00:00Z,2022-01-01 00:00Z)', 'verified', 'fixture', 'r1'),
    ('historical', 'clause-2a', 'v1', 'a1', 'fixture', '[2020-01-01,2021-01-01)', '[2022-01-01 00:00Z,)', 'verified', 'fixture', 'r2'),
    ('new', 'clause-2a', 'v2', 'a2', 'fixture', '[2021-01-01,2023-01-01)', '[2022-01-01 00:00Z,)', 'verified', 'fixture', 'r2'),
    ('unknown', 'clause-2', 'missing', NULL, NULL, NULL, '[2022-01-01 00:00Z,)', 'candidate', NULL, NULL),
    ('ambiguous', 'clause-2a', 'v1', NULL, 'fixture', '[2021-01-01,)', '[2022-01-01 00:00Z,)', 'conflict', NULL, NULL);

DO $$
BEGIN
    BEGIN
        UPDATE assertion SET review_state = 'verified' WHERE assertion_id = 'unknown';
        RAISE EXCEPTION 'missing evidence/time/scope/review accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        UPDATE assertion SET evidence_id = 'a1' WHERE assertion_id = 'new';
        RAISE EXCEPTION 'mismatched anchor version accepted';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;
    BEGIN
        UPDATE assertion SET evidence_id = 'a1', reviewed_by = 'fixture', review_ref = 'r3',
            review_state = 'verified' WHERE assertion_id = 'ambiguous';
        RAISE EXCEPTION 'overlapping verified assertion accepted';
    EXCEPTION WHEN exclusion_violation THEN NULL;
    END;
END;
$$;

SELECT publish_snapshot('previous', repeat('1', 64), '2021-01-01', '2021-12-31 23:59:59Z', 'fixture');
SELECT publish_snapshot('boundary', repeat('2', 64), '2021-01-01', '2022-01-01 00:00Z', 'fixture');
SELECT publish_snapshot('historical', repeat('3', 64), '2020-12-31', '2022-01-01 00:00Z', 'fixture');
SELECT publish_snapshot('partial-repeal', repeat('4', 64), '2023-01-01', '2023-01-01 00:00Z', 'fixture');
BEGIN;
SELECT publish_snapshot('aborted', repeat('5', 64), '2021-01-01', '2022-01-01 00:00Z', 'fixture');
ROLLBACK;

-- Stand-in for a consumer-owned, idempotent projection in this fixture only.
CREATE TEMP TABLE projection (LIKE snapshot_entry INCLUDING ALL);
INSERT INTO projection SELECT e.* FROM snapshot_entry e JOIN snapshot_outbox o USING (snapshot_id) ON CONFLICT DO NOTHING;
INSERT INTO projection SELECT e.* FROM snapshot_entry e JOIN snapshot_outbox o USING (snapshot_id) ON CONFLICT DO NOTHING;
DO $$
BEGIN
    IF (SELECT array_agg(version_id ORDER BY snapshot_id) FROM projection) IS DISTINCT FROM ARRAY['v2','v1','v1']
       OR (SELECT count(*) FROM snapshot_outbox) <> 4
       OR (SELECT count(*) FROM snapshot) <> 4
       OR EXISTS (SELECT FROM projection WHERE provision_id <> 'clause-2a') THEN
        RAISE EXCEPTION 'unexpected cutoff/snapshot/rollback/replay result';
    END IF;
    BEGIN
        UPDATE anchor SET exact_quote = 'Changed' WHERE anchor_id = 'a2';
        RAISE EXCEPTION 'published provenance rewritten';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        INSERT INTO snapshot_entry VALUES ('partial-repeal', 'clause-2a', 'v2', 'a2');
        RAISE EXCEPTION 'entry added after snapshot was sealed';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
END;
$$;
\echo PASS: bitemporal boundaries, provenance, verified overlap, rollback and projection replay
