-- Run with psql -X -d <disposable-db> -f temporal-example.test.sql against a fresh database.
\set ON_ERROR_STOP on
\ir temporal-example.sql

BEGIN;
SET LOCAL search_path TO g0_example, public;

CREATE FUNCTION pg_temp.expect_sqlstate(statement text, expected text)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE statement;
    RAISE EXCEPTION 'Expected SQLSTATE % for %', expected, statement;
EXCEPTION WHEN OTHERS THEN
    IF SQLSTATE <> expected THEN
        RAISE;
    END IF;
END;
$$;

DO $$
DECLARE
    document_a uuid := gen_random_uuid();
    document_b uuid := gen_random_uuid();
    parent_id uuid := gen_random_uuid();
    child_id uuid := gen_random_uuid();
    version_a uuid := gen_random_uuid();
    version_b uuid := gen_random_uuid();
    anchor_id uuid := gen_random_uuid();
    assertion uuid := gen_random_uuid();
    origin_id uuid := gen_random_uuid();
    destination_a uuid := gen_random_uuid();
    destination_b uuid := gen_random_uuid();
    label_candidate uuid := gen_random_uuid();
    edge_conflict uuid := gen_random_uuid();
    effective daterange := '[2020-01-01,)';
    known tstzrange := '[2020-01-01 00:00:00+00,)';
BEGIN
    INSERT INTO document VALUES (document_a, 'a', 'sample'), (document_b, 'b', 'sample');
    INSERT INTO provision VALUES
        (parent_id, document_a, NULL, 'a-parent'),
        (child_id, document_a, parent_id, 'a-child');
    PERFORM pg_temp.expect_sqlstate(
        format('UPDATE provision SET document_id = %L WHERE provision_id = %L', document_b, child_id),
        '23503'
    );

    INSERT INTO provision_version VALUES
        (version_a, child_id, '1', ARRAY[1], 'Version A'),
        (version_b, child_id, '1', ARRAY[1], 'Version B');
    INSERT INTO evidence_anchor VALUES (anchor_id, version_a, repeat('a', 64), 'https://example.test/a', '1');
    INSERT INTO provision_assertion VALUES
        (assertion, 'a-child', 'fixture', child_id, version_a, anchor_id, effective, known, 'verified');
    PERFORM pg_temp.expect_sqlstate(
        format('UPDATE provision_assertion SET version_id = %L WHERE assertion_id = %L', version_b, assertion),
        '23503'
    );

    INSERT INTO jurisdiction VALUES
        (origin_id, 'province'), (destination_a, 'province'), (destination_b, 'province');
    INSERT INTO jurisdiction_label_revision VALUES
        (gen_random_uuid(), origin_id, 'Official', NULL, effective, known, anchor_id, 'verified'),
        (label_candidate, origin_id, 'Candidate', NULL, effective, known, anchor_id, 'candidate'),
        (gen_random_uuid(), origin_id, 'Conflict', NULL, effective, known, anchor_id, 'conflict'),
        (gen_random_uuid(), origin_id, 'Prior', NULL, effective,
         '[2019-01-01 00:00:00+00,2020-01-01 00:00:00+00)', anchor_id, 'verified');
    PERFORM pg_temp.expect_sqlstate(
        format('UPDATE jurisdiction_label_revision SET review_state = %L WHERE label_revision_id = %L',
               'verified', label_candidate),
        '23P01'
    );
    PERFORM pg_temp.expect_sqlstate(
        format('UPDATE jurisdiction_label_revision SET legal_range = %L WHERE label_revision_id = %L',
               '[-infinity,2020-01-01)', label_candidate),
        '23514'
    );
    PERFORM pg_temp.expect_sqlstate(
        format('UPDATE jurisdiction_label_revision SET recorded_range = %L WHERE label_revision_id = %L',
               '[-infinity,2020-01-01 00:00:00+00)', label_candidate),
        '23514'
    );

    INSERT INTO jurisdiction_lineage VALUES
        (gen_random_uuid(), origin_id, destination_a, 'split', effective, known, anchor_id, 'verified'),
        (gen_random_uuid(), origin_id, destination_b, 'split', effective, known, anchor_id, 'verified'),
        (gen_random_uuid(), origin_id, destination_a, 'split', effective, known, anchor_id, 'candidate'),
        (edge_conflict, origin_id, destination_a, 'split', effective, known, anchor_id, 'conflict');
    PERFORM pg_temp.expect_sqlstate(
        format('UPDATE jurisdiction_lineage SET review_state = %L WHERE relation_id = %L',
               'verified', edge_conflict),
        '23P01'
    );
    PERFORM pg_temp.expect_sqlstate(
        format('UPDATE jurisdiction_lineage SET valid_range = %L WHERE relation_id = %L',
               '[-infinity,2020-01-01)', edge_conflict),
        '23514'
    );
    PERFORM pg_temp.expect_sqlstate(
        format('UPDATE jurisdiction_lineage SET recorded_range = %L WHERE relation_id = %L',
               '[-infinity,2020-01-01 00:00:00+00)', edge_conflict),
        '23514'
    );
END;
$$;

ROLLBACK;
\echo PASS: temporal foreign keys, finite lower bounds, review states and lineage splits
