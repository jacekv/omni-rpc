import logging

from colorlog import ColoredFormatter

LOG_LEVEL = logging.DEBUG
# fmt: off
LOGFORMAT = (
    "%(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s"
)
# fmt: on

logging.root.setLevel(LOG_LEVEL)
formatter = ColoredFormatter(LOGFORMAT)
stream = logging.StreamHandler()
stream.setLevel(LOG_LEVEL)
stream.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
logger.addHandler(stream)
