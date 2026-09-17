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


def decide_ticket(
    subject: str,
    description: str,
    order_value_inr: int | None = None,
    days_since_delivery: int | None = None,
    days_since_dispatch: int | None = None,
    product_type: str | None = None,
    opened_status: str | None = None,
    order_status: str | None = None,
) -> Decision:

    ticket_info = f"""
Subject: {subject}
Customer message: {description}

Structured information, if available:
Order value (INR): {order_value_inr}
Days since delivery: {days_since_delivery}
Days since dispatch: {days_since_dispatch}
Product type: {product_type}
Opened status: {opened_status}
Order status: {order_status}
"""

    # Retrieve relevant policy documents
    context = retrieve_context(ticket_info)

    sources = [str(item["source"]) for item in context]

    # No policy context
    if not context:
        return Decision(
            action=Action.NEEDS_MORE_INFORMATION,
            confidence=0.5,
            reason="No matching policy context was found for this ticket.",
            sources=[],
        )

    api_key = os.getenv("OPENAI_API_KEY", "")

    # No API key
    if not api_key or api_key == "your_key":
        return Decision(
            action=Action.NEEDS_MORE_INFORMATION,
            confidence=0.5,
            reason="A policy match was found, but an AI decision could not be verified.",
            sources=sources,
        )

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        timeout=60,
    )

    policy = "\n\n".join(
        f"[{item['source']}]\n{item['text']}"
        for item in context
    )

    system_prompt = """
You are an AI support policy decision assistant.

Your job is to analyze a customer support ticket using ONLY:
1. The customer ticket information.
2. The provided company policy context.

Return ONLY valid JSON with exactly these fields:

{
  "action": "...",
  "confidence": 0.0,
  "reason": "...",
  "sources": ["..."]
}

Allowed actions:

REQUEST_DEFECT_EVIDENCE
APPROVE_REFUND_OR_REPLACEMENT
APPROVE_RETURN
REQUEST_PHOTOS
APPROVE_REPLACEMENT
CANNOT_CANCEL_AFTER_DISPATCH
CANCEL_AND_REFUND
REJECT_OUTSIDE_WINDOW
WAIT_AND_TRACK
NEEDS_MORE_INFORMATION
REJECT_FOOD_RETURN
OFFER_REPLACEMENT_OR_REFUND
OPEN_SHIPPING_INVESTIGATION
REPLACE_CORRECT_ITEM
REJECT_OPENED_ITEM
REFUND
REPLACE
RETURN
DENY
REQUEST_MORE_INFORMATION


IMPORTANT DECISION RULES

1. READ NATURAL LANGUAGE CAREFULLY

Customer information may be written naturally inside the message.

Do NOT require information to appear as separate structured fields.

Examples:

"delivered 2 days ago"
means the product was delivered 2 days ago.

"arrived yesterday"
means the product was delivered yesterday.

"delivered 5 days ago"
means the product was delivered 5 days ago.

"delivered on June 1. Today is September"
provides delivery timing information.

"I uploaded photos"
means photo evidence is available.

"I don't want a replacement"
means the customer does not want a replacement.

"I want a refund"
means the customer is requesting a refund.

"I want to return it"
means the customer is requesting a return.

"unused with tags"
means the product is unused/unopened.

"I wore the shoes"
means the product has been used/opened.


2. DO NOT AUTOMATICALLY REQUEST MORE INFORMATION

Do NOT choose NEEDS_MORE_INFORMATION simply because one of the structured
metadata fields is empty.

Missing optional metadata alone is NOT enough to request more information.

First inspect the customer's natural-language message and extract all facts
that are explicitly stated.

Only choose NEEDS_MORE_INFORMATION when information genuinely required by the
applicable policy is missing and cannot reasonably be determined from the
ticket.


3. DAMAGED GOODS

For damaged goods, carefully identify:

- Whether the item is damaged.
- When it was delivered.
- Whether photo evidence is available.
- The order value, if explicitly provided.
- What action the customer wants.

If the customer says:

"I do not want a replacement"
and
"Please refund my card"

then the customer's requested action is a refund.

Do NOT recommend a replacement merely because the policy also allows
replacement.

If the customer says:

"I uploaded photos"

treat the photo evidence as provided.

Do NOT say that photos are missing when the customer explicitly says they
uploaded photos.


4. WRONG ITEM / WRONG VARIANT

Identify:

- What the customer ordered.
- What the customer received.
- When it was delivered.
- Whether the item is unused/opened.
- What the customer wants.

For a wrong item or wrong flavour/variant, use:

REPLACE_CORRECT_ITEM

when the applicable policy conditions are satisfied.

Do NOT use APPROVE_REPLACEMENT for a wrong-item or wrong-variant case.

If the customer explicitly requests a return, consider the applicable policy
and the customer's request before selecting the action.


5. RETURNS

Use delivery timing stated in the customer's message.

Examples:

"delivered 5 days ago"
"delivered 10 days ago"
"two months ago"
"delivered on June 1. Today is September"

are all useful timing information.

Do not require a separate days_since_delivery field when the timing can be
understood from the customer's message.

Use product type when stated.

Use opened/unused/used status when stated.


6. SHIPPING

Use dispatch timing when the customer provides it.

Examples:

"dispatched 9 days ago"
"it was shipped 6 days ago"

provide dispatch timing.

Apply the shipping policy using that information.


7. CANCELLATION

If the ticket contains information about whether the order has been
dispatched, use that information.

Do not assume that an order is dispatched or not dispatched when the ticket
does not say so.


8. DO NOT INVENT FACTS

Never invent:

- order value
- delivery date
- dispatch date
- product type
- opened/unused status
- order status
- photo evidence

Use only information explicitly stated or clearly inferable from the
customer's message.


9. NEEDS_MORE_INFORMATION

Use NEEDS_MORE_INFORMATION only when:

- the applicable policy requires a specific fact,
- that fact is genuinely missing,
- and it cannot be inferred from the ticket.

For example:

"I want to return this."

may require more information because the ticket does not identify enough
information to determine which return policy applies.


10. FOLLOW THE POLICY

The policy context is the source of truth.

Do not use general customer-service assumptions when the policy gives a
specific rule.


11. CONFIDENCE

Return confidence as a decimal between 0 and 1.

Examples:

0.95 means 95%
0.80 means 80%
0.60 means 60%

Do NOT return confidence as 100, 95, or any number greater than 1.

The confidence value MUST always be between 0 and 1.


12. SOURCES

The application will provide the retrieved policy source filenames.

Return the relevant source filenames.

Do not invent source filenames.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    f"Ticket information:\n"
                    f"{ticket_info}\n\n"
                    f"Policy context:\n"
                    f"{policy}"
                ),
            },
        ],
    )

    raw = response.choices[0].message.content or "{}"

    try:
        data = json.loads(raw)

        # Protect against the model returning percentage instead of decimal.
        confidence = data.get("confidence")

        if isinstance(confidence, (int, float)):
            if confidence > 1 and confidence <= 100:
                confidence = confidence / 100

            data["confidence"] = confidence

        decision = Decision.model_validate(data)

    except (ValidationError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise ValueError(
            "The AI returned an invalid decision."
        ) from error

    # Always use the sources actually retrieved by RAG.
    return decision.model_copy(
        update={
            "sources": sources,
        }
    )