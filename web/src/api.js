// Thin client over the FastAPI backend. Views import only from here — they
// never touch the pipeline directly. Override the base URL with VITE_API_BASE.
const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

// Every failure surfaces as an ApiError with the backend's real `detail`
// string (or a concrete network explanation) — never a bare "Failed to fetch".
export class ApiError extends Error {
  constructor(message, { status = null, kind = 'http', info = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.kind = kind // 'http' (server answered) | 'network' (never reached it)
    this.info = info // structured `detail` object, when the route sent one
  }
}

async function request(path, init, label) {
  let res
  try {
    res = await fetch(`${BASE}${path}`, init)
  } catch (err) {
    // fetch() only rejects when no HTTP response arrived at all: server down,
    // wrong port, or a response the browser refused (CORS).
    throw new ApiError(
      `Could not reach the Legal AI backend at ${BASE} — is \`uvicorn src.api.main:app\` running? (${err.message})`,
      { kind: 'network' },
    )
  }
  if (!res.ok) {
    let detail = `${label} failed with HTTP ${res.status}`
    let info = null
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') {
        detail = body.detail
      } else if (body.detail && typeof body.detail === 'object') {
        info = body.detail
        detail = info.message || JSON.stringify(body.detail)
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, { status: res.status, info })
  }
  return res.json()
}

export async function ingest(file) {
  const form = new FormData()
  form.append('file', file)
  return request('/ingest', { method: 'POST', body: form }, 'Ingest')
}

export async function deleteDocument(sourceId) {
  return request(`/documents/${encodeURIComponent(sourceId)}`, { method: 'DELETE' }, 'Delete document')
}

export async function retrieve(q, k = 5, rerank = false) {
  const params = new URLSearchParams({ q, k: String(k), rerank: String(rerank) })
  return request(`/retrieve?${params.toString()}`, undefined, 'Retrieve')
}

export async function query(payload) {
  return request(
    '/query',
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) },
    'Query',
  )
}

// --- Chat history -------------------------------------------------------
export async function listChats() {
  return request('/chats', undefined, 'List chats')
}

export async function createChat() {
  return request(
    '/chats',
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' },
    'Create chat',
  )
}

export async function getChat(id) {
  return request(`/chats/${encodeURIComponent(id)}`, undefined, 'Open chat')
}

export async function appendMessage(id, message) {
  return request(
    `/chats/${encodeURIComponent(id)}/messages`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(message) },
    'Save message',
  )
}

export async function deleteChat(id) {
  return request(`/chats/${encodeURIComponent(id)}`, { method: 'DELETE' }, 'Delete chat')
}

export async function evaluation() {
  return request('/evaluation', undefined, 'Evaluation')
}

export async function stats() {
  return request('/stats', undefined, 'Stats')
}

export async function embeddingMap() {
  return request('/embedding-map', undefined, 'Embedding map')
}
