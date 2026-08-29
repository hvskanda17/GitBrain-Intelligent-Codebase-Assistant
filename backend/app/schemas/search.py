from pydantic import BaseModel, Field


class SemanticSearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=40, ge=1, le=200)
    token_budget: int = Field(default=8000, ge=500, le=32000)


class RetrievedChunkRead(BaseModel):
    source_type: str
    source_id: str
    label: str
    file_path: str
    chunk_text: str


class SemanticSearchResponse(BaseModel):
    chunks: list[RetrievedChunkRead]
