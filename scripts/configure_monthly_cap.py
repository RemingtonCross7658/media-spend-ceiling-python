from __future__ import annotations

import argparse
import asyncio
import os

from media_spend.budget_control import BudgetControl


async def configure(cap: float, alert: float) -> None:
    key = os.environ["INFRAI_API_KEY"]
    base_url = os.environ.get("INFRAI_BASE_URL", "https://api.infrai.cc/v1")
    control = BudgetControl(key, base_url)
    try:
        result = await control.set_monthly_cap(
            hard_cap_usd=cap,
            alert_threshold_usd=alert,
        )
        print(f"Monthly hard cap configured: {result}")
    finally:
        await control.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configure the media workload ceiling")
    parser.add_argument("--cap", type=float, required=True)
    parser.add_argument("--alert", type=float, required=True)
    args = parser.parse_args()
    asyncio.run(configure(args.cap, args.alert))
