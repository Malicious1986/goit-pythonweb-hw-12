## ------------------------------- Builder Stage ------------------------------ ## 
FROM python:3.13-bookworm AS builder

RUN apt-get update && apt-get install --no-install-recommends -y \
        build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Download the latest installer, install it and then remove it
ADD https://astral.sh/uv/install.sh /install.sh
RUN chmod -R 655 /install.sh && /install.sh && rm /install.sh

# Set up the UV environment path correctly
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY ./pyproject.toml .
COPY ./README.md .
COPY ./src ./src

RUN uv sync

## ------------------------------- Production Stage ------------------------------ ##
FROM python:3.13-slim-bookworm AS production

# Set environment variables for DB and access token
ARG POSTGRES_DB
ARG POSTGRES_USER
ARG POSTGRES_PASSWORD
ARG DB_URL
ARG JWT_SECRET
ARG JWT_ALGORITHM
ARG JWT_EXPIRATION_SECONDS
ARG MAIL_USERNAME
ARG MAIL_PASSWORD
ARG MAIL_FROM
ARG MAIL_PORT
ARG MAIL_SERVER
ARG MAIL_FROM_NAME
ARG MAIL_STARTTLS
ARG MAIL_SSL_TLS
ARG USE_CREDENTIALS
ARG VALIDATE_CERTS
ARG ORIGINS
ARG CLOUDINARY_NAME
ARG CLOUDINARY_API_KEY
ARG CLOUDINARY_API_SECRET

# Set environment variables for DB and access token (values may be provided via build-args)
ENV POSTGRES_DB=${POSTGRES_DB}
ENV POSTGRES_USER=${POSTGRES_USER}
ENV POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
ENV DB_URL=${DB_URL}
ENV JWT_SECRET=${JWT_SECRET}
ENV JWT_ALGORITHM=${JWT_ALGORITHM}
ENV JWT_EXPIRATION_SECONDS=${JWT_EXPIRATION_SECONDS}
ENV MAIL_USERNAME=${MAIL_USERNAME}
ENV MAIL_PASSWORD=${MAIL_PASSWORD}
ENV MAIL_FROM=${MAIL_FROM}
ENV MAIL_PORT=${MAIL_PORT}
ENV MAIL_SERVER=${MAIL_SERVER}
ENV MAIL_FROM_NAME=${MAIL_FROM_NAME}
ENV MAIL_STARTTLS=${MAIL_STARTTLS}
ENV MAIL_SSL_TLS=${MAIL_SSL_TLS}
ENV USE_CREDENTIALS=${USE_CREDENTIALS}
ENV VALIDATE_CERTS=${VALIDATE_CERTS}
ENV ORIGINS=${ORIGINS}
ENV CLOUDINARY_NAME=${CLOUDINARY_NAME}
ENV CLOUDINARY_API_KEY=${CLOUDINARY_API_KEY}
ENV CLOUDINARY_API_SECRET=${CLOUDINARY_API_SECRET}

WORKDIR /app

COPY ./main.py .
COPY ./alembic.ini .
COPY ./migrations ./migrations
COPY /src src
COPY --from=builder /app/.venv .venv

# Set up environment variables for production
ENV PATH="/app/.venv/bin:$PATH"

# Expose the specified port for FastAPI
EXPOSE $PORT

# Start the application with Uvicorn in production mode, using environment variable references
CMD ["uvicorn", "src.main:app", "--log-level", "info", "--host", "0.0.0.0" , "--port", "8080"]