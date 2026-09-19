// Thin client over the FastAPI backend. Views import only from here — they
// never touch the pipeline directly. Override the base URL with VITE_API_BASE.
const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function unwrap(res, label) {
  if (!res.ok) {
    let detail = `${label} failed (${res.status})`
    try {
      const body = await res.json()
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }
  return res.json()
}

export async function ingest(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/ingest`, { method: 'POST', body: form })
  return unwrap(res, 'Ingest')
}

export async function retrieve(q, k = 5, rerank = false) {
  const params = new URLSearchParams({ q, k: String(k), rerank: String(rerank) })
  const res = await fetch(`${BASE}/retrieve?${params.toString()}`)
  return unwrap(res, 'Retrieve')
}

export async function query(payload) {
  const res = await fetch(`${BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return unwrap(res, 'Query')
}

export async function evaluation() {
  const res = await fetch(`${BASE}/evaluation`)
  return unwrap(res, 'Evaluation')
}
