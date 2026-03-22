from app.schemas.common import ORMModel


class HealthResponse(ORMModel):
    service: str
    version: str
    environment: str
