import json
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

from .rag import retrieve_context
from .schemas import Action

load_dotenv()


class Decision(BaseModel):
	action: Action
	confidence: float = Field(ge=0, le=1)
	reason: str = Field(min_length=1)
	sources: list[str]


def decide_ticket(subject: str, description: str) -> Decision:
	context = retrieve_context(f"{subject}\n{description}")
	sources = [str(item["source"]) for item in context]
	if not context:
		return Decision(action=Action.NEEDS_MORE_INFORMATION, confidence=1.0, reason="No matching policy context was found.", sources=[])

	api_key = os.getenv("OPENAI_API_KEY", "")
	if not api_key or api_key == "your_key":
		return Decision(action=Action.NEEDS_MORE_INFORMATION, confidence=0.5, reason="A policy match was found, but an AI decision could not be verified.", sources=sources)

	from openai import OpenAI

	client = OpenAI(api_key=api_key, timeout=60)
	policy = "\n\n".join(f"[{item['source']}]\n{item['text']}" for item in context)
	response = client.chat.completions.create(
		model="gpt-4.1-mini",
		temperature=0,
		response_format={"type": "json_object"},
		messages=[
			{"role": "system", "content": "You are a support policy decision assistant. Return only JSON with action, confidence, reason, and sources. Use NEEDS_MORE_INFORMATION when policy context is insufficient. Allowed actions: REFUND, REPLACE, RETURN, REQUEST_PHOTOS, REQUEST_MORE_INFORMATION, DENY, NEEDS_MORE_INFORMATION."},
			{"role": "user", "content": f"Ticket:\nSubject: {subject}\nDescription: {description}\n\nPolicy context:\n{policy}"},
		],
	)
	raw = response.choices[0].message.content or "{}"
	try:
		decision = Decision.model_validate_json(raw)
	except (ValidationError, json.JSONDecodeError) as error:
		raise ValueError("The AI returned an invalid decision") from error
	return decision.model_copy(update={"sources": sources})
