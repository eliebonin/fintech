# API contracts

This package will contain generated TypeScript request/response models and
client interfaces derived from versioned OpenAPI contracts.

It must not import SQLAlchemy/Python modules, expose database table internals,
or contain tenant credentials. Contracts should carry object UUID/type,
effective version/status, provenance, valuation-cut/information-cut fields, and
structured error codes where applicable.
