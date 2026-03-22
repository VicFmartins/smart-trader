from app.schemas.common import ORMModel


class AccountRead(ORMModel):
    id: int
    client_id: int
    broker: str
