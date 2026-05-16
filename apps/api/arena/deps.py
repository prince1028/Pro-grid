"""FastAPI dependency providers."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from arena.core.db import SessionLocal
from arena.core.redis import RedisLike, get_redis


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as s:
        yield s


def redis_dep() -> RedisLike:
    return get_redis()


SessionDep = Depends(get_session)
RedisDep = Depends(redis_dep)
