from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import pagination_params
from app.db.session import get_db
from app.schemas.common import APIResponse, ListAPIResponse, PaginationParams
from app.schemas.ingestion_report import IngestionReportRead, IngestionReportReviewUpdate
from app.schemas.etl import UploadResponse
from app.services.import_pipeline import ImportPipelineService
from app.services.ingestion_reports import IngestionReportService


router = APIRouter(prefix="/ingestion-reports")


@router.get("", response_model=ListAPIResponse[IngestionReportRead])
def list_ingestion_reports(
    db: Session = Depends(get_db),
    pagination: PaginationParams = Depends(pagination_params),
    review_required: Annotated[bool | None, Query(description="Filter by review-required ingestion reports")] = None,
    review_status: Annotated[str | None, Query(description="Filter by review status")] = None,
) -> ListAPIResponse[IngestionReportRead]:
    result = IngestionReportService(db).list_reports(
        pagination=pagination,
        review_required=review_required,
        review_status=review_status,
    )
    return ListAPIResponse(data=result.items, pagination=result.to_pagination_meta())


@router.get("/{report_id}", response_model=APIResponse[IngestionReportRead])
def get_ingestion_report(report_id: int, db: Session = Depends(get_db)) -> APIResponse[IngestionReportRead]:
    report = IngestionReportService(db).get_report(report_id)
    return APIResponse(data=report)


@router.patch("/{report_id}/review", response_model=APIResponse[IngestionReportRead])
def update_ingestion_report_review(
    report_id: int,
    payload: IngestionReportReviewUpdate,
    db: Session = Depends(get_db),
) -> APIResponse[IngestionReportRead]:
    report = IngestionReportService(db).update_review_status(
        report_id,
        review_status=payload.review_status,
        approved_by=payload.approved_by,
    )
    return APIResponse(data=report)


@router.post("/{report_id}/reprocess", response_model=APIResponse[UploadResponse])
def reprocess_ingestion_report(report_id: int, db: Session = Depends(get_db)) -> APIResponse[UploadResponse]:
    result = ImportPipelineService(db).reprocess_report(report_id)
    return APIResponse(data=result)
