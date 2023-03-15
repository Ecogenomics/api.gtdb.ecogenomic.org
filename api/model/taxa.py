from typing import List

from pydantic import BaseModel, Field


class TaxaAll(BaseModel):
    taxa: List[str] = Field(..., description='all taxa in the current release')
