import json
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Action(str, Enum):
	REFUND = "REFUND"
	REPLACE = "REPLACE"
	RETURN = "RETURN"
	REQUEST_PHOTOS = "REQUEST_PHOTOS"
	REQUEST_MORE_INFORMATION = "REQUEST_MORE_INFORMATION"
	DENY = "DENY"
	NEEDS_MORE_INFORMATION = "NEEDS_MORE_INFORMATION"


class UserCreate(BaseModel):
	email: EmailStr
	password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
	model_config = ConfigDict(from_attributes=True)
	id: int
	email: EmailStr
	created_at: datetime


class Token(BaseModel):
	access_token: str
	token_type: str = "bearer"


class TicketCreate(BaseModel):
	subject: str = Field(min_length=3, max_length=200)
	description: str = Field(min_length=10, max_length=10000)


class DecisionRead(BaseModel):
	model_config = ConfigDict(from_attributes=True)
	action: Action
	confidence: float = Field(ge=0, le=1)
	reason: str
	sources: list[str]

	@field_validator("sources", mode="before")
	@classmethod
	def parse_sources(cls, value: str | list[str]) -> list[str]:
		return json.loads(value) if isinstance(value, str) else value


class TicketRead(BaseModel):
	model_config = ConfigDict(from_attributes=True)
	id: int
	subject: str
	description: str
	created_at: datetime
	decision: DecisionRead | None = None
