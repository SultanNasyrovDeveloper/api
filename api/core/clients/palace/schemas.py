from datetime import datetime

from pydantic import BaseModel


class PalaceNode(BaseModel):
    id: str
    difficulty: float
    cpr: int
    repetitions: int
    last_interval: int
    last_repetition: datetime
