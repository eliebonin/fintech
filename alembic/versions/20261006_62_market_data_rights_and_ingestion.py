"""Layered activity rights and retained atomic market-data deliveries."""
from alembic import op

revision = '20261006_62'
down_revision = '20261005_61'
branch_labels = depends_on = None


def upgrade():
    # Freeze DDL in the revision: later application metadata must not alter history.
    op.execute("""
        CREATE TABLE md.dataset_access_profile (
            dataset_id UUID PRIMARY KEY REFERENCES md.dataset(dataset_id),
            licensee_organisation_id UUID NOT NULL REFERENCES secm.organisation(organisation_id),
            external_id_namespace_id UUID REFERENCES ing.external_id_namespace(external_id_namespace_id),
            permitted_tenant_id UUID REFERENCES ten.tenant(tenant_id),
            usage_scope VARCHAR(20) NOT NULL,
            provider_enabled BOOLEAN NOT NULL DEFAULT false,
            activation_reference TEXT NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
            CONSTRAINT ck_dataset_access_scope CHECK (usage_scope IN ('PERSONAL', 'COMMERCIAL')),
            CONSTRAINT ck_dataset_personal_tenant CHECK (usage_scope <> 'PERSONAL' OR permitted_tenant_id IS NOT NULL),
            CONSTRAINT ck_dataset_activation_evidence CHECK (length(trim(activation_reference)) > 0)
        );
        CREATE TABLE md.licence_activity_grant (
            grant_id UUID PRIMARY KEY DEFAULT uuidv7(),
            dataset_licence_assignment_id UUID NOT NULL REFERENCES md.dataset_licence_assignment(dataset_licence_assignment_id),
            activity VARCHAR(30) NOT NULL,
            usage_scope VARCHAR(20) NOT NULL,
            evidence_basis VARCHAR(30) NOT NULL,
            evidence_reference TEXT NOT NULL,
            valid_from DATE NOT NULL,
            valid_to DATE,
            status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
            CONSTRAINT uq_licence_activity_grant UNIQUE(dataset_licence_assignment_id, activity, usage_scope, valid_from),
            CONSTRAINT ck_licence_grant_activity CHECK (activity IN ('ACQUIRE', 'STORE', 'DISPLAY', 'NON_DISPLAY', 'CLIENT_REPORTING', 'REDISTRIBUTE', 'DERIVED_DATA')),
            CONSTRAINT ck_licence_grant_basis CHECK (usage_scope IN ('PERSONAL', 'COMMERCIAL') AND evidence_basis IN ('CONTRACT', 'PERSONAL_DECLARATION')),
            CONSTRAINT ck_licence_commercial_contract CHECK (usage_scope <> 'COMMERCIAL' OR evidence_basis = 'CONTRACT'),
            CONSTRAINT ck_licence_grant_period CHECK (valid_to IS NULL OR valid_to >= valid_from),
            CONSTRAINT ck_licence_grant_evidence CHECK (length(trim(evidence_reference)) > 0)
        );
        CREATE TABLE md.dataset_right_requirement (
            requirement_id UUID PRIMARY KEY DEFAULT uuidv7(),
            dataset_id UUID NOT NULL REFERENCES md.dataset(dataset_id),
            activity VARCHAR(30) NOT NULL,
            requirement_code VARCHAR(100) NOT NULL,
            dataset_licence_assignment_id UUID REFERENCES md.dataset_licence_assignment(dataset_licence_assignment_id),
            CONSTRAINT uq_dataset_right_requirement UNIQUE(dataset_id, activity, requirement_code),
            CONSTRAINT ck_dataset_requirement_activity CHECK (activity IN ('ACQUIRE', 'STORE', 'DISPLAY', 'NON_DISPLAY', 'CLIENT_REPORTING', 'REDISTRIBUTE', 'DERIVED_DATA'))
        );
        CREATE TABLE md.market_data_ingestion_run (
            run_id UUID PRIMARY KEY DEFAULT uuidv7(),
            dataset_id UUID NOT NULL REFERENCES md.dataset(dataset_id),
            source_payload_id UUID NOT NULL UNIQUE REFERENCES ing.source_payload(source_payload_id),
            delivery_key VARCHAR(250) NOT NULL,
            content_sha256 VARCHAR(64) NOT NULL,
            raw_payload TEXT NOT NULL,
            received_at_utc TIMESTAMPTZ NOT NULL,
            rights_evidence JSONB NOT NULL,
            report JSONB NOT NULL,
            CONSTRAINT uq_market_data_ingestion_delivery UNIQUE(dataset_id, delivery_key),
            CONSTRAINT ck_market_data_ingestion_json CHECK (jsonb_typeof(rights_evidence) = 'array' AND jsonb_typeof(report) = 'object')
        );
        CREATE FUNCTION md.prevent_ingestion_run_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'market-data ingestion runs are immutable; retain a new delivery instead';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_ingestion_run_immutable BEFORE UPDATE OR DELETE ON md.market_data_ingestion_run
            FOR EACH ROW EXECUTE FUNCTION md.prevent_ingestion_run_mutation();
    """)
    comments = {
        'dataset_access_profile': {'dataset_id': 'Dataset governed by strict rights.', 'licensee_organisation_id': 'Actual licensee or identified personal operator.', 'external_id_namespace_id': 'Exact permitted ingestion namespace.', 'permitted_tenant_id': 'Single personal workspace or reviewed commercial scope.', 'usage_scope': 'PERSONAL or COMMERCIAL; not a licence grant.', 'provider_enabled': 'Technical activation separate from rights.', 'activation_reference': 'Evidence for operational activation.', 'status': 'Only ACTIVE profiles permit access.'},
        'licence_activity_grant': {'grant_id': 'Immutable activity grant identity.', 'dataset_licence_assignment_id': 'Dataset-specific licence assignment.', 'activity': 'Controlled permitted activity.', 'usage_scope': 'PERSONAL or COMMERCIAL use.', 'evidence_basis': 'CONTRACT or PERSONAL_DECLARATION; declarations are not commercial clearance.', 'evidence_reference': 'Attributable contract or personal declaration.', 'valid_from': 'Inclusive first use date.', 'valid_to': 'Inclusive last use date or open ended.', 'status': 'Only ACTIVE grants satisfy requirements.'},
        'dataset_right_requirement': {'requirement_id': 'Immutable prerequisite identity.', 'dataset_id': 'Dataset requiring this agreement.', 'activity': 'Activity whose prerequisites are conjunctive.', 'requirement_code': 'Stable layer identifier.', 'dataset_licence_assignment_id': 'Required agreement assignment; null denies use.'},
        'market_data_ingestion_run': {'run_id': 'Immutable retained delivery UUIDv7.', 'dataset_id': 'Actual delivered dataset.', 'source_payload_id': 'Lineage payload linked to retained raw text.', 'delivery_key': 'Stable delivery identity; changed content conflicts.', 'content_sha256': 'SHA-256 of inbound UTF-8 bytes.', 'raw_payload': 'Exact retained inbound JSON text.', 'received_at_utc': 'Real receipt time, never backdated.', 'rights_evidence': 'Frozen acquisition and storage rights evidence.', 'report': 'Counts, rejections and request parameters.'},
    }
    for table, columns in comments.items():
        for column, comment in columns.items():
            op.execute(f"COMMENT ON COLUMN md.{table}.{column} IS '{comment}'")


def downgrade():
    raise RuntimeError('Forward-only: retained source deliveries and rights evidence must not be discarded.')
