# Orvix web client

React replacement for the Streamlit UI. It talks directly to the existing FastAPI and OpenAI-compatible routes; no backend files are changed.

## Run

1. Start the existing ChatChat API server (default: `http://127.0.0.1:7861`).
2. Copy `.env.example` to `.env` only if the API is not on the default address. In development, Vite proxies `/api` to `http://127.0.0.1:7861`.
3. In this directory run `npm install` and `npm run dev`.

Use `npm run build` to produce the deployable bundle in `dist/`.

The FastAPI server must allow the web client's origin via its existing CORS configuration when the app is hosted on a different origin.

## Included routes

- `/chat` — streamed OpenAI-compatible general chat, sessions and tools
- `/rag` — knowledge-base and search-engine chat
- `/knowledge-base` — create, upload, list, and delete knowledge-base documents
- `/mcp` — add, enable, disable, and delete MCP connections
- `/api-keys` — explains the existing server-managed key flow

Provider API keys deliberately remain server-managed. The Streamlit page wrote directly to `model_settings.yaml`; a browser cannot safely or legitimately do that without a new privileged backend endpoint, which this frontend-only migration intentionally does not introduce.
