from pydantic import BaseModel, Field


class StatusDbResponse(BaseModel):
    timeMs: float = Field(...)
    online: bool = Field(...)
