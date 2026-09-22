import { useState } from 'react'
import { ingest } from '../api.js'
import Banner from '../components/Banner.jsx'
import Button from '../components/Button.jsx'
import Card, { CardHeader } from '../components/Card.jsx'
import Dropzone from '../components/Dropzone.jsx'
import { UploadIcon } from '../components/icons.jsx'

function Stat({ value, label }) {
  return (
    <div className="rounded-lg border border-line-soft bg-surface px-4 py-3 shadow-[var(--shadow-flat)]">
      <div className="font-mono text-2xl font-medium text-accent">{value}</div>
      <div className="mt-1 text-xs text-muted">{label}</div>
    </div>
  )
}

export default function Ingest() {
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  async function submit() {
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      setResult(await ingest(file))
    } catch (err) {
      setError({ message: err.message, status: err.status ?? null, kind: err.kind ?? 'http' })
      setResult(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card tone="input">
        <CardHeader
          icon={UploadIcon}
          title="Add a document to the index"
          subtitle="Ingestion → summary-augmented chunking → embedding → LanceDB. Statutes chunk by section; other documents fall back to paragraph chunking."
        />
        <Dropzone file={file} onFile={(f) => { setError(null); setFile(f) }} disabled={busy} />
        <div className="mt-4 flex justify-end">
          <Button onClick={submit} disabled={!file || busy}>
            {busy ? 'Indexing…' : 'Ingest and index'}
          </Button>
        </div>
      </Card>

      {error && (
        <Banner variant="error" title={error.message}>
          {error.kind === 'network'
            ? 'Nothing was indexed — the request never reached the API.'
            : error.status === 409
              ? 'This document is already in the index, so it was not added again.'
              : `Nothing was indexed. The API answered with HTTP ${error.status ?? '?'}${
                  error.status === 503 ? ' — the embedding model could not be loaded; check the backend log.' : '.'
                }`}
        </Banner>
      )}

      {result && (
        <div className="space-y-5">
          {result.used_fallback ? (
            <Banner variant="info" title="No legal structure detected">
              Used fallback paragraph chunking, so this document is still searchable.
            </Banner>
          ) : (
            <Banner variant="success" title="Indexed by legal structure">
              Parsed the Act/Chapter/Section hierarchy and indexed {result.new_chunk_count} chunks.
            </Banner>
          )}

          <div className="grid grid-cols-3 gap-3">
            <Stat value={result.totals.chunks} label="chunks indexed" />
            <Stat value={result.totals.documents} label="documents indexed" />
            <Stat value={result.new_chunk_count} label={`new from ${result.filename}`} />
          </div>

          <Card tone="flat" className="!p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs text-muted">
                  <th className="px-4 py-3 font-medium">Chunk</th>
                  <th className="px-4 py-3 font-medium">Reference</th>
                  <th className="px-4 py-3 font-medium">Text</th>
                </tr>
              </thead>
              <tbody>
                {result.new_chunks.map((c) => (
                  <tr key={c.chunk_id} className="border-b border-line-soft last:border-0 align-top">
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-accent">{c.chunk_id}</span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-muted">{c.metadata.section_ref || '—'}</td>
                    <td className="px-4 py-3 leading-relaxed text-ink/90">{c.text}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}
    </div>
  )
}
