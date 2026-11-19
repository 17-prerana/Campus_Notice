import Icon from './Icon'

const PLACEHOLDER = /^(not (mentioned|specified)( in the notice)?|n\/?a|none|unknown|not available)$/i

const hasValue = (value) => typeof value === 'string' && value.trim() && !PLACEHOLDER.test(value.trim())
const listItems = (value) => (Array.isArray(value) ? value : [value]).filter(hasValue)

function MetaCard({ icon, label, value }) {
  if (!hasValue(value)) return null
  return <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
    <div className="flex items-center gap-2 text-slate-500"><Icon className="text-brand-600" name={icon} size={16}/><span className="text-xs font-semibold uppercase tracking-wide">{label}</span></div>
    <p className="mt-2 break-words text-sm leading-5 text-slate-700">{value}</p>
  </div>
}

function DetailSection({ title, icon, values, tone = 'slate' }) {
  const items = listItems(values)
  if (!items.length) return null
  const tones = { slate: 'border-slate-200 bg-slate-50 text-slate-700', violet: 'border-brand-100 bg-brand-50 text-brand-900', amber: 'border-amber-200 bg-amber-50 text-amber-900' }
  return <section className={`rounded-xl border p-4 ${tones[tone]}`}>
    <div className="flex items-center gap-2"><Icon name={icon} size={17}/><h3 className="text-sm font-semibold">{title}</h3></div>
    <ul className="mt-3 space-y-2 text-sm leading-6">{items.map((item, index) => <li className="flex gap-2" key={`${item}-${index}`}><span aria-hidden="true" className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-current opacity-60"/>{item}</li>)}</ul>
  </section>
}

function SummaryPreview({ result, isProcessing }) {
  const summary = result?.summary
  const isLocal = result?.summary_mode === 'local'
  const modeLabel = isLocal ? 'Local Summary' : 'AI Summary'
  const urgencyClasses = { High: 'bg-rose-100 text-rose-800', Medium: 'bg-amber-100 text-amber-800', Low: 'bg-emerald-100 text-emerald-800' }

  return <section className="rounded-2xl border border-slate-200 bg-[#262930] p-5 shadow-sm sm:p-6">
    <div className="flex items-start justify-between gap-3"><div><h2 className="text-sm font-semibold text-slate-900">Notice summary</h2><p className="mt-1 text-sm text-slate-500">{result ? `Processed: ${result.filename}` : isProcessing ? 'Processing your notice…' : 'A structured overview appears after processing.'}</p></div><div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-blue-50 text-blue-600"><Icon name="sparkles" size={18}/></div></div>
    {isProcessing ? <div className="mt-5 rounded-xl bg-brand-50 p-5 text-center"><p className="text-sm font-medium text-brand-700">Processing notice…</p><p className="mt-1 text-xs leading-5 text-brand-600">The extracted notice details will appear here when ready.</p></div>
      : !summary ? <div className="mt-5 rounded-xl bg-slate-50 p-5 text-center"><p className="text-sm font-medium text-slate-600">No processed notice yet</p><p className="mt-1 text-xs leading-5 text-slate-400">Upload a PDF or image to extract its text and generate a summary.</p></div>
        : <div className="mt-5 space-y-5">
          <div className="flex flex-wrap items-center gap-2"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${isLocal ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'}`}>{modeLabel}</span>{hasValue(summary.urgency) && <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${urgencyClasses[summary.urgency] ?? 'bg-slate-100 text-slate-700'}`}>{summary.urgency} urgency</span>}</div>
          {result.warning && <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-800" role="alert">{result.warning}</p>}
          {hasValue(summary.notice_title) && <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Notice title</p><h3 className="mt-1 text-xl font-bold tracking-tight text-slate-900">{summary.notice_title}</h3></div>}
          <div className="grid gap-3 lg:grid-cols-2"><DetailSection icon="sparkles" title="Short summary" tone="violet" values={summary.short_summary}/><DetailSection icon="book" title="Detailed summary" values={summary.detailed_summary}/></div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"><DetailSection icon="calendar" title="Important dates" values={summary.important_dates}/><DetailSection icon="calendar" title="Event dates" values={summary.event_dates}/><MetaCard icon="users" label="Target audience" value={summary.target_audience}/><MetaCard icon="book" label="Department" value={summary.department}/><MetaCard icon="file" label="Venue" value={summary.venue}/><MetaCard icon="file" label="Contact information" value={summary.contact_information}/></div>
          <div className="grid gap-3 lg:grid-cols-3"><DetailSection icon="check" title="Action items" tone="violet" values={summary.action_items}/><DetailSection icon="file" title="Important instructions" values={summary.important_instructions}/><DetailSection icon="file" title="Required documents" values={summary.required_documents}/></div>
          {(hasValue(summary.source_information) || listItems(summary.uncertainty_warnings).length > 0) && <div className="grid gap-3 lg:grid-cols-2">{hasValue(summary.source_information) && <section className="rounded-xl border border-slate-200 p-4"><div className="flex items-center gap-2 text-slate-700"><Icon name="file" size={17}/><h3 className="text-sm font-semibold">Source information</h3></div><p className="mt-2 text-sm leading-6 text-slate-600">{summary.source_information}</p></section>}<DetailSection icon="clock" title="Uncertainty warnings" tone="amber" values={summary.uncertainty_warnings}/></div>}
        </div>}
  </section>
}

export default SummaryPreview
