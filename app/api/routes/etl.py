from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import APIResponse
from app.schemas.etl import ETLRunFromS3Request, ETLRunRequest, ETLRunResponse
from app.services.import_pipeline import ImportPipelineService


router = APIRouter()


@router.post("/run", response_model=APIResponse[ETLRunResponse])
def run_etl(
    payload: ETLRunRequest | None = None,
    db: Session = Depends(get_db),
) -> APIResponse[ETLRunResponse]:
    request = payload or ETLRunRequest()
    return APIResponse(data=ImportPipelineService(db).run(source_path=request.source_path))


@router.post("/run-from-s3", response_model=APIResponse[ETLRunResponse])
def run_etl_from_s3(
    payload: ETLRunFromS3Request | None = None,
    db: Session = Depends(get_db),
) -> APIResponse[ETLRunResponse]:
    request = payload or ETLRunFromS3Request()
    return APIResponse(data=ImportPipelineService(db).run_from_s3(s3_key=request.s3_key, s3_prefix=request.s3_prefix))
