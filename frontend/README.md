# Document Q&A — Frontend

React + TypeScript + Vite client for the Clickatell document Q&A assessment
backend. Upload a document, browse the document list, and ask questions
against the uploaded content.

## Setup

```
npm install
```

## Run (dev)

```
npm run dev
```

Starts the Vite dev server on `http://localhost:5173`. The dev server
proxies `/documents`, `/query`, and `/ask` requests to a backend running on
`http://localhost:8000` (see `vite.config.ts`'s `server.proxy`), so the
FastAPI backend must be running separately — the root `README.md` covers
how to start it. This proxy is a dev-only convenience that avoids needing
CORS configuration on the backend; it does not carry over to a production
build.

## Build

```
npm run build
```

Type-checks (`tsc -b`) then produces a static production bundle in `dist/`.

## Lint

```
npm run lint
```

Runs `oxlint` against `.oxlintrc.json`.
