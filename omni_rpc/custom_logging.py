import logging
import uuid

from pythonjsonlogger import jsonlogger

trace_id = None


def get_trace_id():
    return uuid.uuid4()


class ContextFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = trace_id
        return True


LOG_LEVEL = logging.DEBUG
LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s %(trace_id)s"

logging.root.setLevel(LOG_LEVEL)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(LOG_FORMAT)
logHandler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
logger.addFilter(ContextFilter())
logger.addHandler(logHandler)
