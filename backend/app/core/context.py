from contextvars import ContextVar

# Set by app.main's request middleware and by Celery task wrappers (Phase 4+) so every
# log line can be tied back to the request or task that produced it.
current_request_id: ContextVar[str | None] = ContextVar("current_request_id", default=None)
current_task_id: ContextVar[str | None] = ContextVar("current_task_id", default=None)
