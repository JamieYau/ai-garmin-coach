# AI Garmin Coach Demo Script

This five-minute walkthrough uses only the synthetic demo dataset. It never
requires Garmin credentials or real health data.

## Before recording

1. Start PostgreSQL, the backend, and the frontend using the commands in the
   README.
2. Sign in with the local demo account after running `npm run demo:seed`, or
   sign in with any local account and choose **Load demo data** on the Sources
   page.
3. Open the dashboard at a desktop viewport and make sure no real account data
   is visible.

## Walkthrough

### 0:00–0:25 — Frame the product

Show the landing page and say: “AI Garmin Coach turns normalized activity,
sleep, and recovery data into a focused daily coaching dashboard.”

### 0:25–1:05 — Show the credential-free demo path

Open **Sources**. Point out **Explore with demo data**, then choose **Load demo
data**. Explain that the records are deterministic synthetic data scoped to the
signed-in user, so the app can be evaluated without a Garmin account.

### 1:05–2:10 — Read the dashboard overview

Open **Overview**. Call out the seven-day activity totals, latest recovery
metrics, sleep summary, and the data-state banner identifying demo data. Keep
the explanation descriptive rather than prescriptive: the numbers are a
synthetic example, not medical advice.

### 2:10–3:05 — Inspect the training history

Open **Activities** and highlight the recent session list and its typed
activity fields. Then open **Recovery** to show the sleep and recovery trends.
Explain that the backend normalizes the provider payloads into connector-neutral
tables before the dashboard reads them.

### 3:05–4:10 — Explain the coach insight

Open **Coach**. Show the structured recommendation, its focus, and any risk
flags. Explain that deterministic metric summarization and safety checks happen
before the model call, and the response is validated against a Pydantic schema.

### 4:10–5:00 — Close with privacy and architecture

Open **Settings** and point out the data controls. Close on the architecture
diagram in the README: Better Auth protects browser/API calls, PostgreSQL owns
the user-scoped records, and scheduled jobs keep sync and daily insight work
outside the web request path.

## Recording notes

- Do not show passwords, API keys, database URLs, real Garmin data, or browser
  session cookies.
- If the demo-data action has already run, use **Refresh demo data**; it is
  safe to rerun.
- Keep the recording to product behavior and documented MVP boundaries; do not
  imply medical diagnosis, continuous real-time sync, or Garmin API guarantees.
