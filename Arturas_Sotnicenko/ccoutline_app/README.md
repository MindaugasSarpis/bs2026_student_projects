# CCOUTLINE App

Plain static exported-data website for `ccoutline.com`.

The current frontend baseline is a one-page, chart-first country browser:
- countries render in staged export order from `/data/countries.json`
- each country section includes a glossary plus collapsible per-indicator disclosures
- each indicator disclosure opens to a D3-backed yearly chart first
- raw yearly rows stay available as secondary detail inside a nested disclosure

## Build

Build the app shell and stage the canonical site-export contract into `/data`:

```bash
python scripts/build_ccoutline_app.py
```

If the canonical export root is not present yet, you can still build the shell with placeholder data:

```bash
python scripts/build_ccoutline_app.py --allow-missing-data
```

Run the full publish flow from typed analysis through export, publication staging, and final app build:

```bash
python scripts/publish_ccoutline_site.py
```

## Local Preview

For a real local preview, publish the exports first and then serve the built app:

```bash
python scripts/publish_ccoutline_site.py
python scripts/validate_ccoutline_publication.py
python scripts/validate_ccoutline_publication.py --built-data-root ccoutline_app/dist/data
npx -y firebase-tools serve --only hosting --project landing-ccoutline-com --host 0.0.0.0 --port 5000
```

Then open `http://127.0.0.1:5000`.

Important:
- `python scripts/build_ccoutline_app.py --allow-missing-data` is only for shell validation and may show an empty placeholder state.
- The one-page site reads staged files from `/data`, so a real preview depends on the publish flow having produced `generated/ccoutline_site/data` first.
- `python scripts/validate_ccoutline_publication.py` is the publication-readiness guardrail for staged and built site data. Use it before preview or deploy.

For the full Firebase deploy and custom-domain checklist, see:
- [`docs/CCOUTLINE_DEPLOYMENT_RUNBOOK.md`](/workspaces/da-ai-v2/docs/CCOUTLINE_DEPLOYMENT_RUNBOOK.md)

## Hosting

- Firebase Hosting public root: `ccoutline_app/dist`
- SPA rewrite target: `index.html`

## Source Structure

- [`main.js`](/workspaces/da-ai-v2/ccoutline_app/src/main.js) is the thin bootstrap and composition root
- [`src/app/data/`](/workspaces/da-ai-v2/ccoutline_app/src/app/data) owns staged-site data loading
- [`src/app/legal/`](/workspaces/da-ai-v2/ccoutline_app/src/app/legal) defines the standalone privacy, cookie, and manage-cookies routes
- [`src/app/state/`](/workspaces/da-ai-v2/ccoutline_app/src/app/state) owns the Redux Toolkit store, slices, selector factories, and disclosure key helpers
- [`src/app/view-models/`](/workspaces/da-ai-v2/ccoutline_app/src/app/view-models) shapes country and indicator render models
- [`src/app/rendering/`](/workspaces/da-ai-v2/ccoutline_app/src/app/rendering) owns page and disclosure rendering
- [`src/app/charts/`](/workspaces/da-ai-v2/ccoutline_app/src/app/charts) contains the chart facade plus the D3-backed indicator adapter
- [`src/app/shared/`](/workspaces/da-ai-v2/ccoutline_app/src/app/shared) holds shared formatting and DOM helpers

## State Architecture

- One app-wide Redux Toolkit store owns bootstrap state, staged country payloads, analytics control state, and UI disclosure state.
- Selector factories derive country analytics state and country-local UI view models from Redux-owned inputs rather than persisting recomputed analytics rows in the store.
- The frontend remains static-site and import-map delivered. React migration, bundler adoption, and broader frontend-platform redesign remain deferred outside this tranche.

## Validation

- `node --test ccoutline_app/tests/*.mjs` is the primary regression lane for Redux slice behavior, selector memoization, and renderer contracts.
- `python scripts/build_ccoutline_app.py --allow-missing-data` is the lightweight shell-validation pass when you need to confirm the static app still stages and builds without full published exports.

## Page Contract

- `/`
  - one long-scroll page
  - countries rendered in staged export order
  - plain country header plus glossary block per country
  - compact collapsible indicator disclosures per indicator
  - chart-first expanded indicator body with raw rows as secondary detail
- `/privacy/`, `/cookies/`, `/manage-cookies/`
  - standalone legal surfaces rendered through the same SPA entrypoint
  - shared footer navigation across the main app and legal pages
  - no staged country-data bootstrap on legal-only routes
