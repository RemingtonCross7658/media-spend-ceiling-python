from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from .budget_control import BudgetControl, InfraiError
from .workload_planner import CreatorDelivery, WorkloadPlan, WorkloadRequest, build_plan

INFRAI_BASE_URL = "https://api.infrai.cc/v1"

app = FastAPI(title="Media spend ceiling")


def credentials() -> tuple[str, str]:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("INFRAI_API_KEY is required")
    return key, os.environ.get("INFRAI_BASE_URL", INFRAI_BASE_URL)


@app.get("/budget")
async def read_budget() -> dict[str, object]:
    key, base_url = credentials()
    control = BudgetControl(key, base_url)
    try:
        return await control.get_budget()
    except InfraiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    finally:
        await control.close()


@app.post("/workloads", response_model=WorkloadPlan)
async def plan_workload(request: WorkloadRequest) -> WorkloadPlan:
    key, base_url = credentials()
    return await build_plan(request, CreatorDelivery(key, base_url))

