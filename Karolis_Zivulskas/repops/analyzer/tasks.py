"""Celery tasks for the analysis pipeline."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select

from repops.db import get_session
from repops.models import (
    AnalysisLabel,
    AnalysisResult,
    KeywordEntry,
    Post,
    PostStatus,
    Profile,
)
from repops.analyzer import keyword_matcher
from repops.analyzer.profile_scorer import recalculate_profile
from repops.observability.logging import get_logger
from repops.observability.metrics import (
    analysis_duration_seconds,
    analysis_score_histogram,
    keyword_hits_by_pattern,
    keyword_matches_total,
    posts_analyzed_total,
    posts_flagged_total,
)
from repops.settings import settings

logger = get_logger(__name__)

# Keyword severity → risk score
_SEVERITY_SCORE: dict[int, float] = {
    1: 0.35,   # low
    2: 0.65,   # medium
    3: 0.95,   # high
}


@shared_task(
    name="repops.analyzer.tasks.analyze_post",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def analyze_post(self: object, facebook_id: str) -> dict:  # type: ignore[type-arg]
    """Keyword analysis pipeline for a single post."""
    with get_session() as session:
        post = session.scalar(select(Post).where(Post.facebook_id == facebook_id))
        if not post:
            logger.warning("analyze_post_not_found", facebook_id=facebook_id)
            return {"error": "post not found"}

        if post.status != PostStatus.RAW:
            return {"skipped": True, "status": post.status}

        logger.info("analyze_post_start", post_id=str(post.id), facebook_id=facebook_id)
        t0 = time.monotonic()

        # Load all active keyword patterns
        keyword_entries = session.scalars(
            select(KeywordEntry).where(KeywordEntry.keyword_set.has(is_active=True))
        ).all()
        plain_patterns = [(e.pattern, e.severity) for e in keyword_entries if not e.is_regex]
        regex_patterns = [(e.pattern, e.severity) for e in keyword_entries if e.is_regex]

        automaton = keyword_matcher.build_automaton(plain_patterns)
        kw_matches = keyword_matcher.match_text(post.content, automaton)
        if regex_patterns:
            kw_matches += keyword_matcher.match_text_regex(post.content, regex_patterns)

        matched_kws = list({m.pattern for m in kw_matches})  # deduplicate

        # Stamp last_matched_at on every entry that fired
        if matched_kws:
            entry_by_pattern = {e.pattern: e for e in keyword_entries}
            now = datetime.now(timezone.utc)
            for pattern in matched_kws:
                entry = entry_by_pattern.get(pattern)
                if entry:
                    entry.last_matched_at = now
        kw_severity = keyword_matcher.top_severity(kw_matches)

        # Score and label
        overall_score = _SEVERITY_SCORE.get(kw_severity, 0.0)
        if kw_severity == 3:
            overall_label = AnalysisLabel.HATE_SPEECH
        elif kw_severity in (1, 2):
            overall_label = AnalysisLabel.KEYWORD_MATCH
        else:
            overall_label = AnalysisLabel.CLEAN

        result = AnalysisResult(
            post_id=post.id,
            matched_keywords=matched_kws,
            keyword_severity=kw_severity,
            overall_label=overall_label,
            overall_score=overall_score,
        )
        session.add(result)

        if overall_score >= settings.hate_speech_threshold:
            post.status = PostStatus.FLAGGED
        else:
            post.status = PostStatus.ANALYZED

        session.commit()

        duration = time.monotonic() - t0
        analysis_duration_seconds.observe(duration)
        analysis_score_histogram.observe(overall_score)
        posts_analyzed_total.labels(language="unknown").inc()
        if matched_kws:
            keyword_matches_total.labels(keyword_set="active").inc()
            severity_label = {1: "low", 2: "medium", 3: "high"}.get(kw_severity, "low")
            for kw in matched_kws:
                keyword_hits_by_pattern.labels(pattern=kw, severity=severity_label).inc()
        if post.status == PostStatus.FLAGGED:
            severity_label = {1: "low", 2: "medium", 3: "high"}.get(kw_severity, "low")
            posts_flagged_total.labels(severity=severity_label).inc()

        logger.info(
            "analyze_post_done",
            post_id=str(post.id),
            score=overall_score,
            label=overall_label,
            keywords_matched=len(matched_kws),
            duration_ms=round(duration * 1000),
        )

    # Recalculate profile risk score if post has an author
    if post.author_id:
        recalculate_profile_task.apply_async(
            kwargs={"profile_id": str(post.author_id)},
            queue="analysis",
        )

    return {"label": overall_label, "score": overall_score, "keywords": matched_kws}


@shared_task(name="repops.analyzer.tasks.requeue_raw_posts", bind=True)
def requeue_raw_posts(self: object) -> dict:  # type: ignore[type-arg]
    """Safety net: re-queue any RAW posts that haven't been analyzed yet."""
    with get_session() as session:
        raw_posts = session.scalars(
            select(Post).where(Post.status == PostStatus.RAW).limit(500)
        ).all()

    for post in raw_posts:
        analyze_post.apply_async(
            kwargs={"facebook_id": post.facebook_id},
            queue="analysis",
        )

    logger.info("requeued_raw_posts", count=len(raw_posts))
    return {"requeued": len(raw_posts)}


@shared_task(name="repops.analyzer.tasks.recalculate_all_profile_scores", bind=True)
def recalculate_all_profile_scores(self: object) -> dict:  # type: ignore[type-arg]
    """Hourly: recompute risk scores for all monitored profiles."""
    with get_session() as session:
        profiles = session.scalars(select(Profile)).all()

    for profile in profiles:
        recalculate_profile_task.apply_async(
            kwargs={"profile_id": str(profile.id)},
            queue="analysis",
        )

    return {"profiles_queued": len(profiles)}


@shared_task(name="repops.analyzer.tasks.recalculate_profile_task", bind=True)
def recalculate_profile_task(self: object, profile_id: str) -> float:
    return recalculate_profile(uuid.UUID(profile_id))
