import json
from datetime import timedelta

import redis
from sqlalchemy import func, select

from .models import Run, now


class StatsCache:
    def __init__(self, settings, client=None):
        self.settings = settings
        self.client = client or redis.Redis.from_url(
            settings.cache_url, socket_connect_timeout=0.5, socket_timeout=0.5
        )
        self.hits = self.misses = self.fallbacks = 0

    def key(self, repo, days):
        return f"{self.settings.deployment_id}:stats:{repo.owner_id}:{repo.id}:{days}:v{repo.stats_version}"

    def stats(self, db, repo, days=30, enabled=True):
        db.refresh(
            repo, ["stats_version"]
        )  # A post-commit version never reads an old cache key.
        key = self.key(repo, days)
        if enabled:
            try:
                cached = self.client.get(key)
                if cached:
                    self.hits += 1
                    return {**json.loads(cached), "cacheSource": "hit"}
            except (redis.RedisError, ValueError):
                self.fallbacks += 1
        self.misses += 1
        rows = db.execute(
            select(Run.analysis_status, func.count())
            .where(
                Run.repository_id == repo.id,
                Run.github_created_at >= now() - timedelta(days=days),
            )
            .group_by(Run.analysis_status)
        ).all()
        result = {
            "counts": dict(rows),
            "total": sum(n for _, n in rows),
            "asOf": now().isoformat(),
            "days": days,
            "version": repo.stats_version,
            "cacheSource": "miss",
        }
        if enabled:
            try:
                self.client.setex(key, self.settings.cache_ttl, json.dumps(result))
            except redis.RedisError:
                result["cacheSource"] = "database_fallback"
        return result

    def invalidate(self, repo, old_version):
        try:
            current = repo.stats_version
            repo.stats_version = old_version
            key = self.key(repo, 30)
            repo.stats_version = current
            self.client.delete(key)
        except redis.RedisError:
            pass  # DB version in every key is the correctness boundary, not deletion.
