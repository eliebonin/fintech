"""Point-in-time corporate-action derivation without rewriting source facts."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Connection, or_, select

from . import models as m


@dataclass(frozen=True)
class DerivedObservation:
    """A calculated market-data value and the factors visible at an information cut."""

    observation_id: UUID
    raw_value: Decimal
    derived_value: Decimal
    adjustment_factor_ids: tuple[UUID, ...]
    adjustment_basis: str


@dataclass(frozen=True)
class DerivedPosition:
    """A calculated position quantity and the corporate actions visible at a cut."""

    position_snapshot_line_id: UUID
    raw_quantity: Decimal
    derived_quantity: Decimal
    corporate_action_ids: tuple[UUID, ...]


def derive_adjusted_observation(
    connection: Connection,
    observation_id: UUID,
    adjustment_basis: str,
    information_cutoff_utc: datetime,
) -> DerivedObservation:
    """Derive a factor-adjusted value using only actions known by the stated cut.

    The function only accepts RAW observations.  It intentionally returns a
    derived value rather than updating the raw observation or pretending that a
    current vendor-restated history recreates the historic information set.
    """

    if information_cutoff_utc.tzinfo is None:
        raise ValueError("information_cutoff_utc must be timezone-aware")
    observation = connection.execute(
        select(m.market_data_observation).where(
            m.market_data_observation.c.market_data_observation_id == observation_id
        )
    ).mappings().one_or_none()
    if observation is None:
        raise ValueError("Unknown market_data_observation_id")
    if observation["value_basis"] != "RAW":
        raise ValueError("Only RAW observations may receive a corporate-action adjustment")
    if observation["market_date"] is None:
        raise ValueError("A market_date is required to derive adjusted history")

    factors = [
        dict(row)
        for row in connection.execute(
            select(m.market_data_adjustment_factor)
            .select_from(
                m.market_data_adjustment_factor.join(
                    m.corporate_action,
                    m.market_data_adjustment_factor.c.corporate_action_id
                    == m.corporate_action.c.corporate_action_id,
                )
            )
            .where(
                m.market_data_adjustment_factor.c.raw_market_data_series_id
                == observation["market_data_series_id"],
                m.market_data_adjustment_factor.c.adjustment_basis == adjustment_basis,
                m.market_data_adjustment_factor.c.effective_date > observation["market_date"],
                m.corporate_action.c.status.in_(("CONFIRMED", "COMPLETED")),
                m.corporate_action.c.recorded_at_utc <= information_cutoff_utc,
            )
            .order_by(
                m.market_data_adjustment_factor.c.effective_date.asc(),
                m.market_data_adjustment_factor.c.market_data_adjustment_factor_id.asc(),
            )
        ).mappings()
    ]
    derived_value = Decimal(observation["value"])
    for factor in factors:
        derived_value *= Decimal(factor["factor"])
    return DerivedObservation(
        observation_id=observation_id,
        raw_value=Decimal(observation["value"]),
        derived_value=derived_value,
        adjustment_factor_ids=tuple(factor["market_data_adjustment_factor_id"] for factor in factors),
        adjustment_basis=adjustment_basis,
    )


def derive_adjusted_position(
    connection: Connection,
    position_snapshot_line_id: UUID,
    information_cutoff_utc: datetime,
) -> DerivedPosition:
    """Derive split/bonus quantity without mutating the original position snapshot."""

    if information_cutoff_utc.tzinfo is None:
        raise ValueError("information_cutoff_utc must be timezone-aware")
    line = connection.execute(
        select(
            m.position_snapshot_line.c.position_snapshot_line_id,
            m.position_snapshot_line.c.reference_node_id,
            m.position_snapshot_line.c.quantity,
            m.position_snapshot.c.as_of_date,
        )
        .select_from(
            m.position_snapshot_line.join(
                m.position_snapshot,
                m.position_snapshot_line.c.position_snapshot_id
                == m.position_snapshot.c.position_snapshot_id,
            )
        )
        .where(m.position_snapshot_line.c.position_snapshot_line_id == position_snapshot_line_id)
    ).mappings().one_or_none()
    if line is None:
        raise ValueError("Unknown position_snapshot_line_id")
    instrument_node_id = connection.scalar(
        select(m.listing.c.instrument_node_id).where(
            m.listing.c.listing_node_id == line["reference_node_id"]
        )
    ) or line["reference_node_id"]
    actions = [
        dict(row)
        for row in connection.execute(
            select(m.corporate_action.c.corporate_action_id, m.corporate_action_effect.c.ratio)
            .select_from(
                m.corporate_action.join(
                    m.corporate_action_effect,
                    m.corporate_action.c.corporate_action_id
                    == m.corporate_action_effect.c.corporate_action_id,
                ).join(
                    m.corporate_action_date,
                    m.corporate_action.c.corporate_action_id
                    == m.corporate_action_date.c.corporate_action_id,
                )
            )
            .where(
                m.corporate_action.c.affected_instrument_node_id == instrument_node_id,
                m.corporate_action.c.status.in_(("CONFIRMED", "COMPLETED")),
                m.corporate_action.c.recorded_at_utc <= information_cutoff_utc,
                m.corporate_action_effect.c.effect_type == "QUANTITY_CHANGE",
                m.corporate_action_effect.c.ratio.is_not(None),
                m.corporate_action_date.c.date_role == "EFFECTIVE",
                m.corporate_action_date.c.date_value <= line["as_of_date"],
            )
            .order_by(m.corporate_action_date.c.date_value.asc(), m.corporate_action.c.corporate_action_id.asc())
        ).mappings()
    ]
    derived_quantity = Decimal(line["quantity"])
    for action in actions:
        derived_quantity *= Decimal(action["ratio"])
    return DerivedPosition(
        position_snapshot_line_id=position_snapshot_line_id,
        raw_quantity=Decimal(line["quantity"]),
        derived_quantity=derived_quantity,
        corporate_action_ids=tuple(action["corporate_action_id"] for action in actions),
    )
