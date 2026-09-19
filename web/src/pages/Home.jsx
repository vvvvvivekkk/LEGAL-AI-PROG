import { Link } from 'react-router-dom'
import Card, { CardHeader } from '../components/Card.jsx'
import { ShieldIcon } from '../components/icons.jsx'

// Placeholder landing — the animated hero + live stats land in a later step.
export default function Home() {
  return (
    <Card tone="input">
      <CardHeader
        icon={ShieldIcon}
        title="Legal AI"
        subtitle="Ask questions over indexed legal documents and get answers checked against their source."
      />
      <div className="flex gap-3">
        <Link to="/ask" className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white">
          Ask a question
        </Link>
        <Link to="/ingest" className="rounded-lg border border-line px-4 py-2 text-sm font-medium text-muted hover:text-ink">
          Add a document
        </Link>
      </div>
    </Card>
  )
}
