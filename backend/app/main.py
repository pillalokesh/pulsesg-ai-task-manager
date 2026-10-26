import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import DEFAULT_JWT_SECRET, settings
from app.db import Base, engine, get_db
from app.models import Ticket, TicketMessage, User
from app.schemas import (
    AuthRequest,
    AuthResponse,
    MessageRequest,
    MessageResponse,
    ProfileUpdate,
    RegisterRequest,
    SuggestionResponse,
    TicketRequest,
    TicketResponse,
    TicketUpdate,
    UserResponse,
)
from app.security import create_token, current_user, hash_password, verify_password
from app.services import delete_ticket, set_default_status, suggestion_for, user_tickets


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.app_env == "production" and settings.jwt_secret == DEFAULT_JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be configured outside local development")
    if settings.create_schema:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="PulsesG Support Portal", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
prefix = f"{settings.context_path}/api"
logger = logging.getLogger(__name__)


def error_response(request: Request, status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "timestamp": datetime.now(UTC).isoformat(),
            "status": status_code,
            "message": message,
            "path": request.url.path,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, _: RequestValidationError) -> JSONResponse:
    return error_response(request, 400, "Please check the submitted fields")


@app.exception_handler(HTTPException)
async def http_error(request: Request, error: HTTPException) -> JSONResponse:
    message = str(error.detail)
    if error.status_code == 401 and message in {"Unauthorized", "Not authenticated"}:
        message = "Unauthorized"
    response = error_response(request, error.status_code, message)
    if error.headers:
        response.headers.update(error.headers)
    return response


@app.exception_handler(Exception)
async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=(type(error), error, error.__traceback__),
    )
    return error_response(request, 500, "An unexpected error occurred")


@app.get(f"{settings.context_path}/actuator/health")
def health(response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "DOWN"}
    return {"status": "UP"}


@app.post(f"{prefix}/auth/register", response_model=AuthResponse, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    email = str(request.email).lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = User(
        full_name=request.fullName,
        email=email,
        password_hash=hash_password(request.password),
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered") from error
    return AuthResponse(token=create_token(user.email), user=UserResponse.model_validate(user))


@app.post(f"{prefix}/auth/login", response_model=AuthResponse)
def login(request: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.scalar(select(User).where(func.lower(User.email) == str(request.email).lower()))
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return AuthResponse(token=create_token(user.email), user=UserResponse.model_validate(user))


@app.get(f"{prefix}/auth/me", response_model=UserResponse)
def auth_me(user: User = Depends(current_user)) -> User:
    return user


@app.get(f"{prefix}/users/me", response_model=UserResponse)
def get_profile(user: User = Depends(current_user)) -> User:
    return user


@app.put(f"{prefix}/users/me", response_model=UserResponse)
def update_profile(
    request: ProfileUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> User:
    user.full_name = request.fullName
    db.commit()
    db.refresh(user)
    return user


def owned_ticket(ticket_id: int, user: User, db: Session) -> Ticket:
    ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id, Ticket.user_id == user.id))
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.get(f"{prefix}/tickets", response_model=list[TicketResponse])
def list_tickets(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_tickets(db, user)


@app.post(f"{prefix}/tickets", response_model=TicketResponse, status_code=201)
def create_ticket(
    request: TicketRequest, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    ticket = Ticket(
        user_id=user.id,
        title=request.title,
        description=request.description,
        category=request.category,
        priority=request.priority,
    )
    set_default_status(ticket)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.get(f"{prefix}/tickets/{{ticket_id}}", response_model=TicketResponse)
def get_ticket(ticket_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return owned_ticket(ticket_id, user, db)


@app.put(f"{prefix}/tickets/{{ticket_id}}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    request: TicketUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    ticket = owned_ticket(ticket_id, user, db)
    for field, value in request.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(ticket, field, value)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.delete(f"{prefix}/tickets/{{ticket_id}}", status_code=status.HTTP_204_NO_CONTENT)
def remove_ticket(
    ticket_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    delete_ticket(db, owned_ticket(ticket_id, user, db))


@app.get(f"{prefix}/tickets/{{ticket_id}}/messages", response_model=list[MessageResponse])
def list_messages(
    ticket_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    owned_ticket(ticket_id, user, db)
    return list(
        db.scalars(
            select(TicketMessage)
            .where(TicketMessage.ticket_id == ticket_id)
            .order_by(TicketMessage.created_at.asc())
        )
    )


@app.post(
    f"{prefix}/tickets/{{ticket_id}}/messages", response_model=MessageResponse, status_code=201
)
def create_message(
    ticket_id: int,
    request: MessageRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    owned_ticket(ticket_id, user, db)
    message = TicketMessage(ticket_id=ticket_id, user_id=user.id, message=request.message)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@app.post(f"{prefix}/tickets/{{ticket_id}}/ai-suggestion", response_model=SuggestionResponse)
def ticket_suggestion(
    ticket_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return SuggestionResponse(suggestion=suggestion_for(owned_ticket(ticket_id, user, db)))
