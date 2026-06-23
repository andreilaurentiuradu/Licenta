import { useState } from 'react'

/**
 * Groups history entries into time buckets (Today / This week / This month /
 * Last 3 months / Older) and shows them as collapsible sections, in the style
 * of the Support page. All sections start collapsed; they open on click.
 *
 * Date filtering (from/to) stays in the parent page — this component only
 * groups and renders the already-loaded list.
 *
 * props:
 *   entries  – array of objects with a `date` field (ISO "YYYY-MM-DD") and `id`
 *   children – function (subsetEntries) => JSX, renders one section's content
 */

const BUCKETS = [
  { key: 'today', label: 'Today' },
  { key: 'week',  label: 'This week' },
  { key: 'month', label: 'This month' },
  { key: 'q',     label: 'Last 3 months' },
  { key: 'older', label: 'Older' },
]

function bucketIndex(dateStr) {
  if (!dateStr) return 4
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const d = new Date(`${dateStr}T00:00:00`)
  if (Number.isNaN(d.getTime())) return 4
  const diff = Math.floor((today - d) / 86400000) // whole days
  if (diff <= 0)  return 0   // today (or future)
  if (diff <= 7)  return 1   // this week
  if (diff <= 30) return 2   // this month
  if (diff <= 90) return 3   // last 3 months
  return 4                   // older
}

export default function HistoryAccordion({ entries, children }) {
  // null = all sections collapsed on page load; they open on click
  const [open, setOpen] = useState(null)

  if (!entries || entries.length === 0) return null

  const groups = [[], [], [], [], []]
  for (const e of entries) groups[bucketIndex(e.date)].push(e)

  const sections = BUCKETS
    .map((b, i) => ({ ...b, items: groups[i] }))
    .filter((s) => s.items.length > 0)

  return (
    <div className="space-y-2">
      {sections.map((s) => {
        const isOpen = open === s.key
        return (
          <div key={s.key} className="rounded-2xl bg-white/8 border border-white/10 overflow-hidden">
            <button
              type="button"
              onClick={() => setOpen(isOpen ? null : s.key)}
              className="w-full flex items-center justify-between px-5 py-4 hover:bg-white/12 transition-colors"
            >
              <span className="text-sm font-medium text-white">
                {s.label}
                <span className="ml-2 text-xs text-white/40">({s.items.length})</span>
              </span>
              <span
                className="text-white/40 text-lg ml-4 shrink-0"
                style={{ transform: isOpen ? 'rotate(45deg)' : 'none', transition: 'transform 0.2s' }}
              >
                +
              </span>
            </button>
            {isOpen && <div className="px-3 pb-3">{children(s.items)}</div>}
          </div>
        )
      })}
    </div>
  )
}
