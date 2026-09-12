# Claim Review Interface

Next.js 16 front end for the openIMIS claim fraud and rejection scoring service. An adjudicator
enters a claim (or pastes an openIMIS JSON payload), and the page returns the calibrated risk score,
the recommended action, and the TreeSHAP factors behind it.

## Running

The scoring service must be running first — see the [repository README](../../README.md):

```bash
cd ../backend
uvicorn service.app:app --host 0.0.0.0 --port 8000
```

Then:

```bash
npm install
npm run dev
```

Open <http://localhost:3000>.

Requests go to `http://127.0.0.1:8000` directly and fall back to the `/api/proxy/*` rewrite defined
in [`next.config.ts`](next.config.ts), so the page works with or without the proxy. The header polls
`/health` every five seconds and shows service status, test ROC-AUC, the alert cutoff, and the
feature count.

## Structure

```text
app/
├── page.tsx                    # Layout, scoring request, form/JSON tab state
├── layout.tsx                  # Document shell and metadata
├── globals.css                 # Design tokens and all component styling
├── types.ts                    # Request/response contracts shared with the service
└── components/
    ├── Header.tsx              # Masthead with live service health
    ├── Presets.tsx             # Sample claim loaders
    ├── ClaimForm.tsx           # Structured claim entry, advanced inputs collapsed
    ├── JsonUploader.tsx        # Drop / paste a raw claim payload
    ├── ResultsDashboard.tsx    # Score, risk scale against the cutoff, recommendation
    └── ShapExplainer.tsx       # What raised and lowered the score

sample_claims/                  # Routine, suspicious, and high-cost demo payloads
```

## Styling

There is no CSS framework. [`app/globals.css`](app/globals.css) defines the whole design system as
custom properties: one neutral scale, a single accent used for focus rings, and three muted signal
colours reserved for risk meaning. Layout uses hairline borders rather than shadows, and form fields
pack densely so a wider window means fewer rows rather than more empty space.

## Scripts

| Command | Purpose |
| :--- | :--- |
| `npm run dev` | Development server on port 3000 |
| `npm run build` | Production build |
| `npm start` | Serve the production build |
