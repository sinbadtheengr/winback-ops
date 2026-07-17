# Winback Ops — 3-Minute Demo Video

## Before recording

1. Set `DEMO_MODE=true` and `MOCK_SEND=true` in `.env`.
2. Regenerate fixtures: `python scripts/generate_sample_data.py`.
3. Run the backend on port 8000 and the frontend on port 3000.
4. Start from a fresh browser tab at `http://localhost:3000`.
5. Have `sample_data/clinic_adversarial.csv` ready in the file picker.

The adversarial fixture is the best recording choice: it uses a semicolon
delimiter, unusual headers, mixed date/currency formats, duplicate rows, and a
malformed date. Do not show real customer data or an API key.

## Recording script

### 0:00–0:20 — Problem

**Show:** The empty Winback Ops dashboard.

**Say:**

> Med spas have valuable clients who quietly stop booking. The problem is that
> the booking export needed to find them is messy and every clinic formats it
> differently. Winback Ops is an operator that turns that export into an
> approval-gated recovery workflow.

### 0:20–0:40 — Upload the messy export

**Show:** Select `clinic_adversarial.csv`, then click **Upload booking export**.
Pause on the detected headers and row count.

**Say:**

> I am uploading a deliberately hostile clinic export. It has a semicolon
> delimiter, descriptive column names, mixed dates and currencies, service
> aliases, duplicates, and even a bad record. The product stores the original
> CSV and first shows its raw shape rather than assuming a template.

### 0:40–1:10 — Profile the data

**Show:** Click **Profile this dataset** and scroll through the profile panel.
Point to the column mapping, service cadence, dormancy rules, and data quirks.

**Say:**

> The profiler identifies which columns represent the client, service, visit
> date, and payment. It also normalizes the clinic's treatment names into a
> service taxonomy and applies a different cadence for Botox, laser, facials,
> fillers, and microneedling. That matters because a 45-day laser cadence and a
> 180-day filler cadence should not be treated the same way.

### 1:10–1:55 — The engineering agent loop

**Show:** Click **Run sandboxed segmentation**. Keep the Agent activity panel
visible as Codegen and Sandbox complete.

**Say:**

> This is the core of Winback Ops. Rather than ask an AI to write generic
> marketing copy, it generates data-handling logic for this clinic's schema and
> runs it in a restricted sandbox. The output has a strict contract, the totals
> are checked against the emitted clients and segment revenue, and duplicate
> client memberships or invalid dates fail verification. If verification fails,
> the failed Sandbox attempt and a Codegen repair attempt are recorded here, up
> to three tries.

**Important recording note:** A clean fixture normally passes on the first
attempt. Do not fabricate a failure for the video. If a genuine repair occurs,
show it; otherwise show the completed Codegen and Sandbox entries and explain
the visible retry policy.

### 1:55–2:20 — Revenue board

**Show:** The **Verified segmentation** card with dormant-client count,
recoverable revenue, and number of segments.

**Say:**

> The result is not an abstract score. It gives the clinic a concrete list of
> dormant clients grouped by treatment and lateness, plus a conservative
> recoverable-revenue projection based on the average ticket and expected return
> rate for each bucket.

### 2:20–2:45 — Campaigns and approval

**Show:** Click **Draft win-back campaigns**, then show a segment's subject,
body, recipient count, and projected revenue. Click **Approve & mock send** for
one draft.

**Say:**

> Each segment receives a tailored draft and a projected dollar outcome. It is
> still a draft: nothing sends without an explicit human approval. This demo
> uses a mock send so the safety gate is visible without contacting anyone.

### 2:45–3:00 — Close

**Show:** The approved campaign plus the completed Agent activity entries.

**Say:**

> Winback Ops is built for one concrete workflow: turn a messy booking export
> into a safe, explainable win-back queue. The agent does the data engineering
> first, so a human can confidently decide what to send next.

## Capture checklist

- Record at 1080p or higher with browser zoom at 100%.
- Keep the browser's developer tools, API key, and terminal output off screen.
- Use the local deterministic demo mode for repeatability.
- Capture one clean full-flow take and one backup take focused on Agent activity.
- Add the final video URL to the Devpost submission before the deadline.
