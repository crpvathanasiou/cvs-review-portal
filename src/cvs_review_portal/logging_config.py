"""Standard-library logging configuration for the `cvs_review_portal` namespace."""

import logging
import sys
import time

from cvs_review_portal.settings import LogLevel

_LOGGER_NAME = "cvs_review_portal"
_HANDLER_NAME = "cvs_review_portal_stream"
_LOG_FORMAT = "timestamp=%(asctime)s level=%(levelname)s logger=%(name)s message=%(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging(log_level: LogLevel) -> None:
    """Configure the `cvs_review_portal` logger idempotently.

    Repeated calls update the level but never add a duplicate handler, so
    repeated application-factory calls (e.g. in tests) are safe. The root
    logger is never touched.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(log_level)
    logger.propagate = False

    if any(handler.name == _HANDLER_NAME for handler in logger.handlers):
        return

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    formatter.converter = time.gmtime
    handler = logging.StreamHandler(sys.stdout)
    handler.name = _HANDLER_NAME
    handler.setFormatter(formatter)
    logger.addHandler(handler)
