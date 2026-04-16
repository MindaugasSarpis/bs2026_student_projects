"""Celery tasks for the reporter layer."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select

from repops.db import get_session
from repops.models import Post, Report, ReportOutcome, ReportStatus
from repops.reporter import evidence_bundler, meta_reporter, alert_router
from repops.observability.logging import get_logger
from repops.observability.metrics import reports_pending_gauge, reports_submitted_total

logger = get_logger(__name__)


@shared_task(
    name="repops.reporter.tasks.submit_report",
    bind=True,
    max_retries=5,
    default_retry_delay=300,  # retry every 5 min
)
def submit_report(self: object, post_id: str) -> dict:  # type: ignore[type-arg]
    """Bundle evidence and submit a report to Meta for a single post."""
    post_uuid = uuid.UUID(post_id)

    with get_session() as session:
        post = session.get(Post, post_uuid)
        if not post:
            logger.warning("submit_report_post_not_found", post_id=post_id)
            return {"error": "post not found"}

        # Check if a pending/submitted report already exists
        existing = session.scalar(
            select(Report).where(
                Report.post_id == post_uuid,
                Report.status.in_([ReportStatus.QUEUED, ReportStatus.SUBMITTED]),
            )
        )
        if existing:
            logger.info("report_already_exists", post_id=post_id)
            return {"skipped": True}

        # Create report record
        report = Report(
            post_id=post_uuid,
            status=ReportStatus.SUBMITTING,
            report_category=_determine_category(post),
        )
        session.add(report)
        session.flush()
        report_id = report.id

        # Bundle evidence → S3
        post_data = {"facebook_id": post.facebook_id, "url": post.url, "content": post.content}
        analysis = post.analysis_results[0] if post.analysis_results else {}
        analysis_data = (
            {
                "overall_score": analysis.overall_score,
                "overall_label": analysis.overall_label,
                "matched_keywords": analysis.matched_keywords,
            }
            if analysis
            else {}
        )
        evidence_key = evidence_bundler.bundle_evidence(post_data, analysis_data, post.screenshot_s3_key)
        report.evidence_s3_key = evidence_key
        session.commit()

    # Submit to Meta (Playwright — outside the DB session)
    result = asyncio.run(
        meta_reporter.submit_report(
            post_url=post.url,
            category=report.report_category,  # type: ignore[union-attr]
        )
    )

    with get_session() as session:
        report = session.get(Report, report_id)
        if not report:
            return {"error": "report record missing"}

        if result.success:
            report.status = ReportStatus.SUBMITTED
            report.submitted_at = datetime.now(tz=timezone.utc)
            reports_submitted_total.labels(outcome="success").inc()
            logger.info("report_submitted_ok", post_id=post_id)
        else:
            report.status = ReportStatus.FAILED
            report.retry_count += 1
            report.error_message = result.error
            reports_submitted_total.labels(outcome="failed").inc()
            logger.warning("report_submission_failed", post_id=post_id, error=result.error)

        session.commit()

    # Send Slack/email alert
    if result.success and post.analysis_results:
        ar = post.analysis_results[0]
        asyncio.run(
            alert_router.send_slack_alert(
                post_url=post.url,
                score=ar.overall_score,
                label=ar.overall_label,
                matched_keywords=ar.matched_keywords or [],
            )
        )

    if not result.success:
        raise self.retry(exc=RuntimeError(result.error or "submission failed"))  # type: ignore[union-attr]

    return {"success": True}


@shared_task(
    name="repops.reporter.tasks.flush_report_queue",
    bind=True,
)
def flush_report_queue(self: object) -> dict:  # type: ignore[type-arg]
    """Pick up QUEUED reports and submit them."""
    with get_session() as session:
        queued = session.scalars(
            select(Report)
            .where(Report.status == ReportStatus.QUEUED)
            .limit(20)
        ).all()

    reports_pending_gauge.set(len(queued))

    for report in queued:
        submit_report.apply_async(
            kwargs={"post_id": str(report.post_id)},
            queue="reporting",
        )

    logger.info("flushed_report_queue", count=len(queued))
    return {"flushed": len(queued)}


def _determine_category(post: Post) -> str:
    """Heuristically choose the best Meta report category for a post."""
    if not post.analysis_results:
        return "hate_speech"
    ar = post.analysis_results[0]
    if ar.overall_label == "hate_speech":
        return "hate_speech"
    if ar.overall_label == "disinformation":
        return "false_information"
    return "hate_speech"
