import uvicorn

from omni_rpc.config.settings import parse_and_load_environment_settings


def main() -> None:
    settings = parse_and_load_environment_settings()
    settings.configure_logging()
    uvicorn.run(
        "omni_rpc._app:app",
        host=settings.host,
        port=settings.port,
        log_config=settings.log_config,
        access_log=settings.access_log,
        workers=settings.workers,
        reload=settings.reload,
    )


if __name__ == "__main__":
    main()
