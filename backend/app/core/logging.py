import logging
import sys

from app.core.config import get_settings

settings = get_settings()


class RequestContextFilter(logging.Filter):
    """Injects request_id / task_id from contextvars into every record so the format
    string below never breaks for log calls made outside a request or task (startup,
    one-off scripts) -- those just show '-'."""

    def filter(self, record: logging.LogRecord) -> bool:
        from app.core.context import current_request_id, current_task_id

        record.request_id = current_request_id.get() or "-"
        record.task_id = current_task_id.get() or "-"
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [req=%(request_id)s task=%(task_id)s] %(name)s: %(message)s"
        )
    )
    handler.addFilter(RequestContextFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO if settings.DEBUG else logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
