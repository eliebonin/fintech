"""Invented seed data has explicit origin evidence, never a fabricated contract."""
from alembic import op

revision='20261030_106'
down_revision='20261030_105'
branch_labels=None
depends_on=None


def upgrade():
    op.drop_constraint('ck_dataset_access_scope','dataset_access_profile',schema='md',type_='check')
    op.create_check_constraint('ck_dataset_access_scope','dataset_access_profile',"usage_scope IN ('PERSONAL','COMMERCIAL','SYNTHETIC')",schema='md')
    op.drop_constraint('ck_licence_grant_basis','licence_activity_grant',schema='md',type_='check')
    op.create_check_constraint('ck_licence_grant_basis','licence_activity_grant',
        "usage_scope IN ('PERSONAL','COMMERCIAL','SYNTHETIC') AND evidence_basis IN ('CONTRACT','PERSONAL_DECLARATION','PERSONAL_RESEARCH_EXCEPTION','SYNTHETIC_ORIGIN') AND ((usage_scope='SYNTHETIC') = (evidence_basis='SYNTHETIC_ORIGIN'))",schema='md')
    op.alter_column('dataset_access_profile','usage_scope',schema='md',comment='PERSONAL, COMMERCIAL or invented-data-only SYNTHETIC scope; scope does not create activity grants.')
    op.alter_column('licence_activity_grant','usage_scope',schema='md',comment='PERSONAL, COMMERCIAL or invented-data-only SYNTHETIC use covered by this grant.')
    op.alter_column('licence_activity_grant','evidence_basis',schema='md',comment='CONTRACT, PERSONAL_DECLARATION, PERSONAL_RESEARCH_EXCEPTION or invented-data-only SYNTHETIC_ORIGIN; synthetic/personal evidence is not commercial provider permission.')


def downgrade():
    # Existing synthetic evidence must be removed by an explicit maintenance
    # decision before downgrade; never rewrite it into claimed commercial rights.
    op.drop_constraint('ck_licence_grant_basis','licence_activity_grant',schema='md',type_='check')
    op.create_check_constraint('ck_licence_grant_basis','licence_activity_grant',
        "usage_scope IN ('PERSONAL','COMMERCIAL') AND evidence_basis IN ('CONTRACT','PERSONAL_DECLARATION','PERSONAL_RESEARCH_EXCEPTION')",schema='md')
    op.drop_constraint('ck_dataset_access_scope','dataset_access_profile',schema='md',type_='check')
    op.create_check_constraint('ck_dataset_access_scope','dataset_access_profile',"usage_scope IN ('PERSONAL','COMMERCIAL')",schema='md')
