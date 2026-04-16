"""Endpoints for viewing and managing Meta reports."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from repops.api.dependencies import get_db
from repops.models import Report, ReportOutcome, ReportStatus
from repops.reporter.tasks import submit_report as submit_report_task

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]


class ReportResponse(BaseModel):
    id: uuid.UUID
    post_id: uuid.UUID
    status: ReportStatus
    outcome: ReportOutcome
    report_category: str
    evidence_s3_key: str | None
    meta_reference_id: str | None
    retry_count: int
    error_message: str | None
    submitted_by: str

    model_config = {"from_attributes": True}


class OutcomeUpdate(BaseModel):
    outcome: ReportOutcome
    meta_reference_id: str | None = None


@router.get("/", response_model=list[ReportResponse])
def list_reports(
    db: DB,
    status: ReportStatus | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> list[Report]:
    q = select(Report).order_by(Report.created_at.desc()).offset(offset).limit(limit)
    if status:
        q = q.where(Report.status == status)
    return list(db.scalars(q).all())


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: uuid.UUID, db: DB) -> Report:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/{report_id}/retry", response_model=dict)  # type: ignore[type-arg]
def retry_report(report_id: uuid.UUID, db: DB) -> dict:  # type: ignore[type-arg]
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status not in (ReportStatus.FAILED, ReportStatus.QUEUED):
        raise HTTPException(status_code=400, detail="Only FAILED or QUEUED reports can be retried")

    report.status = ReportStatus.QUEUED
    report.error_message = None
    db.commit()

    submit_report_task.apply_async(
        kwargs={"post_id": str(report.post_id)},
        queue="reporting",
    )
    return {"queued": True}


@router.patch("/{report_id}/outcome", response_model=ReportResponse)
def update_outcome(report_id: uuid.UUID, body: OutcomeUpdate, db: DB) -> Report:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.outcome = body.outcome
    if body.meta_reference_id:
        report.meta_reference_id = body.meta_reference_id
    db.commit()
    db.refresh(report)
    return report
