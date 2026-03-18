export default function RiskBadge({ level }) {
  if (!level) return <span className="text-slate-400 text-xs">N/A</span>
  return <span className={`badge-${level}`}>{level.charAt(0).toUpperCase() + level.slice(1)}</span>
}
