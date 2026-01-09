from typing import Annotated, Optional
from annotated_types import Ge
from pydantic import BaseModel, StringConstraints, ConfigDict

AmountInt = Annotated[int, Ge(1)]
CurrencyStr = Annotated[str, StringConstraints(min_length=3, max_length=3)]
StatusStr = Annotated[str, StringConstraints(pattern=r"^(pending|completed|failed|refunded)$")]
PaymentMethodStr = Annotated[str, StringConstraints(min_length=2, max_length=50)]
DescriptionStr = Annotated[str, StringConstraints(min_length=0, max_length=255)]


class PaymentCreate(BaseModel):
    user_id: int
    amount_cents: AmountInt
    currency: CurrencyStr
    description: Optional[DescriptionStr] = None
    payment_method: PaymentMethodStr


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    amount_cents: AmountInt
    currency: CurrencyStr
    description: Optional[str] = None
    status: StatusStr
    payment_method: PaymentMethodStr


class PaymentUpdate(BaseModel):
    amount_cents: Optional[AmountInt] = None
    currency: Optional[CurrencyStr] = None
    description: Optional[DescriptionStr] = None
    status: Optional[StatusStr] = None
    payment_method: Optional[PaymentMethodStr] = None
