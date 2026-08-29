import redis.asyncio as redis

from app.core.config import get_settings

settings = get_settings()

# One client, reused everywhere. redis-py pools connections internally, so this is
# safe to import and use from any request handler without extra setup.
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
