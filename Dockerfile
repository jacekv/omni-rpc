FROM python:3.11-slim AS base

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction --no-ansi --only main --no-root

COPY README.md ./
COPY src/ src/
COPY config/ config/

RUN poetry install --no-interaction --no-ansi --only main

COPY entrypoint.sh ./

EXPOSE 8000

ENV OMNI_RPC_ENVIRONMENT=prod

ENTRYPOINT ["./entrypoint.sh"]
CMD ["python", "-m", "omni_rpc.main", "--environment", "dev"]
