# scripts/

Utility scripts (data seeding, batch analysis, KB rebuilds, etc.). Empty for now.

Conventions when adding scripts:

- Plain Python or Node, no global side effects on import.
- Read paths from environment variables, never hardcode absolute paths.
- Print a short usage banner when run without arguments.
