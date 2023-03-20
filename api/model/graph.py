from pydantic import BaseModel, Field


class GraphHistogramBin(BaseModel):
    height: float = Field(..., description='The height of the bin.')
    x0: float = Field(..., description='The left-most coordinate of the bin.')
    x1: float = Field(..., description='The right-most coordinate of the bin.')
