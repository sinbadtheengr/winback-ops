# Frontend — init on Day 1

Not scaffolded yet (keeps the repo light). First Claude Code session, run:

```bash
npx create-next-app@latest . --typescript --tailwind --app --eslint --no-src-dir --import-alias "@/*"
npm i lucide-react
```

Then build the four-panel flow per `docs/PLAN.md` Day 5:
Upload → Analysis (profile + live codegen/repair stream via SSE) → Revenue board → Approve & send.
API base: `http://localhost:8000`.
