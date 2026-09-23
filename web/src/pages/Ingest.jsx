import { useState } from 'react'
import { deleteDocument, ingest } from '../api.js'
import Banner from '../components/Banner.jsx'
import Button from '../components/Button.jsx'
import Card, { CardHeader, PageHeader } from '../components/Card.jsx'
import Dropzone from '../components/Dropzone.jsx'
import { UploadIcon } from '../components/icons.jsx'

function Stat({ value, label }) {
  return (
    <div className="group rounded-xl border border-line bg-white px-4 py-3 shadow-[var(--shadow-card)] transition-[border-color,transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:border-accent-line">
      <div className="font-mono text-2xl font-medium text-accent">{value}</div>
      <div className="mt-1 text-xs text-muted transition-colors group-hover:text-ink">{label}</div>
    </div>
  )
}

export default function Ingest() {
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  async function runIngest() {
    setBusy(true)
    setError(null)
    try {
      setResult(await ingest(file))
      return true
    } catch (err) {
      setError({
        message: err.message,
        status: err.status ?? null,
        kind: err.kind ?? 'http',
        info: err.info ?? null,
      })
      setResult(null)
      return false
    } finally {
      setBusy(false)
    }
  }

  async function submit() {
    if (!file) return
    await runIngest()
  }

  // Duplicate hit: drop the indexed copy first, then ingest the upload again.
  async function replace() {
    const sourceId = error?.info?.duplicate_source_id
    if (!file || !sourceId) return
    setBusy(true)
    try {
      await deleteDocument(sourceId)
    } catch (err) {
      setError({
        message: `Could not remove '${sourceId}': ${err.message}`,
        status: err.status ?? null,
        kind: err.kind ?? 'http',
        info: null,
      })
      setBusy(false)
      return
    }
    setBusy(false)
    await runIngest()
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ingest"
        subtitle="Add documents to the index so they can be searched and cited."
      />
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
          {error.info?.duplicate_source_id && (
            <div className="mt-3">
              <Button onClick={replace} disabled={busy}>
                {busy ? 'Replacing…' : `Replace existing document`}
              </Button>
              <p className="mt-2 text-xs text-muted">
                Removes the {error.info.duplicate_chunk_count} indexed chunk
                {error.info.duplicate_chunk_count === 1 ? '' : 's'} of
                {' '}&lsquo;{error.info.duplicate_source_id}&rsquo;, then indexes this upload in its place.
              </p>
            </div>
          )}
        </Banner>
      )}

      {result && (
        <div className="space-y-6">
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
                <tr className="border-b border-line bg-surface text-left text-xs text-muted">
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
                    <td className="px-4 py-3 leading-relaxed text-ink">{c.text}</td>
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
