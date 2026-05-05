from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CopilotAppContext(BaseModel):
  current_zone_id: int | None = Field(default=None)
  current_zone_name: str | None = Field(default=None)
  latitude: float | None = Field(default=None)
  longitude: float | None = Field(default=None)
  location_label: str | None = Field(default=None)
  day_of_week: int | None = Field(default=None, ge=0, le=6)
  hour: int | None = Field(default=None, ge=0, le=23)
  use_custom_time: bool = Field(default=False)


class CopilotParameters(BaseModel):
  current_zone_query: str | None = Field(default=None)
  current_zone_id: int | None = Field(default=None)
  current_zone_name: str | None = Field(default=None)
  day_of_week: int | None = Field(default=None, ge=0, le=6)
  hour: int | None = Field(default=None, ge=0, le=23)
  use_current_location: bool = Field(default=False)
  use_current_time: bool = Field(default=True)
  latitude: float | None = Field(default=None)
  longitude: float | None = Field(default=None)
  confirmation_options: list[str] = Field(default_factory=list)
  scenario_label: str | None = Field(default=None)


class CopilotChatRequest(BaseModel):
  message: str = Field(min_length=1)
  summary: str = Field(default="")
  app_context: CopilotAppContext
  session_parameters: CopilotParameters | None = Field(default=None)


class CopilotChatResponse(BaseModel):
  reply: str
  summary: str
  parameters: CopilotParameters
  results: dict[str, Any] | None = Field(default=None)
  action: Literal["chat", "function"]
  needs_confirmation: bool = Field(default=False)
