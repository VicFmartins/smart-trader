from __future__ import annotations

import asyncio
import io
from functools import partial

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import UploadTooLargeError
from app.db.session import get_db
from app.schemas.common import APIResponse
from app.schemas.pdf_import import PDFImportReviewPayload
from app.services.pdf_import.pipeline import PDFImportReviewService
from app.services.import_jobs import ImportJobService


router = APIRouter(prefix="/imports/pdf")
MAX_PDF_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024


@router.post("/review", response_model=APIResponse[PDFImportReviewPayload])
async def review_pdf_broker_note(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> APIResponse[PDFImportReviewPayload]:
    import_job_service = ImportJobService(db)
    import_job = None
    try:
        file_bytes = await file.read()
        if len(file_bytes) > MAX_PDF_UPLOAD_SIZE_BYTES:
            max_mb = MAX_PDF_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise UploadTooLargeError(f"Uploaded file exceeds the maximum allowed size of {max_mb} MB.")

        import_job = import_job_service.create_pdf_review_job(file_name=file.filename or "")
        stream = io.BytesIO(file_bytes)
        loop = asyncio.get_running_loop()
        payload = await loop.run_in_executor(
            None,
            partial(
                PDFImportReviewService.process_uploaded_stream,
                file.filename or "",
                stream,
                import_job.batch_id,
            ),
        )
        payload.import_job = import_job_service.to_read_model(import_job_service.complete_pdf_review(import_job=import_job, review_payload=payload))
        return APIResponse(data=payload)
    except Exception as exc:
        if import_job is not None:
            import_job_service.fail_pdf_review(import_job=import_job, message=str(exc))
        raise
    finally:
        await file.close()
