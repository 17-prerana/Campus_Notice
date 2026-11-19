import Icon from './Icon'
const navigation = [
  ['Overview', 'grid', 'overview'],
  ['Upload Notice', 'upload', 'upload-notice'],
  ['Notice History', 'file', 'notice-history'],
  ['API Documentation', 'book', 'api-documentation'],
  ['Settings', 'settings', 'settings'],
]

function Sidebar({ activeItem, onNavigate }) { return <aside className="flex w-full shrink-0 flex-col border-b border-slate-200 bg-[#181A1E] p-4 md:min-h-screen md:w-64 md:border-r md:border-b-0 md:p-5"><div className="flex items-center gap-3 px-2 py-2"><div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-brand-600 to-blue-600 text-xs font-bold text-[#142620] shadow-sm">CN</div><div><p className="text-sm font-semibold">College Notice</p><p className="text-xs text-slate-500">Assistant</p></div></div><nav className="mt-6 flex gap-1 overflow-x-auto pb-1 md:flex-col" aria-label="Main navigation">{navigation.map(([label, icon, sectionId]) => <button aria-current={activeItem === label ? 'page' : undefined} className={`flex shrink-0 items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition ${activeItem === label ? 'bg-brand-600 text-[#142620] shadow-sm' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`} key={label} onClick={() => onNavigate(label, sectionId)} type="button"><Icon name={icon} size={18}/>{label}</button>)}</nav><div className="mt-auto hidden rounded-xl bg-slate-50 p-3 md:block"><p className="text-xs font-semibold text-slate-700">Phase 2 interface</p><p className="mt-1 text-xs leading-5 text-slate-500">Data services will be connected in a later phase.</p></div></aside> }
export default Sidebar
