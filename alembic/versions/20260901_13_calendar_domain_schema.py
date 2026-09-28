"""Move calendar reference data into the dedicated calendar domain schema."""

from alembic import op
import sqlalchemy as sa


revision = "20260901_13"
down_revision = "20260901_12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create calendar tables, preserve existing definitions, and retarget consumers."""

    bind = op.get_bind()
    op.execute('CREATE SCHEMA IF NOT EXISTS "cal"')

    op.create_table(
        "market_calendar",
        sa.Column("market_calendar_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for a governed market or settlement calendar definition."),
        sa.Column("calendar_code", sa.String(length=100), nullable=False, comment="Stable unique calendar code such as XLON_TRADING, TARGET2, NYSE, or CRYPTO_24X7."),
        sa.Column("display_name", sa.String(length=250), nullable=False, comment="Human-readable name of the calendar."),
        sa.Column("timezone_name", sa.String(length=100), nullable=False, comment="IANA timezone used by the calendar."),
        sa.Column("calendar_kind", sa.String(length=40), nullable=False, comment="Calendar use such as TRADING, SETTLEMENT, FIXING, HOLIDAY, or CONTINUOUS_24X7."),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'ACTIVE'"), comment="Lifecycle status of the calendar definition."),
        sa.UniqueConstraint("calendar_code"),
        schema="cal",
    )
    op.create_table(
        "market_calendar_session",
        sa.Column("market_calendar_session_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for one calendar date's session definition."),
        sa.Column("market_calendar_id", sa.UUID(), sa.ForeignKey("cal.market_calendar.market_calendar_id"), nullable=False, comment="Calendar to which this dated session belongs."),
        sa.Column("session_date", sa.Date(), nullable=False, comment="Local calendar date represented by this session definition."),
        sa.Column("session_status", sa.String(length=30), nullable=False, comment="Session state such as OPEN, CLOSED, or HALF_DAY."),
        sa.Column("open_local_time", sa.Time(), nullable=True, comment="Local wall-clock opening time for an open or half-day session."),
        sa.Column("close_local_time", sa.Time(), nullable=True, comment="Local wall-clock closing time for an open or half-day session."),
        sa.Column("source_reference", sa.String(length=250), nullable=True, comment="Source or publication reference supporting this session definition."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="UTC timestamp at which this session definition was created."),
        sa.UniqueConstraint("market_calendar_id", "session_date", name="uq_market_calendar_session_date"),
        sa.CheckConstraint(
            "(session_status = 'CLOSED' AND open_local_time IS NULL AND close_local_time IS NULL) OR "
            "(session_status IN ('OPEN', 'HALF_DAY') AND open_local_time IS NOT NULL AND close_local_time IS NOT NULL)",
            name="ck_market_calendar_session_times",
        ),
        schema="cal",
    )
    op.create_table(
        "market_calendar_holiday",
        sa.Column("market_calendar_holiday_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for one calendar holiday or closure reason."),
        sa.Column("market_calendar_id", sa.UUID(), sa.ForeignKey("cal.market_calendar.market_calendar_id"), nullable=False, comment="Calendar to which this holiday entry belongs."),
        sa.Column("holiday_date", sa.Date(), nullable=False, comment="Local calendar date on which the holiday or closure applies."),
        sa.Column("holiday_name", sa.String(length=250), nullable=False, comment="Human-readable holiday or closure name."),
        sa.Column("holiday_kind", sa.String(length=40), nullable=False, server_default=sa.text("'FULL_CLOSE'"), comment="Closure kind such as FULL_CLOSE, BANK_HOLIDAY, or MARKET_HOLIDAY."),
        sa.Column("source_reference", sa.String(length=250), nullable=True, comment="Source or publication reference supporting this holiday entry."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="UTC timestamp at which this holiday definition was created."),
        sa.UniqueConstraint("market_calendar_id", "holiday_date", name="uq_market_calendar_holiday_date"),
        schema="cal",
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO cal.market_calendar (
                market_calendar_id, calendar_code, display_name, timezone_name,
                calendar_kind, status
            )
            SELECT market_calendar_id, calendar_code, display_name, timezone_name,
                   calendar_kind, status
            FROM secm.market_calendar
            """
        )
    )

    for constraint_name, table_name in (
        ("market_venue_market_calendar_id_fkey", "market_venue"),
        ("schedule_calendar_id_fkey", "schedule"),
        ("valuation_policy_rule_market_calendar_id_fkey", "valuation_policy_rule"),
    ):
        op.drop_constraint(constraint_name, table_name, schema="secm" if table_name != "valuation_policy_rule" else "ten", type_="foreignkey")

    op.create_foreign_key(
        "fk_market_venue_calendar",
        "market_venue",
        "market_calendar",
        ["market_calendar_id"],
        ["market_calendar_id"],
        source_schema="secm",
        referent_schema="cal",
    )
    op.create_foreign_key(
        "fk_schedule_calendar",
        "schedule",
        "market_calendar",
        ["calendar_id"],
        ["market_calendar_id"],
        source_schema="secm",
        referent_schema="cal",
    )
    op.create_foreign_key(
        "fk_valuation_policy_rule_calendar",
        "valuation_policy_rule",
        "market_calendar",
        ["market_calendar_id"],
        ["market_calendar_id"],
        source_schema="ten",
        referent_schema="cal",
    )
    op.drop_table("market_calendar", schema="secm")


def downgrade() -> None:
    """Restore the legacy security-master calendar location and remove calendar tables."""

    bind = op.get_bind()

    op.drop_constraint("fk_market_venue_calendar", "market_venue", schema="secm", type_="foreignkey")
    op.drop_constraint("fk_schedule_calendar", "schedule", schema="secm", type_="foreignkey")
    op.drop_constraint("fk_valuation_policy_rule_calendar", "valuation_policy_rule", schema="ten", type_="foreignkey")

    op.create_table(
        "market_calendar",
        sa.Column("market_calendar_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for a governed market or settlement calendar definition."),
        sa.Column("calendar_code", sa.String(length=100), nullable=False, comment="Stable unique calendar code such as XLON_TRADING, TARGET2, NYSE, or CRYPTO_24X7."),
        sa.Column("display_name", sa.String(length=250), nullable=False, comment="Human-readable name of the calendar."),
        sa.Column("timezone_name", sa.String(length=100), nullable=False, comment="IANA timezone used by the calendar."),
        sa.Column("calendar_kind", sa.String(length=40), nullable=False, comment="Calendar use such as TRADING, SETTLEMENT, FIXING, HOLIDAY, or CONTINUOUS_24X7."),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'ACTIVE'"), comment="Lifecycle status of the calendar definition."),
        sa.UniqueConstraint("calendar_code"),
        schema="secm",
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO secm.market_calendar (
                market_calendar_id, calendar_code, display_name, timezone_name,
                calendar_kind, status
            )
            SELECT market_calendar_id, calendar_code, display_name, timezone_name,
                   calendar_kind, status
            FROM cal.market_calendar
            """
        )
    )
    op.create_foreign_key(
        "market_venue_market_calendar_id_fkey",
        "market_venue",
        "market_calendar",
        ["market_calendar_id"],
        ["market_calendar_id"],
        source_schema="secm",
        referent_schema="secm",
    )
    op.create_foreign_key(
        "schedule_calendar_id_fkey",
        "schedule",
        "market_calendar",
        ["calendar_id"],
        ["market_calendar_id"],
        source_schema="secm",
        referent_schema="secm",
    )
    op.create_foreign_key(
        "valuation_policy_rule_market_calendar_id_fkey",
        "valuation_policy_rule",
        "market_calendar",
        ["market_calendar_id"],
        ["market_calendar_id"],
        source_schema="ten",
        referent_schema="secm",
    )
    op.drop_table("market_calendar_holiday", schema="cal")
    op.drop_table("market_calendar_session", schema="cal")
    op.drop_table("market_calendar", schema="cal")
    op.execute('DROP SCHEMA IF EXISTS "cal"')
