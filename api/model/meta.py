from pydantic import BaseModel, Field


class MetaVersionResponse(BaseModel):
    major: int = Field(...)
    minor: int = Field(...)
    patch: int = Field(...)
