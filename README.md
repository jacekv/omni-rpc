## Setup

```
poetry install
poetry run omni-rpc init-chains
```

This will install the dependencies and download the ethereum-lists/chains repository.

## Start the service

```
poetry run python -m omni_rpc.main
```

By default this starts the server on `127.0.0.1:8000` using the `dev` environment config.

To use a different environment:

```
poetry run python -m omni_rpc.main --environment staging
poetry run python -m omni_rpc.main --environment prod
```

## Tests

```
poetry run pytest
```

## Configuration

Environment-specific config files live in `config/`:

```
config/
├── config.template.yaml   # Documented template
├── dev.yaml
├── staging.yaml
└── prod.yaml
```

See `config/config.template.yaml` for available settings and their descriptions.
