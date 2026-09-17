import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..llm import decide_ticket
from ..models import AIDecision, Ticket, User
from ..schemas import TicketCreate, TicketRead

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _owned_ticket(db: Session, ticket_id: int, user_id: int) -> Ticket:
	ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id, Ticket.user_id == user_id))
	if ticket is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
	return ticket


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]) -> Ticket:
	ticket = Ticket(user_id=current_user.id, subject=payload.subject, description=payload.description)
	db.add(ticket)
	db.flush()
	try:
		decision = decide_ticket(payload.subject, payload.description)
	except (ValueError, RuntimeError) as error:
		db.rollback()
		raise HTTPException(status_code=502, detail=str(error)) from error
	ticket.decision = AIDecision(
		action=decision.action.value,
		confidence=decision.confidence,
		reason=decision.reason,
		sources=json.dumps(decision.sources),
	)
	db.commit()
	db.refresh(ticket)
	return ticket


@router.get("", response_model=list[TicketRead])
def list_tickets(db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]) -> list[Ticket]:
	return list(db.scalars(select(Ticket).where(Ticket.user_id == current_user.id).order_by(Ticket.created_at.desc())))


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: int, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]) -> Ticket:
	return _owned_ticket(db, ticket_id, current_user.id)
