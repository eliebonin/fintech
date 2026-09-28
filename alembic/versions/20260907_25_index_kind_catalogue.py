"""Add governed index-kind semantics for onboarding and API catalogues."""

from alembic import op
import sqlalchemy as sa


revision = "20260907_25"
down_revision = "20260907_24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "index_kind_catalogue",
        sa.Column("index_kind_catalogue_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one governed index-kind catalogue entry."),
        sa.Column("index_kind_code", sa.String(length=40), nullable=False, comment="Stable controlled code used by index terms, proposals, and integrations, such as PUBLIC or PROPRIETARY."),
        sa.Column("display_name", sa.String(length=150), nullable=False, comment="Human-readable label shown to Operations users."),
        sa.Column("description", sa.Text(), nullable=False, comment="Governed plain-language meaning of the index kind."),
        sa.Column("dissemination_class", sa.String(length=30), nullable=False, comment="Whether the index is publicly disseminated, restricted, private, or bespoke; this describes access rather than methodology ownership."),
        sa.Column("methodology_ownership", sa.String(length=40), nullable=False, comment="Ownership or control of the methodology, such as PROVIDER_OWNED, CLIENT_OWNED, OPEN_OR_PUBLIC, or MIXED."),
        sa.Column("example_text", sa.String(length=500), nullable=True, comment="Short representative example that helps Operations choose the correct semantic category."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status of the governed index-kind catalogue entry."),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False, comment="Display ordering value for index-kind selection lists."),
        sa.PrimaryKeyConstraint("index_kind_catalogue_id"),
        sa.UniqueConstraint("index_kind_code", name="uq_index_kind_catalogue_code"),
        schema="secm",
    )
    op.execute(
        sa.text(
            """
            INSERT INTO secm.index_kind_catalogue
                (index_kind_code, display_name, description, dissemination_class, methodology_ownership, example_text, status, sort_order)
            VALUES
                ('PUBLIC', 'Public benchmark', 'Publicly disseminated or observable benchmark. Public access does not mean the methodology is open; the provider may still own and restrict the methodology.', 'PUBLIC', 'PROVIDER_OWNED', 'S&P 500: publicly quoted benchmark with provider-owned methodology.', 'ACTIVE', 10),
                ('QIS', 'QIS / quantitative strategy', 'Rules-based quantitative investment strategy expressed as an index. It is commonly provider- or client-designed and may be public, restricted, or private.', 'RESTRICTED', 'MIXED', 'A bank QIS index with a documented ruleset and controlled distribution.', 'ACTIVE', 20),
                ('PROPRIETARY', 'Proprietary methodology', 'Index whose methodology, calculation rules, or constituent process is owned or controlled by a provider or client. It may still have a public price or identifier.', 'RESTRICTED', 'PROVIDER_OWNED', 'A provider-owned thematic or systematic index distributed to selected users.', 'ACTIVE', 30),
                ('CUSTOM_BASKET', 'Custom basket', 'Bespoke index or basket maintained for a client, product, or internal use. Its constituent snapshots and rules are governed separately from this category code.', 'PRIVATE', 'CLIENT_OWNED', 'A manually maintained client basket whose constituents are snapshotted over time.', 'ACTIVE', 40)
            ON CONFLICT (index_kind_code) DO NOTHING
            """
        )
    )
    op.create_foreign_key(
        "fk_index_terms_index_kind_catalogue",
        "index_terms",
        "index_kind_catalogue",
        ["index_kind"],
        ["index_kind_code"],
        source_schema="secm",
        referent_schema="secm",
    )


def downgrade() -> None:
    op.drop_constraint("fk_index_terms_index_kind_catalogue", "index_terms", schema="secm", type_="foreignkey")
    op.drop_table("index_kind_catalogue", schema="secm")
