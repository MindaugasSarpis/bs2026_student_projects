"""Route alerts (Slack, email) when content is flagged or reported."""

from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

import httpx

from repops.observability.logging import get_logger
from repops.settings import settings

logger = get_logger(__name__)


async def send_slack_alert(
    post_url: str,
    score: float,
    label: str,
    matched_keywords: list[str],
) -> None:
    """Post a notification to the configured Slack webhook."""
    if not settings.slack_webhook_url:
        return

    severity_emoji = "🔴" if score >= 0.9 else "🟠" if score >= 0.7 else "🟡"
    kw_text = ", ".join(f"`{k}`" for k in matched_keywords[:5]) or "—"

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{severity_emoji} RepOps Alert"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Label:* {label}"},
                    {"type": "mrkdwn", "text": f"*Score:* {score:.2f}"},
                    {"type": "mrkdwn", "text": f"*Keywords:* {kw_text}"},
                    {"type": "mrkdwn", "text": f"*Post:* <{post_url}|View>"},
                ],
            },
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.slack_webhook_url.get_secret_value(),
                json=payload,
            )
            response.raise_for_status()
        logger.info("slack_alert_sent", post_url=post_url, score=score)
    except Exception as exc:
        logger.error("slack_alert_failed", error=str(exc))


def send_email_alert(
    post_url: str,
    score: float,
    label: str,
) -> None:
    """Send an alert email via SMTP (synchronous, for Celery tasks)."""
    if not settings.alert_email:
        return

    subject = f"[RepOps] {label.upper()} detected — score {score:.2f}"
    body = (
        f"A post has been flagged by RepOps.\n\n"
        f"Label:  {label}\n"
        f"Score:  {score:.2f}\n"
        f"URL:    {post_url}\n\n"
        f"Log in to the RepOps dashboard to review and action."
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "repops@localhost"
    msg["To"] = settings.alert_email

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.sendmail("repops@localhost", [settings.alert_email], msg.as_string())
        logger.info("email_alert_sent", recipient=settings.alert_email)
    except Exception as exc:
        logger.error("email_alert_failed", error=str(exc))
