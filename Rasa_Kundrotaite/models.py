from pydantic import BaseModel


class Obligation(BaseModel):
    actor: str
    action: str
    modality: str
    condition: str
    span: str
    rationale: str


class ObligationList(BaseModel):
    obligations: list[Obligation]
