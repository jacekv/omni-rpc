import logging
import logging.config
from typing import Any

from omni_rpc.adapters.outbound.python_logger import PythonLogger
from omni_rpc.domain.ports.logger import Logger


def get_log_config(formatter: str, handler: str, levels: dict) -> dict[str, Any]:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.json.JsonFormatter",
                "fmt": (
                    "%(asctime)s %(levelname)s %(name)s "
                    "%(message)s %(module)s %(funcName)s "
                    "%(lineno)d %(process)d"
                ),
                "timestamp": "datetime",
            },
            "standard": {
                "format": ("%(asctime)s [%(levelname)s] " "%(name)s: %(message)s"),
            },
            "simple": {
                "format": "[%(levelname)s] %(message)s",
            },
        },
        "handlers": {
            "stdout": {
                "level": "NOTSET",
                "class": "logging.StreamHandler",
                "formatter": formatter,
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "handlers": [handler],
            "level": levels.get("root", "WARNING"),
        },
        "loggers": {
            "omni_rpc": {
                "handlers": [handler],
                "level": levels.get("omni_rpc", "INFO"),
                "propagate": False,
            },
            "uvicorn": {
                "handlers": [handler],
                "level": levels.get("uvicorn", "INFO"),
                "propagate": False,
            },
        },
    }


def configure_logging(formatter: str, handler: str, levels: dict) -> None:
    config = get_log_config(formatter, handler, levels)
    logging.config.dictConfig(config)


class LoggerFactory:
    def get_logger(self, name: str) -> Logger:
        return PythonLogger(name)
