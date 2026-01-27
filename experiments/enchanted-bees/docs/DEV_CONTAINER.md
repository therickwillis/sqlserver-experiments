This repository includes a development container image configured for the Enchanted Bees experiment.

Service: `dev` in `docker-compose.yml` (builds from `dev.Dockerfile`).

Included tools:
- .NET SDK 7.0 (for building the SQL Database project)
- Python 3 (for the Flask admin UI)
- `sqlcmd` / `mssql-tools` (to interact with the local SQL Server container)
- `git`, `curl`

Usage (from `experiments/enchanted-bees`):

```bash
# build and start SQL Server + dev container
export PASSWORD=YourStrong(!)Pass
export EXTERNAL_PORT=1433
docker compose up -d --build sqlserver dev

# open a shell into the dev container
docker compose exec dev bash
```

Inside the container you can create a virtualenv, install `requirements.txt` from `src/`, and run `bee-admin.py`.

Note: the dev image now installs Python dependencies from `src/requirements.txt` at build time. If you change `requirements.txt`, rebuild the image:

```bash
docker compose build --no-cache dev
docker compose up -d --build dev
```

Credentials / user:
- **username**: `dev` (no password set in image)
- The image no longer embeds a password. We grant `dev` passwordless sudo for convenience.

User mapping and permissions:
- You can map the container UID/GID to your host user at build time with `USER_ID` / `GROUP_ID` args (defaults to 1000). Example in `docker compose`:

```bash
docker compose build --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) dev
```

Runtime fast-iteration mode:
- If you want fast Python dependency iteration without rebuilding the image, set `DEV_MODE=1` in the `dev` service environment. On container start the entrypoint will install `/workspace/src/requirements.txt` into the user's site-packages (`--user`). This is useful for day-to-day development.

Example to start with `DEV_MODE` enabled:

```bash
DEV_MODE=1 docker compose up -d --build sqlserver dev
docker compose exec dev bash
python3 -m pip list --user
```

To become root one-off inside the container:

```bash
sudo -i
```
