"""Explicit market/package entitlements without duplicating data providers."""
from alembic import op
from sqlalchemy import text

revision = '20261008_73'
down_revision = '20261008_72'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE md.data_provider ADD COLUMN owner_tenant_id uuid REFERENCES ten.tenant(tenant_id);
        ALTER TABLE ten.tenant_dataset_entitlement
          ADD COLUMN coverage_mode varchar(20) NOT NULL DEFAULT 'DATASET',
          ADD CONSTRAINT ck_entitlement_coverage_mode CHECK (coverage_mode IN ('DATASET','SCOPED')),
          ADD CONSTRAINT uq_entitlement_dataset_scope UNIQUE(tenant_dataset_entitlement_id,dataset_id);
    """)
    # Freeze revision DDL; future ORM metadata must not change old migrations.
    op.execute("""
        CREATE TABLE md.dataset_coverage_package (
          coverage_package_id uuid PRIMARY KEY DEFAULT uuidv7(),
          dataset_id uuid NOT NULL REFERENCES md.dataset(dataset_id),
          package_code varchar(100) NOT NULL, display_name varchar(250) NOT NULL,
          content_owner_provider_id uuid NOT NULL REFERENCES md.data_provider(data_provider_id),
          licensing_market_venue_id uuid REFERENCES secm.market_venue(market_venue_id),
          information_timing varchar(30) NOT NULL, evidence_reference text NOT NULL,
          status varchar(30) NOT NULL DEFAULT 'ACTIVE', valid_from date NOT NULL, valid_to date,
          CONSTRAINT uq_dataset_coverage_code UNIQUE(dataset_id,package_code),
          CONSTRAINT uq_package_dataset_scope UNIQUE(coverage_package_id,dataset_id),
          CONSTRAINT ck_package_information_timing CHECK (information_timing IN ('REAL_TIME','DELAYED','END_OF_DAY','HISTORICAL')),
          CONSTRAINT ck_package_valid_period CHECK (valid_to IS NULL OR valid_to >= valid_from),
          CONSTRAINT ck_package_scope_evidence CHECK (length(trim(package_code)) > 0 AND length(trim(evidence_reference)) > 0)
        );
        CREATE TABLE md.market_data_series_coverage (
          dataset_id uuid NOT NULL REFERENCES md.dataset(dataset_id),
          market_data_series_id uuid NOT NULL REFERENCES md.market_data_series(market_data_series_id),
          coverage_package_id uuid NOT NULL,
          PRIMARY KEY(dataset_id,market_data_series_id),
          FOREIGN KEY(coverage_package_id,dataset_id) REFERENCES md.dataset_coverage_package(coverage_package_id,dataset_id)
        );
        CREATE TABLE ten.tenant_dataset_coverage (
          tenant_dataset_entitlement_id uuid NOT NULL, dataset_id uuid NOT NULL,
          coverage_package_id uuid NOT NULL,
          PRIMARY KEY(tenant_dataset_entitlement_id,coverage_package_id),
          FOREIGN KEY(tenant_dataset_entitlement_id,dataset_id) REFERENCES ten.tenant_dataset_entitlement(tenant_dataset_entitlement_id,dataset_id),
          FOREIGN KEY(coverage_package_id,dataset_id) REFERENCES md.dataset_coverage_package(coverage_package_id,dataset_id)
        );
    """)
    op.execute("COMMENT ON COLUMN ten.tenant_dataset_entitlement.coverage_mode IS 'DATASET grants full dataset coverage; SCOPED requires explicit package associations and series classification.'")
    op.execute("COMMENT ON COLUMN md.data_provider.owner_tenant_id IS 'Tenant-private source identity; null is shared. Does not erase upstream ownership or licensing.'")


def downgrade():
    # Removing restrictions would broaden remaining grants: never silently do so.
    connection = op.get_bind()
    for query in (
        "SELECT EXISTS(SELECT 1 FROM ten.tenant_dataset_entitlement WHERE coverage_mode='SCOPED')",
        "SELECT EXISTS(SELECT 1 FROM md.dataset_coverage_package)",
        "SELECT EXISTS(SELECT 1 FROM md.data_provider WHERE owner_tenant_id IS NOT NULL)",
    ):
        if connection.scalar(text(query)):
            raise RuntimeError('Coverage evidence exists; do not discard restrictions by downgrading')
    op.execute('DROP TABLE ten.tenant_dataset_coverage; DROP TABLE md.market_data_series_coverage; DROP TABLE md.dataset_coverage_package')
    op.execute("""
        ALTER TABLE ten.tenant_dataset_entitlement DROP CONSTRAINT uq_entitlement_dataset_scope,
          DROP CONSTRAINT ck_entitlement_coverage_mode, DROP COLUMN coverage_mode;
        ALTER TABLE md.data_provider DROP COLUMN owner_tenant_id;
    """)
