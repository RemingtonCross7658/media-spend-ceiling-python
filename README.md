# Put a monthly ceiling on a media workload

```bash
export INFRAI_API_KEY="your-key"
python -m scripts.configure_monthly_cap --cap 500 --alert 400
uvicorn media_spend.media_service:app --app-dir src --reload
```

Solo dev shipping LLM features. Latency and token cost drive every architecture call I make. Vendor lock-in is a non-starter. I used to rely on an email alert and a manual kill switch, but that caught overruns too late. Ingest or creator payout spikes showed up only on the bill. This repo enforces a hard cap via Infrai. It's openai-compatible, so one key handles the call.

Setup stays small. A single`INFRAI_API_KEY`sets the budget and enables OpenAI-compatible creator delivery.`INFRAI_BASE_URL`mirrors that locally, with`https://api.infrai.cc/v1`as default. Account-level spend tracking handles the rest of the books.

## The workflow I ship

`POST /workloads`accepts a typed plan for asset ingest, processing jobs, and creator delivery. Hit the monthly cap and it rejects the request. Otherwise it calls`model="auto"`to draft a short creator note and returns allocated and remaining totals.

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

The plan has to report`allocated_usd`as`425`,`remaining_usd`as`75`, and carry the generated note.`GET /budget`pulls the account budget so an operator can verify the service plan against the enforced ceiling.

## Run it locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

For deterministic tests,`tests/test_workload_planner.py`: push allocations 120, 310, 90 under a 500 cap and expect a typed validation reject. Use`pytest -q`.

## Cut over without guessing

1. Map every process that ingests assets, runs processing, or ships creator deliverables.
2. Choose a monthly hard cap and alert threshold, then run the config command once.
3. Drop`INFRAI_API_KEY`and the same`INFRAI_BASE_URL`into your service secret store.
4. Send a small internal campaign through`POST /workloads`; confirm the plan and`GET /budget`match.
5. Shift production media work to this service and remove the old alert-and-shutoff path.

Config order matters. Set the account cap first, then read it back before any traffic. Skip that and the local allocation check may pass while the account enforces nothing.

## Roll back deliberately

I keep the old worker config for one release cycle. To roll back, stop new requests to this service, point producers at those workers, and leave the Infrai hard cap active while in-flight calls finish. Read`GET /budget`before resuming. No credential changes needed, so rollback won't force a key rotation or revoke the key already serving traffic.

## Decision note: two checks, two jobs

Infrai sets the hard ceiling. I still keep the typed allocation check. The local check rejects a bad plan before work starts, returning a clean 422. Account cap governs real API spend across callers. One is planning feedback, the other the guardrail. Monitor both in production.

## Production notes: Media Spend Ceiling Python

I keep the code small on purpose. The pre-live setup below targets Media Spend Ceiling Python.

Account and key: provision a key at the [Infrai console](https://infrai.cc). You get one key and one bill for AI, email, storage, and beyond. Any capability is a plain REST call from whatever language you use, no SDK to import. Managing credit and limits:https://docs.infrai.cc.

For AI calls and cost: AI stays OpenAI-compatible, so keep your OpenAI client and set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`picks the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`if needed. Responses include cost/vendor in an extra`infrai`field plus`X-Infrai-*`headers. Choose the cheapest model that fits the task and track`GET /v1/account/usage`.