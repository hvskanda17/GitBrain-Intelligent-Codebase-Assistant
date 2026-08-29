from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("gitbrain", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    # A worker that dies mid-clone shouldn't lose the task -- ack only after it
    # completes, and never prefetch a second task onto a worker that hasn't
    # finished (and thus acked) its current one. The standard combo for
    # long-running, retry-sensitive tasks.
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "workers.tasks.ingestion.*": {"queue": "ingestion"},
        "workers.tasks.parsing.*": {"queue": "ingestion"},
        "workers.tasks.graph.*": {"queue": "ingestion"},
        "workers.tasks.embeddings.*": {"queue": "ingestion"},
    },
)

# Explicit imports rather than autodiscover_tasks(["workers.tasks"]): that call
# looks for a "workers.tasks.tasks" module (Django's one-tasks.py-per-app
# convention, which is what autodiscover_tasks was built around), but this
# project's task code is split across workers/tasks/ingestion.py,
# workers/tasks/parsing.py, workers/tasks/graph.py, and workers/tasks/embeddings.py
# -- autodiscover would silently find none of them, and a worker that never
# imports a task module never registers it, so it would reject incoming messages
# for that task as unrecognized. Importing directly here, *after* celery_app is
# defined, sidesteps needing autodiscover's package/module resolution to be right:
# workers.tasks.ingestion does `from workers.celery_app import celery_app`, and by
# the time that runs, this module is already in sys.modules with celery_app set,
# so the circular import resolves cleanly.
from workers.tasks import embeddings, graph, ingestion, parsing  # noqa: E402,F401
