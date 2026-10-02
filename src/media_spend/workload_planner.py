from __future__ import annotations

from decimal import Decimal

from openai import AsyncOpenAI
from pydantic import BaseModel, Field, model_validator


class SpendAllocation(BaseModel):
    asset_ingestion_usd: Decimal = Field(ge=0)
    processing_jobs_usd: Decimal = Field(ge=0)
    creator_delivery_usd: Decimal = Field(ge=0)

    @property
    def total_usd(self) -> Decimal:
        return (
            self.asset_ingestion_usd
            + self.processing_jobs_usd
            + self.creator_delivery_usd
        )


class WorkloadRequest(BaseModel):
    campaign_name: str = Field(min_length=1, max_length=100)
    monthly_cap_usd: Decimal = Field(gt=0)
    allocation: SpendAllocation
    creator_brief: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def allocation_fits_cap(self) -> "WorkloadRequest":
        if self.allocation.total_usd > self.monthly_cap_usd:
            raise ValueError("media allocation exceeds the monthly hard cap")
        return self


class WorkloadPlan(BaseModel):
    campaign_name: str
    monthly_cap_usd: Decimal
    allocated_usd: Decimal
    remaining_usd: Decimal
    creator_delivery_note: str


class CreatorDelivery:
    def __init__(self, api_key: str, base_url: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def write_note(self, brief: str) -> str:
        response = await self._client.chat.completions.create(
            model="auto",
            messages=[
                {
                    "role": "system",
                    "content": "Write one concise delivery note for a media creator.",
                },
                {"role": "user", "content": brief},
            ],
        )
        return response.choices[0].message.content or "Delivery is ready."


async def build_plan(request: WorkloadRequest, delivery: CreatorDelivery) -> WorkloadPlan:
    note = await delivery.write_note(request.creator_brief)
    allocated = request.allocation.total_usd
    return WorkloadPlan(
        campaign_name=request.campaign_name,
        monthly_cap_usd=request.monthly_cap_usd,
        allocated_usd=allocated,
        remaining_usd=request.monthly_cap_usd - allocated,
        creator_delivery_note=note,
    )

