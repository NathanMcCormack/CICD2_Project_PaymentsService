from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .database import engine, get_db
from .models import Base, PaymentDB, UserDB
from .schemas import PaymentCreate, PaymentRead, PaymentUpdate
from app.mq import publish_payment_created
import os
import httpx

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables once on startup
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Payments Service", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def commit_or_rollback(db: Session, error_msg: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=error_msg)

def verify_user_exists(user_id: int) -> None:
    base_url = os.getenv("USER_SERVICE_URL", "http://localhost:8001").rstrip("/")
    url = f"{base_url}/api/users/{user_id}"

    try:
        r = httpx.get(url, timeout=2.0)
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Users service unavailable")

    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="User not found")
    if r.status_code != 200:
        raise HTTPException(status_code=503, detail="Users service unavailable")


# ------------- Health Check ---------------------
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "payments"}


# ------------- Payment Endpoints ----------------
@app.get("/api/payments", response_model=list[PaymentRead])
def list_payments(db: Session = Depends(get_db)):
    stmt = select(PaymentDB).order_by(PaymentDB.id)
    return list(db.execute(stmt).scalars())


@app.get("/api/payments/{payment_id}", response_model=PaymentRead)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.get(PaymentDB, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@app.get("/api/users/{user_id}/payments", response_model=list[PaymentRead])
def list_payments_for_user(user_id: int, db: Session = Depends(get_db)):
    stmt = select(PaymentDB).where(PaymentDB.user_id == user_id).order_by(PaymentDB.id)
    return list(db.execute(stmt).scalars())

@app.post("/api/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentCreate, db: Session = Depends(get_db)):
    verify_user_exists(payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    payment = PaymentDB(**payload.model_dump())
    db.add(payment)
    commit_or_rollback(db, "Payment could not be created")
    db.refresh(payment)

    publish_payment_created(
        {
            "event": "payment_created",
            "payment_id": payment.id,
            "user_id": payment.user_id,
        }
    )

    return payment

@app.patch("/api/payments/{payment_id}", response_model=PaymentRead)
def patch_payment(payment_id: int, payload: PaymentUpdate, db: Session = Depends(get_db)):
    payment = db.get(PaymentDB, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    for field_name, field_value in payload.model_dump(exclude_unset=True).items():
        setattr(payment, field_name, field_value)

    commit_or_rollback(db, "Payment could not be updated")
    db.refresh(payment)
    return payment


@app.delete("/api/payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(payment_id: int, db: Session = Depends(get_db)) -> Response:
    payment = db.get(PaymentDB, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    db.delete(payment)
    commit_or_rollback(db, "Payment could not be deleted")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
