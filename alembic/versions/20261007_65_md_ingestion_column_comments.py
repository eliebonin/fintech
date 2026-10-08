"""Document ingestion-evidence columns without rewriting migration 64."""
from alembic import op

revision="20261007_65"
down_revision="20261007_64"
branch_labels=depends_on=None


def upgrade():
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_job.job_id IS 'Immutable UUIDv7 identifier for an ingestion execution.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_job.dataset_id IS 'Dataset whose acquisition and publication this job operates.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_job.namespace_id IS 'Source identifier namespace used by the exact job selection.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_job.tenant_id IS 'Tenant permitted to operate this dataset ingestion.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_job.actor_id IS 'Active tenant administrator who started the job.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_job.selection IS 'Ordered source symbols selected for this execution.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_job.request IS 'Exact inclusive start and end market dates requested.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_job.status IS 'Operational lifecycle outcome, separate from calendar quality certification.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_job.started_at_utc IS 'UTC timestamp when the job was recorded before acquisition.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_job.finished_at_utc IS 'UTC terminal timestamp; null only while the job is RUNNING.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_job.summary IS 'Immutable terminal execution counters and recovery evidence.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_attempt.attempt_id IS 'Immutable UUIDv7 identifier for one recorded request attempt or assessment.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_attempt.job_id IS 'Parent execution owning this attempt.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_attempt.symbol IS 'Exact source symbol within the parent job selection.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_attempt.request IS 'Inclusive attempt window within the parent job window.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_attempt.status IS 'Attempt lifecycle outcome, including failed or blocked acquisition.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_attempt.started_at_utc IS 'UTC timestamp recorded before download or resume assessment.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_attempt.finished_at_utc IS 'UTC terminal timestamp; null only while the attempt is RUNNING.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_attempt.delivery_run_id IS 'Matching immutable delivery, null when publication did not succeed.';")
    op.execute("COMMENT ON COLUMN md.market_data_ingestion_attempt.report IS 'Backoff, outcome and failure evidence; immutable after finalization.';")
    op.execute("COMMENT ON COLUMN md.market_data_mapping_history_review.review_id IS 'Immutable UUIDv7 identifier for attributed historical-continuity evidence.';")
    op.execute("COMMENT ON COLUMN md.market_data_mapping_history_review.mapping_id IS 'Source-to-listing mapping whose historical continuity was reviewed.';")
    op.execute("COMMENT ON COLUMN md.market_data_mapping_history_review.tenant_id IS 'Tenant within the reviewed mapping dataset scope.';")
    op.execute("COMMENT ON COLUMN md.market_data_mapping_history_review.actor_id IS 'Active MARKET_DATA tenant administrator who recorded the review.';")
    op.execute("COMMENT ON COLUMN md.market_data_mapping_history_review.market_from IS 'Inclusive first market date covered by the review.';")
    op.execute("COMMENT ON COLUMN md.market_data_mapping_history_review.market_to IS 'Inclusive last market date covered by the review.';")
    op.execute("COMMENT ON COLUMN md.market_data_mapping_history_review.decision IS 'APPROVED or REJECTED historical mapping continuity decision.';")
    op.execute("COMMENT ON COLUMN md.market_data_mapping_history_review.evidence_reference IS 'Nonblank reference or explanation supporting the review.';")
    op.execute("COMMENT ON COLUMN md.market_data_mapping_history_review.reviewed_at_utc IS 'UTC timestamp when the attributed review was recorded.';")
    op.execute("COMMENT ON COLUMN md.market_data_mapping_history_review.supersedes_review_id IS 'Current predecessor replaced for the exact same mapping and period.';")


def downgrade():
    raise RuntimeError("Forward-only: retain operational schema documentation.")
