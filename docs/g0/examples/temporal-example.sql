-- G0 v0.2 example. Run in a disposable PostgreSQL database.
BEGIN;
CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;
CREATE SCHEMA g0_example;
SET LOCAL search_path TO g0_example, public;

CREATE TABLE document (
    document_id uuid PRIMARY KEY,
    canonical_key text NOT NULL UNIQUE,
    document_type text NOT NULL
);

CREATE TABLE provision (
    provision_id uuid PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES document,
    parent_provision_id uuid,
    canonical_key text NOT NULL UNIQUE,
    UNIQUE (canonical_key, provision_id),
    UNIQUE (provision_id, document_id),
    FOREIGN KEY (parent_provision_id, document_id) REFERENCES provision (provision_id, document_id),
    CHECK (parent_provision_id IS DISTINCT FROM provision_id)
);

CREATE TABLE provision_version (
    version_id uuid PRIMARY KEY,
    provision_id uuid NOT NULL REFERENCES provision,
    display_label text NOT NULL,
    sort_path integer[] NOT NULL,
    content_text text NOT NULL,
    UNIQUE (version_id, provision_id)
);

CREATE TABLE evidence_anchor (
    evidence_id uuid PRIMARY KEY,
    version_id uuid NOT NULL REFERENCES provision_version,
    artifact_sha256 text NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    source_url text NOT NULL,
    locator text NOT NULL,
    UNIQUE (evidence_id, version_id)
);

CREATE TABLE provision_assertion (
    assertion_id uuid PRIMARY KEY,
    canonical_key text NOT NULL,
    scope_key text NOT NULL CHECK (scope_key <> ''),
    provision_id uuid NOT NULL,
    version_id uuid NOT NULL,
    evidence_id uuid NOT NULL,
    valid_range daterange NOT NULL,
    recorded_range tstzrange NOT NULL,
    review_state text NOT NULL CHECK (review_state IN ('candidate', 'conflict', 'verified', 'revoked')),
    FOREIGN KEY (canonical_key, provision_id) REFERENCES provision (canonical_key, provision_id),
    FOREIGN KEY (version_id, provision_id) REFERENCES provision_version (version_id, provision_id),
    FOREIGN KEY (evidence_id, version_id) REFERENCES evidence_anchor (evidence_id, version_id),
    CHECK (
        NOT isempty(valid_range) AND NOT lower_inf(valid_range)
        AND isfinite(lower(valid_range)) AND lower_inc(valid_range) AND NOT upper_inc(valid_range)
    ),
    CHECK (
        NOT isempty(recorded_range) AND NOT lower_inf(recorded_range)
        AND isfinite(lower(recorded_range)) AND lower_inc(recorded_range) AND NOT upper_inc(recorded_range)
    ),
    EXCLUDE USING gist (
        canonical_key WITH =,
        scope_key WITH =,
        valid_range WITH &&,
        recorded_range WITH &&
    ) WHERE (review_state = 'verified')
);

CREATE TABLE amendment_operation (
    operation_id uuid PRIMARY KEY,
    amending_version_id uuid NOT NULL REFERENCES provision_version,
    operation_order integer NOT NULL CHECK (operation_order > 0),
    target_provision_id uuid NOT NULL REFERENCES provision,
    before_version_id uuid,
    after_version_id uuid,
    operation_kind text NOT NULL CHECK (
        operation_kind IN ('insert', 'replace', 'repeal', 'correct', 'delete_phrase')
    ),
    effective_on date NOT NULL,
    target_locator text NOT NULL,
    evidence_id uuid NOT NULL REFERENCES evidence_anchor,
    FOREIGN KEY (before_version_id, target_provision_id) REFERENCES provision_version (version_id, provision_id),
    FOREIGN KEY (after_version_id, target_provision_id) REFERENCES provision_version (version_id, provision_id),
    UNIQUE (amending_version_id, operation_order),
    CHECK (
        (operation_kind = 'insert' AND before_version_id IS NULL AND after_version_id IS NOT NULL)
        OR (operation_kind = 'repeal' AND before_version_id IS NOT NULL AND after_version_id IS NULL)
        OR (operation_kind IN ('replace', 'correct', 'delete_phrase')
            AND before_version_id IS NOT NULL AND after_version_id IS NOT NULL
            AND before_version_id <> after_version_id)
    )
);

CREATE TABLE consolidation_lineage (
    lineage_id uuid PRIMARY KEY,
    consolidated_version_id uuid NOT NULL REFERENCES provision_version,
    contributor_version_id uuid NOT NULL REFERENCES provision_version,
    operation_id uuid REFERENCES amendment_operation,
    evidence_id uuid NOT NULL REFERENCES evidence_anchor,
    UNIQUE NULLS NOT DISTINCT (consolidated_version_id, contributor_version_id, operation_id),
    CHECK (consolidated_version_id <> contributor_version_id)
);

CREATE TABLE jurisdiction (
    jurisdiction_id uuid PRIMARY KEY,
    level_code text NOT NULL
);

CREATE TABLE jurisdiction_label_revision (
    label_revision_id uuid PRIMARY KEY,
    jurisdiction_id uuid NOT NULL REFERENCES jurisdiction,
    official_name text NOT NULL,
    official_code text,
    legal_range daterange NOT NULL CHECK (
        NOT isempty(legal_range) AND NOT lower_inf(legal_range)
        AND isfinite(lower(legal_range)) AND lower_inc(legal_range) AND NOT upper_inc(legal_range)
    ),
    recorded_range tstzrange NOT NULL CHECK (
        NOT isempty(recorded_range) AND NOT lower_inf(recorded_range)
        AND isfinite(lower(recorded_range)) AND lower_inc(recorded_range) AND NOT upper_inc(recorded_range)
    ),
    evidence_id uuid NOT NULL REFERENCES evidence_anchor,
    review_state text NOT NULL CHECK (review_state IN ('candidate', 'conflict', 'verified', 'revoked')),
    EXCLUDE USING gist (
        jurisdiction_id WITH =,
        legal_range WITH &&,
        recorded_range WITH &&
    ) WHERE (review_state = 'verified')
);

CREATE TABLE jurisdiction_lineage (
    relation_id uuid PRIMARY KEY,
    from_jurisdiction_id uuid NOT NULL REFERENCES jurisdiction,
    to_jurisdiction_id uuid NOT NULL REFERENCES jurisdiction,
    relation_kind text NOT NULL CHECK (relation_kind IN ('merge', 'split', 'rename', 'boundary_adjustment')),
    valid_range daterange NOT NULL CHECK (
        NOT isempty(valid_range) AND NOT lower_inf(valid_range)
        AND isfinite(lower(valid_range)) AND lower_inc(valid_range) AND NOT upper_inc(valid_range)
    ),
    recorded_range tstzrange NOT NULL CHECK (
        NOT isempty(recorded_range) AND NOT lower_inf(recorded_range)
        AND isfinite(lower(recorded_range)) AND lower_inc(recorded_range) AND NOT upper_inc(recorded_range)
    ),
    evidence_id uuid NOT NULL REFERENCES evidence_anchor,
    review_state text NOT NULL CHECK (review_state IN ('candidate', 'conflict', 'verified', 'revoked')),
    CHECK (relation_kind = 'rename' OR from_jurisdiction_id <> to_jurisdiction_id),
    EXCLUDE USING gist (
        from_jurisdiction_id WITH =,
        to_jurisdiction_id WITH =,
        relation_kind WITH =,
        valid_range WITH &&,
        recorded_range WITH &&
    ) WHERE (review_state = 'verified')
);

COMMIT;
