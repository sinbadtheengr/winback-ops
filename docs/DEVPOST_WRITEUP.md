# Winback Ops — Devpost Draft

Replace bracketed placeholders before submitting.

## Project name

Winback Ops

## Tagline

An agentic revenue-recovery operator that turns messy med-spa booking exports
into verified, approval-gated win-back campaigns.

## Inspiration

Med spas often have a valuable but invisible source of growth: customers who
were regular visitors and then quietly stopped booking. The data to find them
already exists, but it lives in inconsistent CSV exports. One clinic uses split
names and dollar-formatted prices; another uses service aliases, duplicate rows,
or mixed date formats. Generic dashboards expect clean data, and generic AI copy
does not solve the data-engineering problem that comes first.

Winback Ops reverses that order. It first interprets the booking data, then
calculates recoverable revenue, and only then drafts a human-approved outreach
sequence.

## What it does

1. Uploads and safely stores a clinic booking CSV.
2. Profiles the raw schema and maps customer, service, date, and payment fields.
3. Normalizes service aliases and applies service-specific treatment cadences.
4. Generates and sandbox-runs a dataset-specific segmentation routine.
5. Verifies the output contract, segment totals, revenue totals, dates, and
   duplicate client memberships; failed runs can retry through a visible repair
   loop up to three times.
6. Shows dormant-client counts, recoverable-revenue projections, and
   per-segment win-back drafts.
7. Requires explicit approval before a mocked email send.

## How we built it

The dashboard is Next.js with the App Router and TypeScript. The backend is
FastAPI with SQLite for uploaded-dataset state, profiles, segmentations,
campaigns, and an agent run log. The dashboard consumes run updates over
server-sent events so the workflow is visible rather than a black box.

The OpenAI product path uses GPT-5.6 structured output for dataset profiling.
For repeatable local demonstration and testing without API billing, the project
also includes a clearly labelled deterministic demo mode. That mode runs the
same upload, sandbox, verification, repair orchestration, revenue, and approval
workflow against seeded fixtures; it does not make an OpenAI API call.

Generated segmentation code runs in a subprocess with a 30-second timeout and
an import allowlist. The result is parsed into a strict Pydantic schema and then
checked for internally consistent client and revenue totals. The fourth seeded
fixture deliberately includes a semicolon delimiter, unconventional headers,
mixed currency/date formats, service aliases, duplicates, and an invalid row.

## Challenges we ran into

The difficult part was not producing a campaign body. It was safely making a
messy, unfamiliar export usable. We had to handle different delimiters, column
names, compact service aliases, duplicate visit rows, currency strings, and
invalid dates while maintaining a stable output contract for the revenue board.

The second challenge was making agent behavior inspectable. We added durable run
logging, SSE status updates, sandbox restrictions, validation checks, and a
bounded repair policy so users can see what happened and why.

## Accomplishments we are proud of

- A complete upload → analysis → revenue → approval flow, not a chat wrapper.
- Dataset-specific segmentation that handles four intentionally different
  clinic-export shapes.
- A restricted execution path with validation and visible repair attempts.
- Revenue presented as actionable segments and conservative projected dollars.
- Human approval as a hard gate before the mock send.

## What we learned

Reliable agentic workflows need both flexibility and constraints. The agent can
adapt to a clinic's schema, but the execution environment, output schema,
verification rules, retry limit, and human approval boundary must be explicit.
For operational tools, observability is a feature: the run log is as important
as the final campaign draft.

## What's next

- Complete the live GPT-5.6 path for code generation, repair, and campaign
  drafting once API billing is enabled.
- Expand validation with real clinician-reviewed holdout assertions.
- Add a production email provider behind the existing approval gate.
- Validate cadence and recovery assumptions with real, consented clinic data.

## Built with

- OpenAI GPT-5.6 / Responses API
- FastAPI
- Next.js
- TypeScript
- Python
- Pydantic
- SQLite
- pandas

## Submission checklist

- [ ] Add the deployed URL or local-demo instructions.
- [ ] Add the 3-minute video URL: `[VIDEO URL]`.
- [ ] Add 3–5 screenshots: empty state, schema profile, Agent activity,
  verified segmentation, and approval-gated campaign draft.
- [ ] Add repository URL: `[REPOSITORY URL]`.
- [ ] Confirm all claims above match the submitted demo mode and source code.
- [ ] Submit at least six hours before the stated deadline.
