from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BillingAccountResponse(BaseModel):
    project_id: str
    currency: str
    balance_credits: int
    reserved_credits: int
    available_credits: int
    lifetime_purchased_credits: int
    lifetime_used_credits: int


class TopUpRequest(BaseModel):
    amount_credits: int = Field(gt=0)
    description: str | None = Field(default=None, max_length=500)


class CreditTransactionResponse(BaseModel):
    id: str
    type: str
    amount_credits: int
    balance_after_credits: int
    reserved_after_credits: int
    description: str | None
    created_at: datetime


class TransactionListResponse(BaseModel):
    transactions: list[CreditTransactionResponse]
    count: int


class QuotaResponse(BaseModel):
    project_id: str
    daily_job_limit: int | None
    monthly_job_limit: int | None
    daily_credit_limit: int | None
    monthly_credit_limit: int | None
    max_concurrent_jobs: int | None


class QuotaUpdateRequest(BaseModel):
    daily_job_limit: int | None = Field(default=None, ge=0)
    monthly_job_limit: int | None = Field(default=None, ge=0)
    daily_credit_limit: int | None = Field(default=None, ge=0)
    monthly_credit_limit: int | None = Field(default=None, ge=0)
    max_concurrent_jobs: int | None = Field(default=None, ge=0)


class UsageResponse(BaseModel):
    project_id: str
    daily_jobs: int
    monthly_jobs: int
    daily_credits: int
    monthly_credits: int


class ReconciliationResponse(BaseModel):
    account: BillingAccountResponse
    corrected: bool
    metadata: dict[str, Any]
