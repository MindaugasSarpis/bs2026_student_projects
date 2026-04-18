"""Celery tasks for the collection layer."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from repops.models import Post, PostStatus, PostType, Profile, Target
from repops.collector.apify_scraper import ApifyScraper
from repops.collector.types import ScrapedPost
from repops.db import get_session
from repops.observability.logging import get_logger
from repops.observability.metrics import collection_errors_total, posts_collected_total

logger = get_logger(__name__)


@shared_task(
    name="repops.collector.tasks.collect_all_active_targets",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def collect_all_active_targets(self: object) -> dict:  # type: ignore[type-arg]
    """Scheduled task: fan-out a collection job per active target."""
    with get_session() as session:
        targets = session.scalars(
            select(Target).where(Target.is_active.is_(True))
        ).all()

    logger.info("collection_fanout", target_count=len(targets))

    for target in targets:
        collect_target.apply_async(
            args=[str(target.id)],
            queue="collection",
        )

    return {"targets_queued": len(targets)}


@shared_task(
    name="repops.collector.tasks.collect_target",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def collect_target(self: object, target_id: str) -> dict:  # type: ignore[type-arg]
    """Collect posts from one target and enqueue them for analysis."""
    target_uuid = uuid.UUID(target_id)

    with get_session() as session:
        target = session.get(Target, target_uuid)
        if not target:
            logger.warning("collect_target_not_found", target_id=target_id)
            return {"error": "target not found"}

        fb_id = target.facebook_id
        logger.info("collect_target_start", target_id=target_id, fb_id=fb_id)

        try:
            scraped = asyncio.run(_scrape(fb_id))
        except Exception as exc:
            collection_errors_total.labels(
                target_id=target_id, error_type=type(exc).__name__
            ).inc()
            logger.error("collect_target_error", target_id=target_id, error=str(exc))
            raise

        new_count = _persist_posts(session, scraped, target)
        session.commit()

    logger.info(
        "collect_target_done",
        target_id=target_id,
        scraped=len(scraped),
        new=new_count,
    )

    # Enqueue analysis for each new post
    for post in scraped[:new_count]:
        from repops.analyzer.tasks import analyze_post
        analyze_post.apply_async(
            kwargs={"facebook_id": post.facebook_id},
            queue="analysis",
        )

    return {"scraped": len(scraped), "new": new_count}


async def _scrape(fb_page_id: str) -> list[ScrapedPost]:
    from repops.settings import settings
    async with ApifyScraper() as scraper:
        return await scraper.scrape_page(fb_page_id, max_posts=settings.scraper_max_posts, max_comments=settings.scraper_max_comments)


def _persist_posts(
    session: Session, scraped: list[ScrapedPost], target: Target
) -> int:
    """Insert posts that don't already exist. Returns the count of new posts."""
    new_count = 0

    for sp in scraped:
        existing = session.scalar(
            select(Post).where(Post.facebook_id == sp.facebook_id)
        )
        if existing:
            continue

        # Upsert author profile
        author: Profile | None = None
        if sp.author_facebook_id:
            author = session.scalar(
                select(Profile).where(Profile.facebook_id == sp.author_facebook_id)
            )
            if not author:
                author = Profile(
                    facebook_id=sp.author_facebook_id,
                    name=sp.author_name,
                )
                session.add(author)
                session.flush()
            elif sp.author_name and not author.name:
                author.name = sp.author_name

        post = Post(
            facebook_id=sp.facebook_id,
            target_id=target.id,
            author_id=author.id if author else None,
            content=sp.content,
            url=sp.url,
            post_type=PostType(sp.post_type),
            language=None,  # will be detected during analysis
            posted_at=sp.posted_at or datetime.now(tz=timezone.utc),
            reaction_count=sp.reaction_count,
            share_count=sp.share_count,
            comment_count=sp.comment_count,
            status=PostStatus.RAW,
        )
        session.add(post)
        new_count += 1

        posts_collected_total.labels(
            target_id=str(target.id), post_type=sp.post_type
        ).inc()

    return new_count
