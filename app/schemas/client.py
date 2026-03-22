from app.schemas.common import ORMModel


class ClientRead(ORMModel):
    id: int
    name: str
    risk_profile: str
