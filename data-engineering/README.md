# Data Engineering

This folder documents the data pipeline and the target relational storage design for deploying the project with a managed database.

## Contents

- `architecture/rds-architecture.md`
  The proposed PostgreSQL RDS layout, feature-serving flow, and Mermaid ER diagram.
- `sql/postgres-schema.sql`
  A starter schema matching the documented RDS design.

## Scope

The current application reads from local CSV, Parquet, and notebook-generated artifacts. The documentation here describes how to move those same entities into a production-friendly AWS RDS-backed setup without changing the product behavior.
