import logging
import uuid

from pythonjsonlogger import jsonlogger


def get_trace_id():
    return uuid.uuid4()


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(
            log_record, record, message_dict
        )  # noqa: E501
        log_record["dd.trace_id"] = str(get_trace_id())


LOG_LEVEL = logging.DEBUG
LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s %(dd.trace_id)s"

logging.root.setLevel(LOG_LEVEL)
logHandler = logging.StreamHandler()
formatter = CustomJsonFormatter(LOG_FORMAT)
logHandler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
logger.addHandler(logHandler)
