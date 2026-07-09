# Database Migrations

Migrations are executable Python scripts that apply or rollback schema changes.
Run them in order by numeric prefix.

## Usage

```bash
# Apply migration 001
python database/migrations/001_initial_schema.py

# Rollback migration 001
python database/migrations/001_initial_schema.py --down
```

## Current Migrations

| # | File | Description |
|---|------|-------------|
| 001 | `001_initial_schema.py` | Creates raw, staging, curated, quality schemas and all tables |
