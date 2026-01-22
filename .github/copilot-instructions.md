<!-- Guidance for AI coding agents working on this repository -->
# Copilot instructions — sqlserver-experiments

This file contains concise, actionable guidance to help AI coding agents be productive in this repository.

1. Quick project summary
- Purpose: small, focused experiments around SQL Server projects. The most active experiment is **Enchanted Bees** (a SQL DB + small Flask UI).
- Main components:
  - `experiments/enchanted-bees/EnchantedBeesDB/` — SSDT SQL Database Project: schema, seed scripts (`scripts/SeedData/*`).
  - `experiments/enchanted-bees/src/` — Python Flask app (`bee-admin.py`) and DB helper (`db-connect.py`).
  - `experiments/enchanted-bees/docker-compose.yml` — launches a SQL Server container used for local testing.

2. Key developer workflows (executable steps)
- Start local SQL Server: set `PASSWORD` and `EXTERNAL_PORT` and run from `experiments/enchanted-bees/`:

  ```bash
  # from experiments/enchanted-bees/
  export PASSWORD=YourStrong(!)Pass
  export EXTERNAL_PORT=1433
  docker compose up -d
  ```

- Build the database project (uses `dotnet build`):

  ```bash
  dotnet build experiments/enchanted-bees/EnchantedBeesDB/EnchantedBeesDB.sqlproj
  ```

  Note: when building inside VS Code the SQL Database Projects extension may set `SystemDacpacsLocation`; the explicit build shown in CI/terminal logs includes that property.

- Run the Flask admin UI:

  ```bash
  # set connection via DB_CONN_STRING or per-variable envs
  export DB_SERVER=localhost,1433
  export DB_DATABASE=EnchantedBeesDB
  python experiments/enchanted-bees/src/bee-admin.py
  ```

3. Project-specific patterns and conventions
- ODBC handling: both `db-connect.py` and `bee-admin.py` auto-select an available ODBC driver and prefer a full `DB_CONN_STRING` if provided. Prefer using `DB_CONN_STRING` when writing changes that touch connection logic.
- Seeds: seed SQL files in `EnchantedBeesDB/scripts/SeedData/` use stable GUIDs and `MERGE` statements — preserve GUID-based seeding when adding sample data.
- Schema vs code mismatch: `EnchantedBeesDB/Tables/SpeciesType.sql` defines the table `SpeciesType`, but `bee-admin.py` queries `dbo.Species`. Flag this as a behavioral inconsistency to the author when suggesting fixes.
- Minimal UI: `bee-admin.py` uses `render_template_string` and embeds a small Bootstrap table; expect no separate template files.

4. Integration & external dependencies
- Docker image: `mcr.microsoft.com/mssql/server:2022-latest` (see `docker-compose.yml`).
- Python deps: check `experiments/enchanted-bees/src/requirements.txt` if modifying or adding Python code; current code uses `flask`, `pyodbc`, and `python-dotenv`.
- Database project requires .NET SDK for `dotnet build` and (optionally) the VS Code SQL Database Projects extension for convenient deployment.

5. Safe edit guidance for AI agents (do this first)
- Read `experiments/enchanted-bees/src/db-connect.py` and `bee-admin.py` before changing connection behavior.
- When modifying schema or seeds, update `EnchantedBeesDB/scripts/Script.PostDeployment.sql` to include seeds so builds remain reproducible.
- If adding queries, use fully-qualified names (`dbo.TableName`) and prefer the actual table names used under `EnchantedBeesDB/Tables/`.

6. Representative files to inspect for context
- `experiments/enchanted-bees/src/db-connect.py` — connection helper and driver selection.
- `experiments/enchanted-bees/src/bee-admin.py` — small Flask app and query examples.
- `experiments/enchanted-bees/EnchantedBeesDB/Tables/*.sql` — table definitions and constraints.
- `experiments/enchanted-bees/EnchantedBeesDB/scripts/SeedData/*.sql` — seeding approach (GUIDs + MERGE).

If any section is unclear or you want more examples (tests, CI, or a deploy script), tell me which area to expand and I will update this file.
