from __future__ import annotations

import asyncio
import io
import logging
from functools import partial

from fastapi import APIRouter, File, UploadFile

from app.core.exceptions import UploadTooLargeError
from app.schemas.common import APIResponse
from app.schemas.etl import UploadResponse
from app.services.import_pipeline import ImportPipelineService


logger = logging.getLogger(__name__)
router = APIRouter()
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024


@router.post("/upload", response_model=APIResponse[UploadResponse])
async def upload_portfolio_file(
    file: UploadFile = File(...),
) -> APIResponse[UploadResponse]:
    try:
        file_bytes = await file.read()
        if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
            max_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise UploadTooLargeError(f"Uploaded file exceeds the maximum allowed size of {max_mb} MB.")

        stream = io.BytesIO(file_bytes)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(ImportPipelineService.process_uploaded_stream, file.filename or "", stream),
        )
        logger.info("Completed uploaded file processing for %s", file.filename)
        return APIResponse(data=result)
    finally:
        await file.close()
