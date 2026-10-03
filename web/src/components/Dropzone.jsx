import { useRef, useState } from 'react'
import { FileIcon, UploadIcon } from './icons.jsx'

const SHOWN = 6

// Styled drag-and-drop zone with hover + drag-active + selected states.
// Takes several files at once: each drop or browse adds to the selection.
export default function Dropzone({ files, onFiles, accept = '.txt,.pdf', disabled = false }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  function choose(list) {
    const picked = Array.from(list ?? [])
    if (picked.length) onFiles(picked)
  }

  const count = files.length
  const state = dragging
    ? 'border-brand bg-accent-weak shadow-[var(--shadow-glow)]'
    : count
      ? 'border-verified-line bg-verified-weak/60'
      : 'border-faint/50 bg-surface/70 backdrop-blur-lg hover:border-brand hover:bg-accent-weak/60'

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload documents"
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
        if (!disabled) choose(e.dataTransfer.files)
      }}
      className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-[var(--radius)] border border-dashed px-6 py-10 text-center transition-colors ${state} ${disabled ? 'pointer-events-none opacity-60' : ''}`}
    >
      <span
        className={`flex h-12 w-12 items-center justify-center rounded-full ${count ? 'border border-verified-line bg-verified-weak text-verified' : 'border border-accent-line bg-accent-weak text-accent'}`}
      >
        {count ? <FileIcon className="h-6 w-6" /> : <UploadIcon className="h-6 w-6" />}
      </span>
      {count ? (
        <div>
          <div className="text-sm font-medium text-ink">
            {count} file{count === 1 ? '' : 's'} selected
          </div>
          <div className="mt-1 font-mono text-xs leading-relaxed text-muted">
            {files.slice(0, SHOWN).map((f) => f.name).join(', ')}
            {count > SHOWN && ` and ${count - SHOWN} more`}
          </div>
          <div className="mt-1 text-xs text-muted">Click or drop to add more files</div>
        </div>
      ) : (
        <div>
          <div className="text-sm text-ink">
            Drop statutes here, or <span className="font-medium text-accent underline decoration-accent-line underline-offset-2">browse</span>
          </div>
          <div className="mt-1 text-xs text-muted">
            One or many .txt or .pdf files — statutes chunk by section, anything else by paragraph
          </div>
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple
        className="hidden"
        onChange={(e) => {
          choose(e.target.files)
          e.target.value = '' // lets the same file be picked again after a clear
        }}
      />
    </div>
  )
}
