import Card, { CardHeader } from '../components/Card.jsx'
import { ShieldIcon } from '../components/icons.jsx'

// Placeholder — the chat interface with inline expandable proof lands next.
export default function Ask() {
  return (
    <Card tone="input">
      <CardHeader
        icon={ShieldIcon}
        title="Ask"
        subtitle="Chat interface with inline, expandable per-claim proof — coming in the next step."
      />
    </Card>
  )
}
