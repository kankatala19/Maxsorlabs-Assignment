from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
	__tablename__ = "users"

	id: Mapped[int] = mapped_column(primary_key=True)
	email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
	hashed_password: Mapped[str] = mapped_column(String(255))
	created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
	tickets: Mapped[list["Ticket"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Ticket(Base):
	__tablename__ = "tickets"

	id: Mapped[int] = mapped_column(primary_key=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
	subject: Mapped[str] = mapped_column(String(200))
	description: Mapped[str] = mapped_column(Text)
	created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
	user: Mapped[User] = relationship(back_populates="tickets")
	decision: Mapped["AIDecision | None"] = relationship(back_populates="ticket", uselist=False, cascade="all, delete-orphan")


class AIDecision(Base):
	__tablename__ = "ai_decisions"

	id: Mapped[int] = mapped_column(primary_key=True)
	ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), unique=True)
	action: Mapped[str] = mapped_column(String(40))
	confidence: Mapped[float] = mapped_column()
	reason: Mapped[str] = mapped_column(Text)
	sources: Mapped[str] = mapped_column(Text, default="")
	created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
	ticket: Mapped[Ticket] = relationship(back_populates="decision")
