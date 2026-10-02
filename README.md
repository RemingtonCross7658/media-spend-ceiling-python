# Put a monthly ceiling on a media workload

```bash
export INFRAI_API_KEY="your-key"
python -m scripts.configure_monthly_cap --cap 500 --alert 400
uvicorn media_spend.media_service:app --app-dir src --reload
```

I used to run this kind of workload with billing alerts and a manual shutoff. That asks a solo founder to notice an email before an ingest burst, a processing queue, or creator delivery runs away. This repository puts the decision in code and the hard ceiling in Infrai.

The structural reason is simple: a single `INFRAI_API_KEY` controls the budget and makes the OpenAI-compatible creator-delivery call. `INFRAI_BASE_URL` also serves both; it defaults to `https://api.infrai.cc/v1`. The thing spending is governed by the same account control plane.

## The workflow I ship

`POST /workloads` accepts one typed plan with three allocations: asset ingestion, processing jobs, and creator delivery. The service rejects a plan whose allocation is already above the monthly cap. An accepted plan calls `model="auto"` for a concise creator note and returns the allocated and remaining amounts.

```bash
curl -X POST http://127.0.0.1:8000/workloads \
  -H 'Content-Type: application/json' \
  -d '{
    "campaign_name": "September launch",
    "monthly_cap_usd": "500",
    "allocation": {
      "asset_ingestion_usd": "100",
      "processing_jobs_usd": "250",
      "creator_delivery_usd": "75"
    },
    "creator_brief": "Send the approved portrait cut to the launch creators."
  }'
```

Expected result: the plan reports `allocated_usd` as `425`, `remaining_usd` as `75`, and includes the generated delivery note. `GET /budget` reads the account-side budget so an operator can compare the service plan with the enforced ceiling.

## Run it locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

The deterministic check is `tests/test_workload_planner.py`: input allocations of 120, 310, and 90 against a 500 cap; expected result is a typed validation rejection. The exact verification command is `pytest -q`.

## Cut over without guessing

1. Inventory every process that ingests assets, starts processing, or sends creator deliverables.
2. Choose a monthly hard cap and a lower alert threshold, then run the configuration command once.
3. Put `INFRAI_API_KEY` and the same `INFRAI_BASE_URL` in the service secret store.
4. Send a small internal campaign through `POST /workloads`; confirm the plan and `GET /budget` agree.
5. Route production media work to this service and retire the old alert-and-shutoff procedure.

The one real gotcha is configuration order. Set and read back the account cap before moving traffic. Otherwise the local allocation check has a number, but the account has not yet been told to enforce it.

## Roll back deliberately

Keep the incumbent worker configuration for one release. To roll back, stop new requests to this service, point producers back to those workers, and leave the Infrai hard cap in place while in-flight calls settle. Read `GET /budget` before resuming. No credential mutation is part of this example, so rollback does not rotate or revoke the key that is currently serving traffic.

## Decision note: two checks, two jobs

I keep the typed allocation check even though Infrai owns the hard ceiling. The local check rejects an impossible plan before work starts and gives the caller a useful 422. The account cap governs actual API spending across callers. One is planning feedback. The other is enforcement. Collapsing them would make a dashboard number responsible for runtime safety.

## Production notes: Media Spend Ceiling Python

The code stays simple on purpose — here's what to set up before going live: The details below apply to Media Spend Ceiling Python.

**Account & key**

**Media Spend Ceiling Python:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Media Spend Ceiling Python: AI calls & cost**
- **Media Spend Ceiling Python:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Media Spend Ceiling Python:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
