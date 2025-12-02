# goit-pythonweb-hw-12

Simple FastAPI project (contacts API).

## Requirements

- Python 3.12+
- Docker & Docker Compose (for running the API + Postgres together)

Dependencies are defined in `pyproject.toml` and the project uses Poetry for dependency management.

## Quick start (recommended using Docker Compose)

The repository includes a `docker-compose.yml` that runs the `api` service and a `db` (Postgres) service. Compose automatically loads variables from a `.env` file if present.

1. (Optional) Create a `.env` file in the project root with runtime values. Example (use your own secrets — do NOT commit them):

```env
# Postgres
POSTGRES_DB=contacts
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your_postgres_password>
# or full DB URL (recommended for runtime):
DB_URL=postgresql+asyncpg://<user>:<password>@db:5432/contacts

# JWT
JWT_SECRET=<your_jwt_secret_key>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_SECONDS=3600

# Mail (example placeholders)
MAIL_USERNAME=<your_smtp_username>
MAIL_PASSWORD=<your_smtp_password>
MAIL_FROM=<from_email_address>
MAIL_PORT=465
MAIL_SERVER=<smtp_server>
MAIL_FROM_NAME="Rest API Service"
MAIL_STARTTLS=false
MAIL_SSL_TLS=true
USE_CREDENTIALS=true
VALIDATE_CERTS=true

# Frontend origins
ORIGINS=http://localhost:3000

# Third-party services
CLOUDINARY_NAME=<cloudinary_name>
CLOUDINARY_API_KEY=<cloudinary_api_key>
CLOUDINARY_API_SECRET=<cloudinary_api_secret>
```

2. Build and start the stack:

```bash
docker compose up --build
```

This exposes the API at `http://0.0.0.0:8000` (mapped from the container) and Postgres on `5432`.

3. Run database migrations (after DB is healthy):

```bash
# from the project root — runs alembic inside the running api container
docker compose exec api alembic upgrade head
```

## Build with build-time args (bake envs into image)

If you want to bake environment values into the image (not recommended for secrets), the `Dockerfile` declares build-time `ARG`s and sets corresponding `ENV` values. You can pass all variables as `--build-arg`.

Example (zsh — disable history expansion first if any values contain `!`):

```bash
set +H
docker build \
	--no-cache \
	--build-arg POSTGRES_DB=contacts \
	--build-arg POSTGRES_USER=postgres \
	--build-arg POSTGRES_PASSWORD='<your_postgres_password>' \
	--build-arg DB_URL='postgresql+asyncpg://<user>:<password>@localhost:5432/contacts' \
	--build-arg JWT_SECRET='<your_jwt_secret_key>' \
	--build-arg JWT_ALGORITHM='HS256' \
	--build-arg JWT_EXPIRATION_SECONDS='3600' \
	--build-arg MAIL_USERNAME='<your_smtp_username>' \
	--build-arg MAIL_PASSWORD='<your_smtp_password>' \
	--build-arg MAIL_FROM='<from_email@example.com>' \
	--build-arg MAIL_PORT='465' \
	--build-arg MAIL_SERVER='<smtp_server>' \
	--build-arg MAIL_FROM_NAME='Rest API Service' \
	--build-arg MAIL_STARTTLS='false' \
	--build-arg MAIL_SSL_TLS='true' \
	--build-arg USE_CREDENTIALS='true' \
	--build-arg VALIDATE_CERTS='true' \
	--build-arg ORIGINS='http://localhost:3000' \
	--build-arg CLOUDINARY_NAME='<cloudinary_name>' \
	--build-arg CLOUDINARY_API_KEY='<cloudinary_api_key>' \
	--build-arg CLOUDINARY_API_SECRET='<cloudinary_api_secret>' \
	-t goit-pythonweb-hw-10-api:buildarg .
```

Then run the container (or use `docker compose` to run the stack):

```bash
docker compose up -d
```

## Checking logs & troubleshooting

- Tail logs for the `api` service:
  ```bash
  docker compose logs -f api
  ```
- Tail recent logs (non-interactive):
  ```bash
  docker compose logs --no-color --tail 200 api
  ```

## Running locally without Docker

You can still run locally with Poetry or a venv — ensure `.env` values are set in your environment or a `.env` file and run with Uvicorn (or `fastapi dev`).
