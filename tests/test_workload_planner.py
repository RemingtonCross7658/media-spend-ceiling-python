from decimal import Decimal

import pytest
from pydantic import ValidationError

from media_spend.workload_planner import SpendAllocation, WorkloadRequest


def test_rejects_media_plan_above_monthly_cap() -> None:
    with pytest.raises(ValidationError, match="allocation exceeds"):
        WorkloadRequest(
            campaign_name="September launch",
            monthly_cap_usd=Decimal("500"),
            allocation=SpendAllocation(
                asset_ingestion_usd=Decimal("120"),
                processing_jobs_usd=Decimal("310"),
                creator_delivery_usd=Decimal("90"),
            ),
            creator_brief="Send the approved portrait cut to the launch creators.",
        )


def test_accepts_media_plan_with_room_remaining() -> None:
    request = WorkloadRequest(
        campaign_name="September launch",
        monthly_cap_usd=Decimal("500"),
        allocation=SpendAllocation(
            asset_ingestion_usd=Decimal("100"),
            processing_jobs_usd=Decimal("250"),
            creator_delivery_usd=Decimal("75"),
        ),
        creator_brief="Send the approved portrait cut to the launch creators.",
    )

    assert request.allocation.total_usd == Decimal("425")

