from fastapi import FastAPI, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .database import engine, SessionLocal
from .models import Base, PaymentDB
from .schemas import PaymentCreate, PaymentRead, PaymentUpdate

app = FastAPI()
Base.metadata.create_all(bind=engine)


def commit_or_rollback(db: Session, error_msg: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=error_msg)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------- Health Check ---------------------
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "payments"}


# ------------- Payment Endpoints ----------------

# GET: All payments
@app.get("/api/payments", response_model=list[PaymentRead])
def list_payments(db: Session = Depends(get_db)):
    stmt = select(PaymentDB).order_by(PaymentDB.id)
    return list(db.execute(stmt).scalars())


# GET: Payment by ID
@app.get("/api/payments/{payment_id}", response_model=PaymentRead)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.get(PaymentDB, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


# GET: Payments for a given user
@app.get("/api/users/{user_id}/payments", response_model=list[PaymentRead])
def list_payments_for_user(user_id: int, db: Session = Depends(get_db)):
    stmt = (select(PaymentDB).where(PaymentDB.user_id == user_id).order_by(PaymentDB.id))
    return list(db.execute(stmt).scalars())


#POST a new club
@app.post("/api/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentCreate, db: Session = Depends(get_db)):
    payment = PaymentDB(**payload.model_dump())
    db.add(payment)
    commit_or_rollback(db, "Conflicting data, try again")
    db.refresh(payment)
    return payment


# PATCH: Update a payment (e.g. change status to 'completed')
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


# DELETE: Remove a payment
@app.delete("/api/payments/{payment_id}", status_code=204)
def delete_payment(payment_id: int, db: Session = Depends(get_db))-> Response:
    payment = db.get(PaymentDB, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    db.delete(payment)
    commit_or_rollback(db, "Payment could not be deleted")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
