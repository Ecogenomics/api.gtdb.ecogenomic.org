from enum import Enum
from typing import Optional

from fastapi import UploadFile
from pydantic import BaseModel, Field


class NoUserAccEnum(Enum):
    IGNORE = 'ignore'
    LONG = 'long'
    SHORT = 'short'
    CANONICAL = 'canonical'


class PrevUserEnum(Enum):
    IGNORE = 'ignore'
    USER = 'user'
    UBA = 'uba'
    LONG = 'long'
    SHORT = 'short'
    CANONICAL = 'canonical'


class UserOnlyEnum(Enum):
    IGNORE = 'ignore'
    USER = 'user'
    UBA = 'uba'


class UtilContactEmailRequest(BaseModel):
    fromEmail: str = Field(...)
    subject: str = Field(...)
    message: str = Field(...)
    clientResponse: str = Field(...)


class UtilConvertTreeAccessionsRequest(BaseModel):
    newickFile: Optional[UploadFile] = Field(None)
    newickString: Optional[str] = Field(None)
    noUserAcc: NoUserAccEnum = Field(...)
    prevUser: PrevUserEnum = Field(...)
    userOnly: UserOnlyEnum = Field(...)
