from fastapi import FastAPI

from .database import Base, engine
from .routers import auth, tickets

Base.metadata.create_all(bind=engine)
app = FastAPI(title="AI Support Ticket Decision Assistant")
app.include_router(auth.router)
app.include_router(tickets.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI Support Ticket API is running"}
