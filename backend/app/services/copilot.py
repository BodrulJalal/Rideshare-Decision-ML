from __future__ import annotations

import json
from urllib import error, request

from app.core.config import settings
from app.schemas import CopilotParameters


class CopilotService:
    def __init__(self, zone_service):
        self.zone_service = zone_service

    def chat(self, message: str, summary: str, app_context: dict, session_parameters: dict | None = None) -> dict:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured in the backend environment.")

        session_parameters = session_parameters or {}
        orchestration = self._call_gemini(
            schema=self._orchestration_schema(),
            prompt=self._orchestration_prompt(
                message=message,
                summary=summary,
                app_context=app_context,
                session_parameters=session_parameters,
            ),
        )

        action = str(orchestration.get("action") or "chat")
        parameters = self._merge_with_session_parameters(
            CopilotParameters(**(orchestration.get("parameters") or {})),
            session_parameters,
        )

        if action != "function":
            return {
                "reply": str(orchestration.get("reply") or "Tell me your zone and time, and I can help you decide where to relocate."),
                "summary": str(orchestration.get("summary") or summary or ""),
                "parameters": parameters.model_dump(),
                "results": None,
                "action": "chat",
                "needs_confirmation": bool(orchestration.get("needs_confirmation") or False),
            }

        resolved_parameters, confirmation_reply = self._resolve_parameters(parameters, app_context, message)
        if confirmation_reply is not None:
            return {
                "reply": confirmation_reply,
                "summary": self._merge_summary(summary, message, confirmation_reply),
                "parameters": resolved_parameters.model_dump(),
                "results": None,
                "action": "chat",
                "needs_confirmation": True,
            }

        recommendation = self.zone_service.recommend(
            current_zone=str(resolved_parameters.current_zone_id) if resolved_parameters.current_zone_id is not None else None,
            day_of_week=resolved_parameters.day_of_week,
            hour=resolved_parameters.hour,
            latitude=resolved_parameters.latitude,
            longitude=resolved_parameters.longitude,
        )

        final_response = self._call_gemini(
            schema=self._final_response_schema(),
            prompt=self._final_response_prompt(
                message=message,
                summary=summary,
                resolved_parameters=resolved_parameters.model_dump(),
                recommendation=recommendation,
            ),
        )

        return {
            "reply": str(final_response.get("reply") or recommendation.get("driver_message") or "I found a relocation recommendation for you."),
            "summary": str(final_response.get("summary") or self._merge_summary(summary, message, recommendation.get("driver_message", ""))),
            "parameters": resolved_parameters.model_dump(),
            "results": recommendation,
            "action": "function",
            "needs_confirmation": False,
        }

    def _resolve_parameters(self, parameters: CopilotParameters, app_context: dict, message: str) -> tuple[CopilotParameters, str | None]:
        resolved = parameters.model_copy(deep=True)
        query = (resolved.current_zone_query or "").strip()

        if not query and resolved.confirmation_options:
            normalized_message = message.strip().lower()
            if normalized_message in {"yes", "yes please", "yep", "yeah", "correct"}:
                query = resolved.confirmation_options[0]
                resolved.current_zone_query = query
            else:
                for option in resolved.confirmation_options:
                    option_normalized = option.lower()
                    option_id = option.split("(")[-1].replace(")", "").strip() if "(" in option else ""
                    if option_normalized in normalized_message or (option_id and option_id in normalized_message):
                        query = option
                        resolved.current_zone_query = query
                        break

        if query:
            zone_resolution = self._resolve_zone_query_with_gemini(query)
            status = zone_resolution.get("status")

            if status == "matched":
                matched_zone_id = zone_resolution.get("zone_id")
                matched_zone_name = zone_resolution.get("zone_name")
                if matched_zone_id is not None and matched_zone_name:
                    resolved.current_zone_id = int(matched_zone_id)
                    resolved.current_zone_name = str(matched_zone_name)
                    resolved.confirmation_options = []
                else:
                    return (
                        resolved,
                        f'I could not safely resolve "{query}" to an existing TLC taxi zone. Please try again with a zone from the list.',
                    )
            elif status == "clarify":
                options = self._zone_options_from_ids(zone_resolution.get("candidate_zone_ids") or [])
                resolved.confirmation_options = options
                clarification_question = str(zone_resolution.get("clarification_question") or "").strip()
                if not clarification_question:
                    clarification_question = (
                        f'I found a few possible TLC taxi zones for "{query}". '
                        f'Did you mean {", ".join(options)}?'
                    )
                return resolved, clarification_question
            else:
                return (
                    resolved,
                    str(
                        zone_resolution.get("clarification_question")
                        or f'I could not match "{query}" to an existing TLC taxi zone. '
                        "Please try another zone name from the relocation list."
                    ),
                )

        if resolved.current_zone_id is None and app_context.get("current_zone_id") is not None:
            resolved.current_zone_id = int(app_context["current_zone_id"])
            resolved.current_zone_name = str(app_context.get("current_zone_name") or resolved.current_zone_name or "")

        if resolved.use_current_location:
            if app_context.get("latitude") is None or app_context.get("longitude") is None:
                return (
                    resolved,
                    "I need your current device location before I can use the 'current location' scenario. Please allow location access or tell me the zone name.",
                )
            resolved.latitude = float(app_context["latitude"])
            resolved.longitude = float(app_context["longitude"])
            resolved.current_zone_id = None
            resolved.current_zone_name = None
        elif resolved.current_zone_id is None and app_context.get("latitude") is not None and app_context.get("longitude") is not None and not query:
            resolved.latitude = float(app_context["latitude"])
            resolved.longitude = float(app_context["longitude"])

        if resolved.use_current_time or resolved.day_of_week is None or resolved.hour is None:
            if app_context.get("day_of_week") is not None:
                resolved.day_of_week = int(app_context["day_of_week"])
            if app_context.get("hour") is not None:
                resolved.hour = int(app_context["hour"])

        if resolved.day_of_week is None or resolved.hour is None:
            return resolved, "I still need a valid day and time before I can run the relocator."

        if resolved.current_zone_id is None and (resolved.latitude is None or resolved.longitude is None):
            return resolved, "I need either a valid TLC taxi zone or your current location before I can run the relocator."

        return resolved, None

    def _zone_options_from_ids(self, candidate_zone_ids: list[int]) -> list[str]:
        zones = self.zone_service.available_relocation_zones()
        zones_by_id = {int(zone["id"]): zone for zone in zones}
        options: list[str] = []
        for candidate_zone_id in candidate_zone_ids[:5]:
            zone = zones_by_id.get(int(candidate_zone_id))
            if zone is not None:
                options.append(f"{zone['name']} ({zone['id']})")
        return options

    def _resolve_zone_query_with_gemini(self, query: str) -> dict:
        zones = self.zone_service.available_relocation_zones()
        zone_catalog = [
            {
                "id": int(zone["id"]),
                "name": str(zone["name"]),
            }
            for zone in zones
        ]
        zone_lookup = {int(zone["id"]): zone for zone in zone_catalog}

        resolution = self._call_gemini(
            schema=self._zone_resolution_schema(),
            prompt=self._zone_resolution_prompt(query=query, zone_catalog=zone_catalog),
        )

        status = str(resolution.get("status") or "unmatched")
        if status == "matched":
            zone_id = resolution.get("zone_id")
            if zone_id is None:
                return {
                    "status": "unmatched",
                    "clarification_question": (
                        f'I could not safely resolve "{query}" to one exact TLC taxi zone.'
                    ),
                }
            matched_zone = zone_lookup.get(int(zone_id))
            if matched_zone is None:
                return {
                    "status": "unmatched",
                    "clarification_question": (
                        f'I could not safely resolve "{query}" to one exact TLC taxi zone.'
                    ),
                }
            return {
                "status": "matched",
                "zone_id": matched_zone["id"],
                "zone_name": matched_zone["name"],
                "clarification_question": "",
            }

        if status == "clarify":
            candidate_zone_ids = [
                int(zone_id)
                for zone_id in (resolution.get("candidate_zone_ids") or [])
                if int(zone_id) in zone_lookup
            ]
            return {
                "status": "clarify",
                "candidate_zone_ids": candidate_zone_ids,
                "clarification_question": str(resolution.get("clarification_question") or "").strip(),
            }

        return {
            "status": "unmatched",
            "clarification_question": str(resolution.get("clarification_question") or "").strip(),
        }

    def _call_gemini(self, schema: dict, prompt: str) -> dict:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
        payload = {
            "system_instruction": {
                "parts": [
                    {
                        "text": (
                            "You are a relocation copilot for a rideshare app. "
                            "Only work with existing TLC taxi zones. Never invent zones, IDs, times, or model results. "
                            "If the user is unclear, ask concise follow-up questions."
                        )
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": settings.gemini_api_key,
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=45) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Gemini API request failed: {detail or exc.reason}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Gemini API request failed: {exc.reason}") from exc

        candidates = raw.get("candidates") or []
        if not candidates:
            raise RuntimeError("Gemini did not return any candidates.")

        parts = ((candidates[0].get("content") or {}).get("parts") or [])
        text = "".join(str(part.get("text", "")) for part in parts).strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response.")

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Gemini returned invalid JSON: {text}") from exc

    def _orchestration_prompt(self, message: str, summary: str, app_context: dict, session_parameters: dict) -> str:
        zones = self.zone_service.available_relocation_zones()
        zone_names = [f"{zone['name']} ({zone['id']})" for zone in zones]
        return (
            "Decide whether to chat normally or trigger the relocation function.\n"
            "Use function mode when the user wants a recommendation, asks where to relocate, asks why, or poses a what-if scenario.\n"
            "If the user says right now / my location / current location, use the app context.\n"
            "If the user names a zone, preserve the user's wording in current_zone_query instead of inventing a zone name.\n"
            "If the user is confirming or correcting a previous guess, use the latest session parameters.\n"
            "Return concise natural-language reply text.\n\n"
            f"Conversation summary:\n{summary or '(empty)'}\n\n"
            f"App context:\n{json.dumps(app_context, ensure_ascii=True)}\n\n"
            f"Latest session parameters:\n{json.dumps(session_parameters, ensure_ascii=True)}\n\n"
            f"Available TLC taxi zones:\n{json.dumps(zone_names, ensure_ascii=True)}\n\n"
            f"Latest user message:\n{message}"
        )

    def _zone_resolution_prompt(self, query: str, zone_catalog: list[dict[str, int | str]]) -> str:
        return (
            "Map the user's location phrase to the intended TLC taxi zone using only the provided zone catalog.\n"
            "Never invent a zone or ID.\n"
            "If one zone is clearly the intended match, return status 'matched' with its exact ID and name.\n"
            "If more than one zone is plausible or you are not confident, return status 'clarify' with up to 5 candidate zone IDs and a short clarification question.\n"
            "If nothing is plausible, return status 'unmatched' with a short explanation.\n\n"
            f"User location phrase:\n{query}\n\n"
            f"Valid TLC taxi zones:\n{json.dumps(zone_catalog, ensure_ascii=True)}"
        )

    def _final_response_prompt(self, message: str, summary: str, resolved_parameters: dict, recommendation: dict) -> str:
        return (
            "The relocation function has already been executed. "
            "Explain the result clearly and confidently, using the recommendation output as the backbone. "
            "Do not invent numbers or zones. Keep the reply conversational, practical, and concise.\n\n"
            f"Conversation summary:\n{summary or '(empty)'}\n\n"
            f"Latest user message:\n{message}\n\n"
            f"Resolved parameters:\n{json.dumps(resolved_parameters, ensure_ascii=True)}\n\n"
            f"Relocation result:\n{json.dumps(recommendation, ensure_ascii=True)}"
        )

    def _merge_summary(self, summary: str, message: str, reply: str) -> str:
        pieces = [part.strip() for part in [summary, f"User: {message}", f"Assistant: {reply}"] if part and part.strip()]
        merged = " ".join(pieces)
        return merged[-1800:]

    def _merge_with_session_parameters(self, parameters: CopilotParameters, session_parameters: dict) -> CopilotParameters:
        if not session_parameters:
            return parameters

        merged = parameters.model_copy(deep=True)
        previous = CopilotParameters(**session_parameters)

        if merged.current_zone_query is None:
            merged.current_zone_query = previous.current_zone_query
        if merged.current_zone_id is None:
            merged.current_zone_id = previous.current_zone_id
        if merged.current_zone_name is None:
            merged.current_zone_name = previous.current_zone_name
        if merged.day_of_week is None:
            merged.day_of_week = previous.day_of_week
        if merged.hour is None:
            merged.hour = previous.hour
        if merged.latitude is None:
            merged.latitude = previous.latitude
        if merged.longitude is None:
            merged.longitude = previous.longitude
        if not merged.confirmation_options:
            merged.confirmation_options = previous.confirmation_options
        if merged.scenario_label is None:
            merged.scenario_label = previous.scenario_label

        return merged

    def _orchestration_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "reply": {"type": "string"},
                "summary": {"type": "string"},
                "action": {"type": "string", "enum": ["chat", "function"]},
                "needs_confirmation": {"type": "boolean"},
                "parameters": {
                    "type": "object",
                    "properties": {
                        "current_zone_query": {"type": ["string", "null"]},
                        "current_zone_id": {"type": ["integer", "null"]},
                        "current_zone_name": {"type": ["string", "null"]},
                        "day_of_week": {"type": ["integer", "null"]},
                        "hour": {"type": ["integer", "null"]},
                        "use_current_location": {"type": "boolean"},
                        "use_current_time": {"type": "boolean"},
                        "latitude": {"type": ["number", "null"]},
                        "longitude": {"type": ["number", "null"]},
                        "confirmation_options": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "scenario_label": {"type": ["string", "null"]},
                    },
                    "required": [
                        "current_zone_query",
                        "current_zone_id",
                        "current_zone_name",
                        "day_of_week",
                        "hour",
                        "use_current_location",
                        "use_current_time",
                        "latitude",
                        "longitude",
                        "confirmation_options",
                        "scenario_label",
                    ],
                },
            },
            "required": ["reply", "summary", "action", "needs_confirmation", "parameters"],
        }

    def _final_response_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "reply": {"type": "string"},
                "summary": {"type": "string"},
            },
            "required": ["reply", "summary"],
        }

    def _zone_resolution_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["matched", "clarify", "unmatched"]},
                "zone_id": {"type": ["integer", "null"]},
                "zone_name": {"type": ["string", "null"]},
                "candidate_zone_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                },
                "clarification_question": {"type": "string"},
            },
            "required": [
                "status",
                "zone_id",
                "zone_name",
                "candidate_zone_ids",
                "clarification_question",
            ],
        }
