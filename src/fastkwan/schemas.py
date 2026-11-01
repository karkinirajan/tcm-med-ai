from pydantic import BaseModel, Field


class Query(BaseModel):
    query: str = Field(min_length=1, max_length=4000)


class SyndromeResponse(BaseModel):
    result: str


class LifestyleResponse(BaseModel):
    病名: str
    预防与调摄: str | None = None


class RankedItem(BaseModel):
    text: str
    index: int
    relevance_score: float


class PrescriptionResponse(BaseModel):
    results: list[RankedItem]
    message: str | None = None
