import { useRef, useState } from 'react'
import { FileIcon, UploadIcon } from './icons.jsx'

// Styled drag-and-drop zone with hover + drag-active + selected states.
export default function Dropzone({ file, onFile, accept = '.txt,.pdf', disabled = false }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  function choose(f) {
    if (f) onFile(f)
  }

  const state = dragging
    ? 'border-brand bg-accent-weak shadow-[var(--shadow-glow)]'
    : file
      ? 'border-verified-line bg-verified-weak/60'
      : 'border-faint/50 bg-surface/70 backdrop-blur-lg hover:border-brand hover:bg-accent-weak/60'

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload a document"
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && !disabled && inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault()
        if (!disabled) setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        if (!disabled) choose(e.dataTransfer.files?.[0])
      }}
      className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-[var(--radius)] border border-dashed px-6 py-10 text-center transition-colors ${state} ${disabled ? 'pointer-events-none opacity-60' : ''}`}
    >
      <span
        className={`flex h-12 w-12 items-center justify-center rounded-full ${file ? 'border border-verified-line bg-verified-weak text-verified' : 'border border-accent-line bg-accent-weak text-accent'}`}
      >
        {file ? <FileIcon className="h-6 w-6" /> : <UploadIcon className="h-6 w-6" />}
      </span>
      {file ? (
        <div>
          <div className="font-mono text-sm text-ink">{file.name}</div>
          <div className="mt-1 text-xs text-muted">Click to choose a different file</div>
        </div>
      ) : (
        <div>
          <div className="text-sm text-ink">
            Drop a statute here, or <span className="font-medium text-accent underline decoration-accent-line underline-offset-2">browse</span>
          </div>
          <div className="mt-1 text-xs text-muted">.txt or .pdf — statutes chunk by section, anything else by paragraph</div>
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => choose(e.target.files?.[0] ?? null)}
      />
    </div>
  )
}
