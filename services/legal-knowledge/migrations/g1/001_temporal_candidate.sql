BEGIN;
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE SCHEMA g1_temporal;
SET LOCAL search_path TO g1_temporal, public;

CREATE TABLE provision (
    provision_id text PRIMARY KEY,
    family_id text NOT NULL,
    parent_id text,
    UNIQUE (provision_id, family_id),
    FOREIGN KEY (parent_id, family_id) REFERENCES provision (provision_id, family_id),
    CHECK (parent_id <> provision_id)
);
CREATE TABLE provision_version (
    version_id text PRIMARY KEY,
    provision_id text NOT NULL REFERENCES provision,
    label text NOT NULL CHECK (btrim(label) <> ''),
    body text NOT NULL,
    UNIQUE (version_id, provision_id)
);
CREATE TABLE anchor (
    anchor_id text PRIMARY KEY,
    version_id text NOT NULL REFERENCES provision_version,
    artifact_sha256 text NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    source_url text NOT NULL CHECK (source_url LIKE 'https://%'),
    locator text NOT NULL CHECK (btrim(locator) <> ''),
    exact_quote text NOT NULL CHECK (btrim(exact_quote) <> ''),
    UNIQUE (anchor_id, version_id)
);
CREATE TABLE assertion (
    assertion_id text PRIMARY KEY,
    provision_id text NOT NULL REFERENCES provision,
    version_id text NOT NULL,
    evidence_id text,
    scope_key text CHECK (btrim(scope_key) <> ''),
    valid_range daterange,
    recorded_range tstzrange NOT NULL,
    review_state text NOT NULL CHECK (review_state IN ('candidate', 'conflict', 'verified', 'revoked')),
    reviewed_by text,
    review_ref text,
    FOREIGN KEY (version_id, provision_id) REFERENCES provision_version (version_id, provision_id),
    FOREIGN KEY (evidence_id, version_id) REFERENCES anchor (anchor_id, version_id),
    CHECK (valid_range IS NULL OR (
        NOT isempty(valid_range) AND NOT lower_inf(valid_range) AND isfinite(lower(valid_range))
        AND (upper_inf(valid_range) OR isfinite(upper(valid_range)))
    )),
    CHECK (NOT isempty(recorded_range) AND NOT lower_inf(recorded_range) AND isfinite(lower(recorded_range))
        AND lower_inc(recorded_range) AND NOT upper_inc(recorded_range)
        AND (upper_inf(recorded_range) OR isfinite(upper(recorded_range)))),
    CHECK (review_state <> 'verified' OR (evidence_id IS NOT NULL AND scope_key IS NOT NULL AND valid_range IS NOT NULL
        AND coalesce(btrim(reviewed_by), '') <> '' AND coalesce(btrim(review_ref), '') <> '')),
    EXCLUDE USING gist (provision_id WITH =, scope_key WITH =, valid_range WITH &&, recorded_range WITH &&)
        WHERE (review_state = 'verified')
);
CREATE TABLE snapshot (
    snapshot_id text PRIMARY KEY,
    manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
    legal_on date NOT NULL CHECK (isfinite(legal_on)),
    recorded_at timestamptz NOT NULL CHECK (isfinite(recorded_at)),
    scope_key text NOT NULL CHECK (btrim(scope_key) <> '')
);
CREATE TABLE snapshot_entry (
    snapshot_id text REFERENCES snapshot,
    provision_id text REFERENCES provision,
    version_id text NOT NULL,
    anchor_id text NOT NULL,
    PRIMARY KEY (snapshot_id, provision_id),
    FOREIGN KEY (version_id, provision_id) REFERENCES provision_version (version_id, provision_id),
    FOREIGN KEY (anchor_id, version_id) REFERENCES anchor (anchor_id, version_id)
);
CREATE TABLE snapshot_outbox (snapshot_id text PRIMARY KEY REFERENCES snapshot);

CREATE FUNCTION reject_rewrite() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'immutable G1 record in %', TG_TABLE_NAME USING ERRCODE = '23514';
END;
$$;

CREATE TRIGGER immutable_version BEFORE UPDATE OR DELETE ON provision_version
    FOR EACH ROW EXECUTE FUNCTION reject_rewrite();
CREATE TRIGGER immutable_anchor BEFORE UPDATE OR DELETE ON anchor
    FOR EACH ROW EXECUTE FUNCTION reject_rewrite();
CREATE TRIGGER immutable_snapshot BEFORE UPDATE OR DELETE ON snapshot
    FOR EACH ROW EXECUTE FUNCTION reject_rewrite();
CREATE TRIGGER immutable_snapshot_entry BEFORE UPDATE OR DELETE ON snapshot_entry
    FOR EACH ROW EXECUTE FUNCTION reject_rewrite();
CREATE TRIGGER immutable_outbox_event BEFORE UPDATE OR DELETE ON snapshot_outbox
    FOR EACH ROW EXECUTE FUNCTION reject_rewrite();

CREATE FUNCTION check_unsealed_snapshot() RETURNS trigger LANGUAGE plpgsql
SET search_path TO g1_temporal, pg_catalog AS $$
BEGIN
    PERFORM 1 FROM snapshot WHERE snapshot_id = NEW.snapshot_id FOR UPDATE;
    IF EXISTS (SELECT 1 FROM snapshot_outbox WHERE snapshot_id = NEW.snapshot_id) THEN
        RAISE EXCEPTION 'sealed snapshot' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER unsealed_snapshot_entry BEFORE INSERT ON snapshot_entry
    FOR EACH ROW EXECUTE FUNCTION check_unsealed_snapshot();

CREATE FUNCTION publish_snapshot(id text, digest text, legal_date date, cutoff timestamptz, scope text)
RETURNS void LANGUAGE plpgsql SET search_path TO g1_temporal, pg_catalog AS $$
BEGIN
    INSERT INTO snapshot VALUES (id, digest, legal_date, cutoff, scope);
    INSERT INTO snapshot_entry
        SELECT id, provision_id, version_id, evidence_id FROM assertion
        WHERE review_state = 'verified' AND scope_key = scope
          AND valid_range @> legal_date AND recorded_range @> cutoff;
    INSERT INTO snapshot_outbox VALUES (id);
END;
$$;
COMMIT;
