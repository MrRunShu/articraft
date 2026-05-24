import json
import logging
from datetime import datetime, time, timedelta
from typing import Optional

from databases import Database

from app.constants.user import UserConstant
from app.schemas.statistics import StatisticsVO
from app.utils.session import redis_client

logger = logging.getLogger(__name__)

STATISTICS_CACHE_KEY = "statistics:overview"
STATISTICS_CACHE_TTL_SECONDS = 3600  # 1小时


class StatisticsService:
    """系统统计服务，聚合多维运营数据，结果缓存 1 小时"""

    def __init__(self, db: Database):
        self.db = db

    async def get_statistics(self) -> StatisticsVO:
        """获取系统统计（优先走 Redis 缓存）"""
        cached = await self._get_cached_statistics()
        if cached is not None:
            logger.info("统计数据命中缓存")
            return cached

        now = datetime.now()
        today_start = datetime.combine(now.date(), time.min)
        week_start = datetime.combine(now.date() - timedelta(days=now.weekday()), time.min)
        month_start = datetime(now.year, now.month, 1)

        today_count = await self._count_articles_by_range(today_start, now)
        week_count = await self._count_articles_by_range(week_start, now)
        month_count = await self._count_articles_by_range(month_start, now)
        total_count = await self._count_total_articles()
        success_rate = await self._calculate_success_rate(total_count)
        avg_duration_ms = await self._calculate_avg_duration()
        active_user_count = await self._count_active_users(week_start, now)
        total_user_count = await self._count_total_users()
        vip_user_count = await self._count_vip_users()
        quota_used = await self._calculate_quota_used()

        stats = StatisticsVO(
            todayCount=today_count,
            weekCount=week_count,
            monthCount=month_count,
            totalCount=total_count,
            successRate=success_rate,
            avgDurationMs=avg_duration_ms,
            activeUserCount=active_user_count,
            totalUserCount=total_user_count,
            vipUserCount=vip_user_count,
            quotaUsed=quota_used,
        )
        await self._set_cached_statistics(stats)
        return stats

    # ─── 各项统计查询 ─────────────────────────────────────────────

    async def _count_articles_by_range(self, start: datetime, end: datetime) -> int:
        value = await self.db.fetch_val(
            query="""
                SELECT COUNT(1) FROM article
                WHERE isDelete = 0 AND createTime >= :s AND createTime <= :e
            """,
            values={"s": start, "e": end},
        )
        return int(value or 0)

    async def _count_total_articles(self) -> int:
        value = await self.db.fetch_val(
            query="SELECT COUNT(1) FROM article WHERE isDelete = 0",
        )
        return int(value or 0)

    async def _calculate_success_rate(self, total_count: int) -> float:
        if total_count <= 0:
            return 0.0
        success_count = await self.db.fetch_val(
            query="SELECT COUNT(1) FROM article WHERE isDelete = 0 AND status = :status",
            values={"status": "COMPLETED"},
        )
        return round((float(success_count or 0) / float(total_count)) * 100, 1)

    async def _calculate_avg_duration(self) -> int:
        """平均创作耗时（毫秒），利用 completedTime - createTime 计算"""
        value = await self.db.fetch_val(
            query="""
                SELECT AVG(TIMESTAMPDIFF(MICROSECOND, createTime, completedTime) / 1000)
                FROM article
                WHERE isDelete = 0 AND status = :status AND completedTime IS NOT NULL
            """,
            values={"status": "COMPLETED"},
        )
        if value is None:
            return 0
        return int(float(value))

    async def _count_active_users(self, start: datetime, end: datetime) -> int:
        """本周有创作记录的去重用户数"""
        value = await self.db.fetch_val(
            query="""
                SELECT COUNT(DISTINCT userId) FROM article
                WHERE isDelete = 0 AND createTime >= :s AND createTime <= :e
            """,
            values={"s": start, "e": end},
        )
        return int(value or 0)

    async def _count_total_users(self) -> int:
        value = await self.db.fetch_val(
            query="SELECT COUNT(1) FROM user WHERE isDelete = 0",
        )
        return int(value or 0)

    async def _count_vip_users(self) -> int:
        value = await self.db.fetch_val(
            query="SELECT COUNT(1) FROM user WHERE isDelete = 0 AND userRole = :role",
            values={"role": UserConstant.VIP_ROLE},
        )
        return int(value or 0)

    async def _calculate_quota_used(self) -> int:
        """普通用户（非VIP/非admin）已创建的文章数 = 已消耗配额数
        注：项目没有 user.quota 字段，用文章数衡量配额消耗"""
        value = await self.db.fetch_val(
            query="""
                SELECT COUNT(1) FROM article a
                JOIN user u ON a.userId = u.id
                WHERE a.isDelete = 0 AND u.isDelete = 0
                AND u.userRole = :role
            """,
            values={"role": UserConstant.DEFAULT_ROLE},
        )
        return int(value or 0)

    # ─── Redis 缓存 ───────────────────────────────────────────────

    async def _get_cached_statistics(self) -> Optional[StatisticsVO]:
        if redis_client is None:
            return None
        try:
            cached = await redis_client.get(STATISTICS_CACHE_KEY)
            if not cached:
                return None
            return StatisticsVO(**json.loads(cached))
        except Exception:
            logger.exception("读取统计缓存失败")
            return None

    async def _set_cached_statistics(self, stats: StatisticsVO):
        if redis_client is None:
            return
        try:
            await redis_client.setex(
                STATISTICS_CACHE_KEY,
                STATISTICS_CACHE_TTL_SECONDS,
                json.dumps(stats.model_dump(by_alias=True), ensure_ascii=False),
            )
            logger.info("统计数据已写入缓存，TTL=%ds", STATISTICS_CACHE_TTL_SECONDS)
        except Exception:
            logger.exception("写入统计缓存失败")
