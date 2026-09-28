"""Add cryptoasset identity, network, and chain-deployment terms."""

from alembic import op
import sqlalchemy as sa


revision = "20260907_26"
down_revision = "20260907_25"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crypto_network",
        sa.Column("crypto_network_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for a governed blockchain or distributed-ledger network."),
        sa.Column("network_code", sa.String(length=80), nullable=False, comment="Stable network code such as BITCOIN_MAINNET, ETHEREUM_MAINNET, SOLANA_MAINNET, or BASE_MAINNET."),
        sa.Column("display_name", sa.String(length=200), nullable=False, comment="Human-readable blockchain or distributed-ledger network name."),
        sa.Column("network_family", sa.String(length=40), nullable=False, comment="Network family such as BITCOIN, EVM, SOLANA, STELLAR, or OTHER."),
        sa.Column("chain_identifier", sa.String(length=150), nullable=True, comment="Network-specific chain identifier, retained as text because different ecosystems use different identifier formats."),
        sa.Column("native_currency_code", sa.String(length=40), nullable=True, comment="Native asset code when the network has one, such as BTC or ETH; this is descriptive and does not replace the currency foreign key."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status such as ACTIVE, INACTIVE, DEPRECATED, or TESTNET."),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False, comment="Display ordering value for network selection lists."),
        sa.PrimaryKeyConstraint("crypto_network_id"),
        sa.UniqueConstraint("network_code", name="uq_crypto_network_code"),
        schema="secm",
    )
    op.create_table(
        "crypto_asset_terms",
        sa.Column("crypto_asset_terms_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one effective-dated version of cryptoasset terms."),
        sa.Column("instrument_node_id", sa.UUID(), nullable=False, comment="Economic DIGITAL_ASSET instrument governed by these cryptoasset terms."),
        sa.Column("asset_subtype", sa.String(length=40), nullable=False, comment="Cryptoasset subtype such as NATIVE, TOKEN, STABLECOIN, WRAPPED, BRIDGED, or OTHER."),
        sa.Column("native_symbol", sa.String(length=50), nullable=False, comment="Canonical or native symbol of the cryptoasset, distinct from venue-specific trading symbols."),
        sa.Column("protocol_name", sa.String(length=150), nullable=True, comment="Protocol, issuer programme, or token system name when applicable."),
        sa.Column("issuer_organisation_id", sa.UUID(), nullable=True, comment="Issuer or controlling organisation when the cryptoasset has one; null for genuinely decentralised native assets."),
        sa.Column("effective_from", sa.Date(), nullable=False, comment="First date for which this version of cryptoasset terms is effective."),
        sa.Column("effective_to", sa.Date(), nullable=True, comment="Last date for which this version of cryptoasset terms is effective."),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False, comment="Whether this is the current approved cryptoasset terms version."),
        sa.Column("sequence_no", sa.Integer(), server_default=sa.text("1"), nullable=False, comment="Monotonically increasing terms version sequence for the cryptoasset instrument."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'DRAFT'"), nullable=False, comment="Lifecycle status such as DRAFT, ACTIVE, SUPERSEDED, or RETIRED."),
        sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Source payload evidencing this cryptoasset terms version when available."),
        sa.ForeignKeyConstraint(["instrument_node_id"], ["secm.instrument.instrument_node_id"]),
        sa.ForeignKeyConstraint(["issuer_organisation_id"], ["secm.organisation.organisation_id"]),
        sa.ForeignKeyConstraint(["source_payload_id"], ["ing.source_payload.source_payload_id"]),
        sa.PrimaryKeyConstraint("crypto_asset_terms_id"),
        sa.UniqueConstraint("instrument_node_id", "sequence_no", name="uq_crypto_asset_terms_version"),
        sa.CheckConstraint("asset_subtype IN ('NATIVE', 'TOKEN', 'STABLECOIN', 'WRAPPED', 'BRIDGED', 'OTHER')", name="ck_crypto_asset_terms_subtype"),
        sa.CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_crypto_asset_terms_valid_period"),
        schema="secm",
    )
    op.create_table(
        "crypto_asset_deployment",
        sa.Column("crypto_asset_deployment_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one chain-specific cryptoasset deployment."),
        sa.Column("instrument_node_id", sa.UUID(), nullable=False, comment="Economic cryptoasset instrument deployed on the network."),
        sa.Column("crypto_network_id", sa.UUID(), nullable=False, comment="Blockchain or distributed-ledger network hosting the deployment."),
        sa.Column("deployment_kind", sa.String(length=30), nullable=False, comment="Deployment kind such as NATIVE, TOKEN_CONTRACT, WRAPPED, or BRIDGED."),
        sa.Column("contract_address", sa.String(length=500), nullable=True, comment="Chain-specific token or contract address; null for a native asset without a contract."),
        sa.Column("token_standard", sa.String(length=80), nullable=True, comment="Token standard or ledger asset type such as ERC20, SPL, CW20, or native ledger asset."),
        sa.Column("on_chain_symbol", sa.String(length=80), nullable=True, comment="Symbol exposed by the chain deployment, which may differ from the canonical asset symbol."),
        sa.Column("decimals", sa.Integer(), nullable=True, comment="Smallest-unit decimal precision exposed by the chain deployment."),
        sa.Column("is_canonical", sa.Boolean(), server_default=sa.text("false"), nullable=False, comment="Whether this is the issuer or protocol's canonical deployment for the asset."),
        sa.Column("effective_from", sa.Date(), nullable=False, comment="First date for which this deployment is valid."),
        sa.Column("effective_to", sa.Date(), nullable=True, comment="Last date for which this deployment is valid."),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False, comment="Whether this deployment is currently operationally valid."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status such as ACTIVE, PAUSED, DEPRECATED, or RETIRED."),
        sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Source payload evidencing the chain deployment when available."),
        sa.ForeignKeyConstraint(["instrument_node_id"], ["secm.instrument.instrument_node_id"]),
        sa.ForeignKeyConstraint(["crypto_network_id"], ["secm.crypto_network.crypto_network_id"]),
        sa.ForeignKeyConstraint(["source_payload_id"], ["ing.source_payload.source_payload_id"]),
        sa.PrimaryKeyConstraint("crypto_asset_deployment_id"),
        sa.UniqueConstraint("instrument_node_id", "crypto_network_id", "contract_address", name="uq_crypto_asset_deployment_network_address"),
        sa.CheckConstraint("deployment_kind IN ('NATIVE', 'TOKEN_CONTRACT', 'WRAPPED', 'BRIDGED')", name="ck_crypto_asset_deployment_kind"),
        sa.CheckConstraint("(deployment_kind = 'NATIVE' AND contract_address IS NULL) OR (deployment_kind <> 'NATIVE' AND contract_address IS NOT NULL)", name="ck_crypto_asset_deployment_address"),
        sa.CheckConstraint("decimals IS NULL OR (decimals >= 0 AND decimals <= 36)", name="ck_crypto_asset_deployment_decimals"),
        sa.CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_crypto_asset_deployment_valid_period"),
        schema="secm",
    )
    op.execute(
        sa.text(
            """
            INSERT INTO secm.crypto_network
                (network_code, display_name, network_family, chain_identifier, native_currency_code, status, sort_order)
            VALUES
                ('BITCOIN_MAINNET', 'Bitcoin mainnet', 'BITCOIN', 'bitcoin-mainnet', 'BTC', 'ACTIVE', 10),
                ('ETHEREUM_MAINNET', 'Ethereum mainnet', 'EVM', '1', 'ETH', 'ACTIVE', 20),
                ('SOLANA_MAINNET', 'Solana mainnet', 'SOLANA', 'mainnet-beta', 'SOL', 'ACTIVE', 30),
                ('BASE_MAINNET', 'Base mainnet', 'EVM', '8453', 'ETH', 'ACTIVE', 40)
            ON CONFLICT (network_code) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_table("crypto_asset_deployment", schema="secm")
    op.drop_table("crypto_asset_terms", schema="secm")
    op.drop_table("crypto_network", schema="secm")
