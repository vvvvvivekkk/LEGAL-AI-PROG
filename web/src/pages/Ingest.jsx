import { Fragment, useRef, useState } from 'react'
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

// Each file's outcome has its own label, so the state never rests on colour alone.
const STATUS = {
  pending: { label: 'Waiting', cls: 'border-line bg-surface text-muted' },
  indexing: { label: 'Indexing…', cls: 'border-accent-line bg-accent-weak text-accent' },
  indexed: { label: 'Indexed', cls: 'border-verified-line bg-verified-weak text-verified' },
  duplicate: { label: 'Already indexed', cls: 'border-caution-line bg-caution-weak text-caution' },
  failed: { label: 'Failed', cls: 'border-danger-line bg-danger-weak text-danger' },
}

function StatusBadge({ status }) {
  const s = STATUS[status]
  return (
    <span className={`inline-flex whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium ${s.cls}`}>
      {s.label}
    </span>
  )
}

function ChunkTable({ chunks }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-line bg-surface text-left text-xs text-muted">
          <th className="px-4 py-3 font-medium">Chunk</th>
          <th className="px-4 py-3 font-medium">Reference</th>
          <th className="px-4 py-3 font-medium">Text</th>
        </tr>
      </thead>
      <tbody>
        {chunks.map((c) => (
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
  )
}

export default function Ingest() {
  // One entry per selected file: { key, file, status, result, error }.
  const [items, setItems] = useState([])
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(null)
  const [networkError, setNetworkError] = useState(null)
  const [totals, setTotals] = useState(null)
  const [open, setOpen] = useState(null)
  const nextKey = useRef(0)

  const update = (key, patch) => setItems((all) => all.map((it) => (it.key === key ? { ...it, ...patch } : it)))

  // New picks join the waiting files; a pick with the name of a file already
  // in the list replaces that entry, so re-adding a file retries it.
  function addFiles(picked) {
    setNetworkError(null)
    setItems((all) => {
      const names = new Set(picked.map((f) => f.name))
      const kept = all.filter((it) => !names.has(it.file.name))
      const added = picked.map((file) => ({ key: nextKey.current++, file, status: 'pending', result: null, error: null }))
      return [...kept, ...added]
    })
  }

  // Ingest one file; returns false only when the API could not be reached at all.
  async function ingestOne(item) {
    update(item.key, { status: 'indexing', error: null })
    try {
      const result = await ingest(item.file)
      update(item.key, { status: 'indexed', result })
      setTotals(result.totals)
      return result
    } catch (err) {
      if (err.kind === 'network') {
        update(item.key, { status: 'pending' })
        setNetworkError(err.message)
        return false
      }
      update(item.key, {
        status: err.status === 409 ? 'duplicate' : 'failed',
        error: { message: err.message, status: err.status ?? null, info: err.info ?? null },
      })
      return null
    }
  }

  // Files go one at a time so each gets its own duplicate check and the index
  // never takes two writes at once.
  async function runQueue(queue, before) {
    setBusy(true)
    setNetworkError(null)
    let firstIndexed = null
    for (let i = 0; i < queue.length; i++) {
      setProgress({ done: i, total: queue.length, name: queue[i].file.name })
      if (before) {
        const ready = await before(queue[i])
        if (ready === 'stop') break
        if (!ready) continue
      }
      const outcome = await ingestOne(queue[i])
      if (outcome === false) break
      if (outcome && firstIndexed === null) firstIndexed = queue[i].key
    }
    setProgress(null)
    setBusy(false)
    if (queue.length === 1 && firstIndexed !== null) setOpen(firstIndexed)
  }

  const submit = () => runQueue(items.filter((it) => it.status === 'pending'))

  // Duplicate: drop the indexed copy first, then ingest the upload again.
  // Returns 'stop' when the API is unreachable, so the batch halts.
  async function removeExisting(item) {
    const sourceId = item.error?.info?.duplicate_source_id
    if (!sourceId) return false
    try {
      const removed = await deleteDocument(sourceId)
      setTotals(removed.totals)
      return true
    } catch (err) {
      if (err.kind === 'network') {
        setNetworkError(err.message)
        return 'stop'
      }
      update(item.key, {
        status: 'failed',
        error: { message: `Could not remove '${sourceId}': ${err.message}`, status: err.status ?? null, info: null },
      })
      return false
    }
  }

  const replace = (targets) => runQueue(targets, removeExisting)

  function clear() {
    setItems([])
    setOpen(null)
    setNetworkError(null)
  }

  const count = (s) => items.filter((it) => it.status === s).length
  const pending = count('pending')
  const indexed = items.filter((it) => it.status === 'indexed')
  const duplicates = items.filter((it) => it.status === 'duplicate' && it.error?.info?.duplicate_source_id)
  const failed = count('failed')
  const newChunks = indexed.reduce((n, it) => n + it.result.new_chunk_count, 0)
  const byParagraph = indexed.filter((it) => it.result.used_fallback).length
  const settled = items.length > 0 && !busy && pending === 0

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ingest"
        subtitle="Add documents to the index so they can be searched and cited."
      />
      <Card tone="input">
        <CardHeader
          icon={UploadIcon}
          title="Add documents to the index"
          subtitle="Ingestion → summary-augmented chunking → embedding → LanceDB. Statutes chunk by section; other documents fall back to paragraph chunking. Select one file or many."
        />
        <Dropzone
          files={items.filter((it) => it.status === 'pending').map((it) => it.file)}
          onFiles={addFiles}
          disabled={busy}
        />
        <div className="mt-4 flex items-center justify-between gap-3">
          <div>
            {items.length > 0 && (
              <Button variant="ghost" onClick={clear} disabled={busy}>
                Clear list
              </Button>
            )}
          </div>
          <Button onClick={submit} disabled={!pending || busy}>
            {busy
              ? 'Indexing…'
              : pending > 1
                ? `Ingest and index ${pending} files`
                : 'Ingest and index'}
          </Button>
        </div>
        {progress && (
          <div className="mt-4" aria-live="polite">
            <div className="flex justify-between text-xs text-muted">
              <span className="truncate font-mono">{progress.name}</span>
              <span className="shrink-0 pl-3">
                {progress.done + 1} of {progress.total}
              </span>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-raised">
              <div
                className="h-full rounded-full bg-brand transition-[width] duration-300"
                style={{ width: `${(progress.done / progress.total) * 100}%` }}
              />
            </div>
          </div>
        )}
      </Card>

      {networkError && (
        <Banner variant="error" title={networkError}>
          The request never reached the API, so the remaining files were not sent. Start the backend and press
          Ingest again; files already indexed stay indexed.
        </Banner>
      )}

      {settled && (indexed.length > 0 || duplicates.length > 0 || failed > 0) && (
        failed > 0 ? (
          <Banner variant="error" title={`${failed} file${failed === 1 ? '' : 's'} could not be indexed`}>
            The reason is shown next to each file below. The other files were processed normally.
          </Banner>
        ) : duplicates.length > 0 ? (
          <Banner
            variant="caution"
            title={`${duplicates.length} file${duplicates.length === 1 ? ' is' : 's are'} already in the index`}
          >
            {indexed.length > 0 && `Indexed ${indexed.length} file${indexed.length === 1 ? '' : 's'} (${newChunks} new chunks). `}
            Duplicates were not added again. Use Replace to remove the indexed copy and index the upload in its place.
          </Banner>
        ) : indexed.length === 1 && indexed[0].result.used_fallback ? (
          <Banner variant="info" title="No legal structure detected">
            Used fallback paragraph chunking, so this document is still searchable.
          </Banner>
        ) : (
          <Banner
            variant="success"
            title={
              indexed.length === 1
                ? 'Indexed by legal structure'
                : `Indexed ${indexed.length} documents`
            }
          >
            {indexed.length === 1
              ? `Parsed the Act/Chapter/Section hierarchy and indexed ${newChunks} chunks.`
              : `Added ${newChunks} chunks. ${
                  byParagraph === 0
                    ? 'Every file was chunked by section.'
                    : `${indexed.length - byParagraph} chunked by section, ${byParagraph} by paragraph (no legal structure found).`
                }`}
          </Banner>
        )
      )}

      {totals && (
        <div className="grid grid-cols-3 gap-3">
          <Stat value={totals.chunks} label="chunks indexed" />
          <Stat value={totals.documents} label="documents indexed" />
          <Stat value={newChunks} label={indexed.length === 1 ? `new from ${indexed[0].file.name}` : 'new chunks added'} />
        </div>
      )}

      {items.length > 0 && (
        <Card tone="flat" className="!p-0 overflow-hidden">
          <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
            <div className="text-sm font-medium text-ink">
              {items.length} file{items.length === 1 ? '' : 's'}
              <span className="ml-2 font-normal text-muted">
                {[
                  indexed.length && `${indexed.length} indexed`,
                  duplicates.length && `${duplicates.length} already indexed`,
                  failed && `${failed} failed`,
                  pending && `${pending} waiting`,
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </span>
            </div>
            {duplicates.length > 1 && (
              <Button variant="ghost" onClick={() => replace(duplicates)} disabled={busy}>
                Replace all {duplicates.length}
              </Button>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line bg-surface text-left text-xs text-muted">
                  <th className="px-4 py-3 font-medium">File</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 text-right font-medium">Chunks</th>
                  <th className="px-4 py-3 font-medium">Chunking</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <Fragment key={it.key}>
                    <tr className="border-b border-line-soft align-top last:border-0">
                      <td className="px-4 py-3">
                        <div className="font-mono text-xs text-ink">{it.file.name}</div>
                        {it.error && <div className="mt-1 max-w-md text-xs leading-relaxed text-muted">{it.error.message}</div>}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={it.status} />
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-ink">
                        {it.result?.new_chunk_count ?? it.error?.info?.duplicate_chunk_count ?? '—'}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-xs text-muted">
                        {it.result ? (it.result.used_fallback ? 'By paragraph' : 'By section') : '—'}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right">
                        {it.status === 'indexed' && (
                          <button
                            className="text-xs font-medium text-accent underline decoration-accent-line underline-offset-2 hover:text-primary-hover"
                            onClick={() => setOpen(open === it.key ? null : it.key)}
                          >
                            {open === it.key ? 'Hide chunks' : 'Show chunks'}
                          </button>
                        )}
                        {it.status === 'duplicate' && it.error?.info?.duplicate_source_id && (
                          <button
                            className="text-xs font-medium text-accent underline decoration-accent-line underline-offset-2 hover:text-primary-hover disabled:opacity-50"
                            onClick={() => replace([it])}
                            disabled={busy}
                            title={`Removes the ${it.error.info.duplicate_chunk_count} indexed chunks of '${it.error.info.duplicate_source_id}', then indexes this upload in its place.`}
                          >
                            Replace
                          </button>
                        )}
                      </td>
                    </tr>
                    {open === it.key && it.result && (
                      <tr className="border-b border-line-soft">
                        <td colSpan={5} className="bg-surface/60 p-0">
                          <ChunkTable chunks={it.result.new_chunks} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
