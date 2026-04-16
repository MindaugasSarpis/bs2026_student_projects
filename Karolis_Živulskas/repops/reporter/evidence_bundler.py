"""Package evidence (post content + screenshot) and archive to S3."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from repops.observability.logging import get_logger
from repops.settings import settings

logger = get_logger(__name__)


def _s3_client() -> object:
    kwargs: dict = {"region_name": settings.aws_region}  # type: ignore[type-arg]
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id.get_secret_value()
    if settings.aws_secret_access_key:
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key.get_secret_value()
    return boto3.client("s3", **kwargs)


def upload_screenshot(
    screenshot_bytes: bytes,
    post_facebook_id: str,
) -> str | None:
    """Upload a screenshot PNG to S3 and return the object key."""
    if not screenshot_bytes:
        return None

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y/%m/%d")
    key = f"screenshots/{timestamp}/{post_facebook_id}.png"

    try:
        s3 = _s3_client()
        s3.put_object(  # type: ignore[union-attr]
            Bucket=settings.s3_evidence_bucket,
            Key=key,
            Body=screenshot_bytes,
            ContentType="image/png",
        )
        logger.info("screenshot_uploaded", key=key, size=len(screenshot_bytes))
        return key
    except (BotoCoreError, ClientError) as exc:
        logger.error("screenshot_upload_failed", post_id=post_facebook_id, error=str(exc))
        return None


def bundle_evidence(
    post_data: dict,  # type: ignore[type-arg]
    analysis_data: dict,  # type: ignore[type-arg]
    screenshot_key: str | None,
) -> str | None:
    """Create a JSON evidence bundle and upload to S3. Returns the S3 key."""
    bundle = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "post": post_data,
        "analysis": analysis_data,
        "screenshot_s3_key": screenshot_key,
    }
    payload = json.dumps(bundle, ensure_ascii=False, indent=2).encode("utf-8")

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y/%m/%d")
    post_id = post_data.get("facebook_id", "unknown")
    key = f"evidence/{timestamp}/{post_id}.json"

    try:
        s3 = _s3_client()
        s3.put_object(  # type: ignore[union-attr]
            Bucket=settings.s3_evidence_bucket,
            Key=key,
            Body=payload,
            ContentType="application/json",
        )
        logger.info("evidence_bundle_uploaded", key=key)
        return key
    except (BotoCoreError, ClientError) as exc:
        logger.error("evidence_bundle_upload_failed", post_id=post_id, error=str(exc))
        return None


def generate_presigned_url(key: str, expiry_seconds: int = 3600) -> str | None:
    """Generate a time-limited pre-signed URL for an evidence object."""
    try:
        s3 = _s3_client()
        url: str = s3.generate_presigned_url(  # type: ignore[union-attr]
            "get_object",
            Params={"Bucket": settings.s3_evidence_bucket, "Key": key},
            ExpiresIn=expiry_seconds,
        )
        return url
    except (BotoCoreError, ClientError) as exc:
        logger.error("presigned_url_failed", key=key, error=str(exc))
        return None
