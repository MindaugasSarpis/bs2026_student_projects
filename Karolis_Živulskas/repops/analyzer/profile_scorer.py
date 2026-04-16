"""Aggregate per-profile risk scoring.

The risk score is a weighted combination of:
  - flag_rate:    fraction of analyzed posts that were flagged
  - severity_avg: average keyword severity across flagged posts
  - volume:       log-normalized number of flagged posts (activity indicator)
"""

from __future__ import annotations

import math

from sqlalchemy import func, select

from repops.db import get_session
from repops.models import AnalysisResult, AnalysisLabel, Post, Profile
from repops.observability.logging import get_logger

logger = get_logger(__name__)


def compute_risk_score(
    total_posts: int,
    flagged_posts: int,
    avg_hate_score: float,
    top_keyword_severity: int,
) -> float:
    """Compute a 0–1 risk score for a profile.

    Weights:
        40% flag rate
        35% average hate speech score on flagged posts
        15% keyword severity signal
        10% volume bonus (more flagged posts = more credible signal)
    """
    if total_posts == 0:
        return 0.0

    flag_rate = flagged_posts / total_posts
    volume_bonus = math.log1p(flagged_posts) / math.log1p(100)  # capped at 100
    severity_signal = (top_keyword_severity / 3.0) if top_keyword_severity else 0.0

    score = (
        0.40 * flag_rate
        + 0.35 * avg_hate_score
        + 0.15 * severity_signal
        + 0.10 * volume_bonus
    )
    return round(min(1.0, score), 4)


def recalculate_profile(profile_id: object) -> float:
    """Recompute and persist the risk score for one profile. Returns new score."""
    with get_session() as session:
        profile = session.get(Profile, profile_id)
        if not profile:
            logger.warning("profile_not_found", profile_id=str(profile_id))
            return 0.0

        # Total posts analyzed for this author
        total = session.scalar(
            select(func.count(Post.id)).where(Post.author_id == profile.id)
        ) or 0

        # Flagged posts
        flagged = session.scalar(
            select(func.count(AnalysisResult.id))
            .join(Post, Post.id == AnalysisResult.post_id)
            .where(
                Post.author_id == profile.id,
                AnalysisResult.overall_label == AnalysisLabel.HATE_SPEECH,
            )
        ) or 0

        # Average score on flagged posts
        avg_score = session.scalar(
            select(func.avg(AnalysisResult.overall_score))
            .join(Post, Post.id == AnalysisResult.post_id)
            .where(
                Post.author_id == profile.id,
                AnalysisResult.overall_label == AnalysisLabel.HATE_SPEECH,
            )
        ) or 0.0

        # Top keyword severity
        top_severity = session.scalar(
            select(func.max(AnalysisResult.keyword_severity))
            .join(Post, Post.id == AnalysisResult.post_id)
            .where(Post.author_id == profile.id)
        ) or 0

        new_score = compute_risk_score(total, flagged, float(avg_score), int(top_severity))

        profile.risk_score = new_score
        profile.total_posts_analyzed = total
        profile.flagged_posts_count = flagged
        session.commit()

        logger.info(
            "profile_score_updated",
            profile_id=str(profile_id),
            score=new_score,
            total=total,
            flagged=flagged,
        )
        return new_score
