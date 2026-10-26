"""Sessions (daily shift) API routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_shop_id
from app.api.deps import require_min_role
from app.db.models.customer import Customer
from app.db.models.expense import Expense
from app.db.models.payment import Payment
from app.db.models.product import Product
from app.db.models.sale import Sale, SaleItem
from app.db.models.session import Session as SessionModel
from app.db.session import get_db

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ─── Schemas ──────────────────────────────────────────────────────


class CashMovementRequest(BaseModel):
    amount: float = Field(..., gt=0)
    reason: str | None = Field(None, max_length=500)


# ─── Helpers ──────────────────────────────────────────────────────


def _session_to_dict(s: SessionModel) -> dict:
    """Serialize a Session ORM object to a plain dict."""
    return {
        "id": s.id,
        "shop_id": s.shop_id,
        "opened_at": s.opened_at,
        "closed_at": s.closed_at,
        "opening_balance": s.opening_balance,
        "closing_balance": s.closing_balance,
        "expected_closing_balance": s.expected_closing_balance,
        "cash_discrepancy": s.cash_discrepancy,
        "discrepancy_reason": s.discrepancy_reason,
        "total_sales": s.total_sales,
        "cash_sales": s.cash_sales,
        "credit_sales": s.credit_sales,
        "total_expenses": s.total_expenses,
        "cash_removed": s.cash_removed,
        "cash_added": s.cash_added,
        "is_active": s.is_active,
        "notes": s.notes,
    }


def _compute_summary(db: Session, session: SessionModel, shop_id: str) -> dict:
    """
    Compute the live summary of a session.

    Reads from Sales / Expenses / Payments joined on session_id — the
    authoritative source. Does NOT trust `cash_sales` / `total_expenses`
    columns because those are only updated on close (or by sale creation
    which might be missing after direct DB writes).
    """
    sales_q = db.query(Sale).filter(
        Sale.session_id == session.id,
        Sale.shop_id == shop_id,
    )
    all_sales = sales_q.all()
    active_sales = [s for s in all_sales if not s.is_voided]
    voided_sales = [s for s in all_sales if s.is_voided]

    cash_sales = sum(
        (s.total_amount or 0) for s in active_sales if s.payment_status == "paid"
    )
    credit_sales = sum(
        (s.total_amount or 0)
        for s in active_sales
        if s.payment_status in ("unpaid", "partial")
    )
    total_sales = sum((s.total_amount or 0) for s in active_sales)
    voided_amount = sum((s.total_amount or 0) for s in voided_sales)

    payments = (
        db.query(Payment)
        .filter(Payment.session_id == session.id, Payment.shop_id == shop_id)
        .all()
    )
    payments_total = sum(p.amount or 0 for p in payments)
    cash_payments = sum(
        p.amount or 0 for p in payments if (p.method or "cash").lower() == "cash"
    )
    mobile_payments = sum(
        p.amount or 0
        for p in payments
        if (p.method or "").lower() in ("airtel_money", "tnm_mpamba", "mobile_money")
    )

    expenses_q = db.query(Expense).filter(
        Expense.session_id == session.id, Expense.shop_id == shop_id
    )
    expenses_total = sum((e.amount or 0) for e in expenses_q.all())
    expenses_count = expenses_q.count()

    opening = session.opening_balance or 0
    cash_added = session.cash_added or 0
    cash_removed = session.cash_removed or 0

    expected_in_drawer = (
        opening + cash_sales + cash_payments + cash_added - expenses_total - cash_removed
    )

    # If session is closed, use the frozen snapshot if present
    frozen_expected = session.expected_closing_balance
    frozen_discrepancy = session.cash_discrepancy

    return {
        "session_id": session.id,
        "opened_at": session.opened_at.isoformat() if session.opened_at else None,
        "closed_at": session.closed_at.isoformat() if session.closed_at else None,
        "is_active": bool(session.is_active),
        "opening_balance": round(opening, 2),
        "sales": {
            "total_count": len(active_sales),
            "cash_sales": round(cash_sales, 2),
            "credit_sales": round(credit_sales, 2),
            "total_sales": round(total_sales, 2),
            "voided_count": len(voided_sales),
            "voided_amount": round(voided_amount, 2),
        },
        "payments_received": {
            "count": len(payments),
            "total": round(payments_total, 2),
            "cash": round(cash_payments, 2),
            "mobile_money": round(mobile_payments, 2),
        },
        "expenses": {
            "count": expenses_count,
            "total": round(expenses_total, 2),
        },
        "cash_drawer": {
            "opening_balance": round(opening, 2),
            "plus_cash_sales": round(cash_sales, 2),
            "plus_cash_payments_received": round(cash_payments, 2),
            "plus_cash_added": round(cash_added, 2),
            "minus_expenses": round(expenses_total, 2),
            "minus_cash_removed": round(cash_removed, 2),
            "expected_in_drawer": round(expected_in_drawer, 2),
            "frozen_expected": round(frozen_expected, 2) if frozen_expected is not None else None,
            "physical_count": round(session.closing_balance, 2)
            if session.closing_balance is not None
            else None,
            "discrepancy": round(frozen_discrepancy, 2)
            if frozen_discrepancy is not None
            else None,
            "discrepancy_reason": session.discrepancy_reason,
        },
        "computed_at": datetime.utcnow().isoformat(),
    }


def _get_active_session(db: Session, shop_id: str) -> SessionModel | None:
    return (
        db.query(SessionModel)
        .filter(SessionModel.is_active == True, SessionModel.shop_id == shop_id)
        .first()
    )


# ─── Open ─────────────────────────────────────────────────────────


@router.post("/open")
def open_session(
    opening_balance: float = Query(0.0),
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Open a new session (daily shift)."""
    active = _get_active_session(db, shop_id)
    if active:
        raise HTTPException(status_code=400, detail="A session is already open")

    if opening_balance < 0:
        raise HTTPException(status_code=400, detail="Opening balance cannot be negative")

    new_session = SessionModel(
        id=str(uuid.uuid4()),
        opening_balance=opening_balance,
        is_active=True,
        shop_id=shop_id,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return _session_to_dict(new_session)


# ─── Cash movements (added/removed) ──────────────────────────────


@router.post(
    "/current/cash-out",
    dependencies=[Depends(require_min_role("manager"))],
)
def cash_out(
    payload: CashMovementRequest,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Record cash removed from the drawer (e.g. bank deposit).

    Adds to `cash_removed` and appends the reason to `notes`.
    """
    active = _get_active_session(db, shop_id)
    if not active:
        raise HTTPException(status_code=404, detail="No active session")

    active.cash_removed = (active.cash_removed or 0) + payload.amount

    if payload.reason:
        note = f"Cash out MWK {payload.amount:,.0f}: {payload.reason}"
        active.notes = (active.notes + "\n" + note) if active.notes else note

    db.commit()
    db.refresh(active)
    return _session_to_dict(active)


@router.post(
    "/current/cash-in",
    dependencies=[Depends(require_min_role("manager"))],
)
def cash_in(
    payload: CashMovementRequest,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Record cash added to the drawer (e.g. emergency float)."""
    active = _get_active_session(db, shop_id)
    if not active:
        raise HTTPException(status_code=404, detail="No active session")

    active.cash_added = (active.cash_added or 0) + payload.amount

    if payload.reason:
        note = f"Cash in MWK {payload.amount:,.0f}: {payload.reason}"
        active.notes = (active.notes + "\n" + note) if active.notes else note

    db.commit()
    db.refresh(active)
    return _session_to_dict(active)


# ─── Close (with reconciliation) ─────────────────────────────────


@router.post(
    "/close",
    dependencies=[Depends(require_min_role("manager"))],
)
def close_session(
    closing_balance: float,
    notes: str = None,
    discrepancy_reason: str = None,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Close the active session and reconcile the cash drawer.

    - Computes expected cash from live data
    - Compares with the physical count (closing_balance)
    - Stores discrepancy + reason
    - If discrepancy != 0, requires discrepancy_reason (client should send it)
    """
    active = _get_active_session(db, shop_id)
    if not active:
        raise HTTPException(status_code=404, detail="No active session")

    if closing_balance < 0:
        raise HTTPException(status_code=400, detail="Closing balance cannot be negative")

    # Compute live summary and expected drawer
    summary = _compute_summary(db, active, shop_id)
    expected = float(summary["cash_drawer"]["expected_in_drawer"])
    discrepancy = round(float(closing_balance) - expected, 2)

    # If materially short/over, require a reason
    if abs(discrepancy) >= 1 and not discrepancy_reason:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cash drawer is {'over' if discrepancy > 0 else 'short'} by MWK "
                f"{abs(discrepancy):,.2f}. A discrepancy_reason is required."
            ),
        )

    # Persist
    active.closed_at = datetime.utcnow()
    active.closing_balance = closing_balance
    active.expected_closing_balance = expected
    active.cash_discrepancy = discrepancy
    active.discrepancy_reason = discrepancy_reason
    active.total_sales = float(summary["sales"]["total_sales"])
    active.cash_sales = float(summary["sales"]["cash_sales"])
    active.credit_sales = float(summary["sales"]["credit_sales"])
    active.total_expenses = float(summary["expenses"]["total"])
    active.is_active = False
    if notes:
        active.notes = (active.notes + "\n" + notes) if active.notes else notes

    db.commit()
    db.refresh(active)
    return {"message": "Session closed", "session": _session_to_dict(active)}


# ─── Current ──────────────────────────────────────────────────────


@router.get("/current")
def get_current_session(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    active = _get_active_session(db, shop_id)
    if not active:
        return {"detail": "No active session"}
    return _session_to_dict(active)


@router.get("/current/summary")
def get_current_session_summary(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Live-computed summary for the currently active session."""
    active = _get_active_session(db, shop_id)
    if not active:
        raise HTTPException(status_code=404, detail="No active session")
    return _compute_summary(db, active, shop_id)


# ─── Summary / detail for any session (past or active) ───────────


@router.get("/{session_id}/summary")
def get_session_summary(
    session_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """Reconciliation summary for ANY session (used by the drawer)."""
    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id, SessionModel.shop_id == shop_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _compute_summary(db, session, shop_id)


@router.get("/{session_id}/detail")
def get_session_detail(
    session_id: str,
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    Full item-level detail for a session:
    - sales (with items)
    - expenses
    - payments received
    """
    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id, SessionModel.shop_id == shop_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Sales
    sales = (
        db.query(Sale)
        .filter(Sale.session_id == session_id, Sale.shop_id == shop_id)
        .order_by(Sale.created_at.desc())
        .all()
    )
    sale_ids = [s.id for s in sales]
    items_by_sale: dict[str, list[dict]] = {}
    if sale_ids:
        rows = (
            db.query(
                SaleItem.sale_id,
                Product.name,
                SaleItem.quantity,
                SaleItem.unit_price,
                SaleItem.total_price,
            )
            .join(Product, Product.id == SaleItem.product_id)
            .filter(SaleItem.sale_id.in_(sale_ids))
            .all()
        )
        for sale_id, name, qty, unit_px, total_px in rows:
            items_by_sale.setdefault(sale_id, []).append({
                "name": name,
                "quantity": float(qty or 0),
                "unit_price": float(unit_px or 0),
                "total_price": float(total_px or 0),
            })

    customer_ids = {s.customer_id for s in sales if s.customer_id}
    customer_names: dict[str, str] = {}
    if customer_ids:
        for c in (
            db.query(Customer.id, Customer.name)
            .filter(Customer.id.in_(customer_ids), Customer.shop_id == shop_id)
            .all()
        ):
            customer_names[c.id] = c.name

    sales_out = [
        {
            "id": s.id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "total_amount": float(s.total_amount or 0),
            "amount_paid": float(s.amount_paid or 0),
            "payment_status": s.payment_status,
            "is_voided": bool(s.is_voided),
            "void_reason": s.void_reason,
            "customer_name": customer_names.get(s.customer_id) if s.customer_id else None,
            "items": items_by_sale.get(s.id, []),
        }
        for s in sales
    ]

    # Expenses
    expenses = (
        db.query(Expense)
        .filter(Expense.session_id == session_id, Expense.shop_id == shop_id)
        .order_by(Expense.created_at.desc())
        .all()
    )
    expenses_out = [
        {
            "id": e.id,
            "name": e.name,
            "amount": float(e.amount or 0),
            "category": e.category,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in expenses
    ]

    # Payments
    payments = (
        db.query(Payment)
        .filter(Payment.session_id == session_id, Payment.shop_id == shop_id)
        .order_by(Payment.created_at.desc())
        .all()
    )
    payments_out = [
        {
            "id": p.id,
            "amount": float(p.amount or 0),
            "method": p.method,
            "customer_id": p.customer_id,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in payments
    ]

    return {
        "session": _session_to_dict(session),
        "sales": sales_out,
        "expenses": expenses_out,
        "payments": payments_out,
    }


# ─── List all sessions ────────────────────────────────────────────


@router.get("/")
def get_sessions(
    db: Session = Depends(get_db),
    shop_id: str = Depends(get_current_shop_id),
):
    """
    All sessions for this shop, newest first.

    Adds a `reconciliation_status` field per session:
      'active'    — currently open
      'balanced'  — |discrepancy| < 1
      'short'     — drawer short
      'over'      — drawer over
      'not_reconciled' — closed before reconciliation was introduced
    """
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.shop_id == shop_id)
        .order_by(SessionModel.opened_at.desc())
        .all()
    )

    result = []
    for s in sessions:
        d = _session_to_dict(s)
        if s.is_active:
            d["reconciliation_status"] = "active"
        elif s.cash_discrepancy is None:
            d["reconciliation_status"] = "not_reconciled"
        elif abs(s.cash_discrepancy) < 1:
            d["reconciliation_status"] = "balanced"
        elif s.cash_discrepancy < 0:
            d["reconciliation_status"] = "short"
        else:
            d["reconciliation_status"] = "over"
        result.append(d)
    return result