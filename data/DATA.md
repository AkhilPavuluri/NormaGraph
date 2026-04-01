# Data directory

This folder holds **document inventory** files used to plan and validate what you will index before ingestion. It is a **human review step**, not a live corpus.

## Files

| File | Role |
|------|------|
| `document_inventory.csv` | Spreadsheet-friendly inventory (optional) |
| `document_inventory.md` | Markdown inventory template and table |
| `DATA.md` | This file |

## Usage

1. **Populate the inventory** — Add real documents you have or can source to `document_inventory.md` (or the CSV, if you prefer).
2. **Validate metadata** — Ensure required fields are present and consistent (dates, authority, jurisdiction, status).
3. **Review gaps** — Note missing relations, dates, or authority chains before indexing.
4. **When the inventory is complete** — Proceed to ingestion and indexing using your configured pipeline (see the repository root `README.md`). Do not skip the review step if you need reliable citations and retrieval.

## Important notes

- **Do not normalize canonical IDs in this file** — Treat this as a validation and planning list first.
- **Do not ingest from this folder alone** — The inventory describes intent; ingestion uses your configured storage and loaders.
- **Cloud setup is separate** — Credentials, buckets, and vector stores are configured via `.env` and deployment; this directory does not replace that.
- **Use real rows** — Placeholders are for structure only; production runs should reflect documents you actually control or can cite.

## Optional layout (later)

If you split validated vs rejected material on disk, you might use something like:

```
data/
├── validated/
│   ├── judgments/
│   ├── regulations/
│   ├── policies/
│   └── gos/
├── rejected/
├── quarantined/
└── metadata/
    ├── document_inventory.csv
    ├── validation_report.csv
    └── relations_map.csv
```

This layout is **optional**; adapt it to your org’s workflow.
