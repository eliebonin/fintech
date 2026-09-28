# Shared UI package

This package is reserved for presentational components and design-system
primitives that have more than one consumer.

Components should not own tenant authorization, database access, market-data
selection, or trade/NAV business rules. Domain-specific behaviour belongs in
an application feature or data-access package until a second consumer justifies
promotion to shared code.
