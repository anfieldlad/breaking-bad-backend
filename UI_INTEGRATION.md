# UI Integration Guide: Breaking B.A.D.

This is the canonical API contract for frontends. The interactive OpenAPI
schema is served at `/docs` (Swagger UI) and `/openapi.json`.

## 1. Authentication & Base URL

- **Base URL**: `https://your-backend-host` (or `http://localhost:8000` locally).
- **`X-API-Key` header**: required on every `/api/*` endpoint.

> ⚠️ **Never ship the API key to the browser.** Anything in client-side
> JavaScript (e.g. a `NEXT_PUBLIC_*` variable) is public. Call the backend from
> your own server instead (a BFF / proxy route) and attach the key there.
> `breaking-bad-ui` does this with a Next.js route handler.

## 2. Endpoints

| Method | Path | Notes |
|---|---|---|
| `GET` | `/health` | No auth. |
| `POST` | `/api/ingest` | `multipart/form-data` with a `file` field (PDF). |
| `POST` | `/api/chat` | JSON body; responds with an SSE stream. |
| `GET` | `/api/documents/count` | `{"count": number}` |
| `DELETE` | `/api/documents` | `?filename=...` or `?all=true`, plus `X-Cleanup-Password`. |

Errors use the shape `{"detail": "message"}` with a meaningful HTTP status.
Show `detail` to the user rather than a generic message.

### A. Upload PDF (`/api/ingest`)

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('/api/ingest', { method: 'POST', body: formData });
if (!response.ok) {
  const { detail } = await response.json();
  throw new Error(detail);
}
const result = await response.json();
console.log(`${result.chunks_stored} pages processed.`);
```

### B. Streaming Chat (`/api/chat`)

Request body:

```json
{
  "question": "What is this document about?",
  "history": [
    { "role": "user", "parts": [{ "text": "Hi, I'm the owner." }] },
    { "role": "model", "parts": [{ "text": "Hello! I am Breaking B.A.D." }] }
  ]
}
```

The response is `text/event-stream`. Each event is a `data: <json>` line
followed by a blank line. Payload keys:

| Key | When | Meaning |
|---|---|---|
| `sources` | first event | Filenames used as context (may be empty). |
| `thought` | 0..n | Reasoning text, if the model exposes it. Append. |
| `answer` | 0..n | Answer text. Append. |
| `error` | last event, on failure | Generation failed mid-stream. The HTTP status is still 200, so this is the only failure signal once streaming has started. |

**Network chunks do not align with events** — one event can be split across
several `read()` calls. Buffer until you see the `\n\n` separator:

```javascript
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question, history }),
});
if (!response.ok || !response.body) {
  throw new Error(`Chat failed with HTTP ${response.status}`);
}

const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });

  let sep;
  while ((sep = buffer.indexOf('\n\n')) !== -1) {
    const frame = buffer.slice(0, sep);
    buffer = buffer.slice(sep + 2);
    for (const line of frame.split('\n')) {
      if (!line.startsWith('data: ')) continue;
      const data = JSON.parse(line.slice(6));
      if (data.sources) showSources(data.sources);
      if (data.thought) appendThought(data.thought);
      if (data.answer) appendAnswer(data.answer);
      if (data.error) showError(data.error);
    }
  }
}
```

### C. Cleanup (`DELETE /api/documents`)

Requires `X-Cleanup-Password` matching the server's `CLEANUP_PASSWORD`.
If the server has no `CLEANUP_PASSWORD` configured, the endpoint is disabled
and always returns `403`.

## 3. Branding & Theming: "Breaking B.A.D." 🧪

- **The Thinking**: "Cooking the data..." ⚗️ — show the `thought` stream in a
  glassmorphic container with a bubbling laboratory animation.
- **The Answer**: "The pure product." 💎 — use the "blue crystal" palette
  (#00D4FF) for the final response.
