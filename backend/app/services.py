from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Ticket, TicketMessage, TicketStatus, User


def delete_ticket(db: Session, ticket: Ticket) -> None:
    db.execute(delete(TicketMessage).where(TicketMessage.ticket_id == ticket.id))
    db.delete(ticket)
    db.commit()


def user_tickets(db: Session, user: User) -> list[Ticket]:
    return list(
        db.scalars(
            select(Ticket).where(Ticket.user_id == user.id).order_by(Ticket.updated_at.desc())
        )
    )


def suggestion_for(ticket: Ticket) -> str:
    urgency = (
        "This is marked as a high-priority request, so we are treating it with urgency."
        if ticket.priority.value in {"CRITICAL", "HIGH"}
        else "Thanks for sharing the details; we are reviewing this carefully."
    )
    return (
        f"{urgency} Based on your {ticket.category.value.lower()} issue, the next best step is "
        "to confirm the exact impact and any recent changes. We will follow up with a clear "
        "resolution path shortly."
    )


def set_default_status(ticket: Ticket) -> None:
    if ticket.status is None:
        ticket.status = TicketStatus.OPEN
