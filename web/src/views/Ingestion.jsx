import { useState } from 'react'
import { ingest } from '../api.js'

export default function Ingestion() {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  function pick(f) {
    setError(null)
    setFile(f)
  }

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f) pick(f)
  }

  async function submit() {
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      const data = await ingest(file)
      setResult(data)
    } catch (err) {
      setError(err.message)
      setResult(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="panel">
      <h2>Ingestion</h2>
      <p className="muted">
        Upload a statute (.txt or .pdf). It runs ingestion → SAC chunking → embedding → LanceDB append,
        then shows the new chunks and the running index totals.
      </p>

      <div
        className={dragging ? 'dropzone dragging' : 'dropzone'}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <p>{file ? file.name : 'Drag a .txt / .pdf here, or choose a file'}</p>
        <input
          type="file"
          accept=".txt,.pdf"
          onChange={(e) => pick(e.target.files?.[0] ?? null)}
        />
      </div>

      <button className="primary" disabled={!file || busy} onClick={submit}>
        {busy ? 'Ingesting…' : 'Ingest and index'}
      </button>

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="result">
          <div className="totals">
            <div className="metric">
              <span className="metric-value">{result.totals.chunks}</span>
              <span className="metric-label">indexed chunks</span>
            </div>
            <div className="metric">
              <span className="metric-value">{result.totals.documents}</span>
              <span className="metric-label">indexed documents</span>
            </div>
            <div className="metric">
              <span className="metric-value">{result.new_chunk_count}</span>
              <span className="metric-label">new from “{result.filename}”</span>
            </div>
          </div>

          <table className="chunks">
            <thead>
              <tr>
                <th>Chunk id</th>
                <th>Section</th>
                <th>Text</th>
              </tr>
            </thead>
            <tbody>
              {result.new_chunks.map((c) => (
                <tr key={c.chunk_id}>
                  <td className="mono">{c.chunk_id}</td>
                  <td>{c.metadata.section_ref || ''}</td>
                  <td>{c.text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
