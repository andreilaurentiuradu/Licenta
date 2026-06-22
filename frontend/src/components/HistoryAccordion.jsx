import { useState } from 'react'

/**
 * Grupează intrările de istoric pe intervale de timp (Today / This week /
 * This month / Last 3 months / Older) și le afișează ca secțiuni pliabile,
 * în stilul paginii de Support. Prima secțiune negoală e deschisă implicit;
 * restul se deschid la click.
 *
 * Filtrarea pe date (from/to) rămâne în pagina părinte — componenta doar
 * grupează și afișează lista deja încărcată.
 *
 * props:
 *   entries  – array de obiecte cu un câmp `date` (ISO "YYYY-MM-DD") și `id`
 *   children – funcție (subsetEntries) => JSX, randează conținutul unei secțiuni
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
  const diff = Math.floor((today - d) / 86400000) // zile întregi
  if (diff <= 0)  return 0   // azi (sau viitor)
  if (diff <= 7)  return 1   // această săptămână
  if (diff <= 30) return 2   // această lună
  if (diff <= 90) return 3   // ultimele 3 luni
  return 4                   // mai vechi
}

export default function HistoryAccordion({ entries, children }) {
  // null = toate secțiunile închise la intrarea pe pagină; se deschid la click
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
