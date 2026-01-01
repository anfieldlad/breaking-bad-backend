# UI Integration Guide: Breaking B.A.D.

This guide explains how to connect a frontend application to the Breaking B.A.D. backend.

## 1. App Architecture & Layout
For the best user experience, we recommend a **two-page structure**:

1.  **Data Management Page (`/ingest`)**:
    -   A dedicated space for users to upload and view processed documents.
    -   Features a drag-and-drop file uploader.
2.  **Chat Interface (`/chat`)**:
    -   A clean, distraction-free chat UI.
    -   Displays the streaming reasoning ("Thinking") and the final response.

## 2. Authentication & Base URL
- **Base URL**: `https://your-render-app-url.com` (or `http://localhost:8000` for local development)
- **Headers**: No specific auth required for MVP, but ensure `Content-Type: application/json` for chat requests.

## 2. API Endpoints

### A. Upload PDF (`/api/ingest`)
Use a standard multipart/form-data POST request.

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('/api/ingest', {
  method: 'POST',
  body: formData
});
const result = await response.json();
console.log(result.chunks_stored + " pages processed.");
```

### B. Streaming Chat (`/api/chat`)
This endpoint uses **Server-Sent Events (SSE)**. You must handle a stream of JSON chunks.

#### Using `fetch` with `ReadableStream` (Recommended)
```javascript
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: "What is this document about?" })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value, { stream: true });
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      
      // Handle different data types:
      if (data.sources) {
        console.log("Sources:", data.sources);
      }
      if (data.thought) {
        // Append to "Thinking..." UI section
        updateThoughtUI(data.thought);
      }
      if (data.answer) {
        // Append to final answer UI section
        updateAnswerUI(data.answer);
      }
    }
  }
}
```

## 4. Branding & Theming: "Breaking B.A.D." 🧪
This structure fits the theme perfectly:

- **The Thinking**: "Cooking the data..." ⚗️
  - *Recommendation*: Show the `thought` stream inside a glassmorphic container with a bubbling laboratory animation.
- **The Answer**: "The pure product." 💎
  - *Recommendation*: Use a "blue crystal" color palette (#00D4FF) for the final response text to give it that premium, high-quality feel.

## 5. Integration Examples
For a React implementation, check out `react-use-event-source` or simply use the `fetch` stream logic within a `useEffect` or an event handler.
