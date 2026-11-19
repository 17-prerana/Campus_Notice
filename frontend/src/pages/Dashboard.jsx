import { useState } from 'react'
import FileUpload from '../components/FileUpload'
import Icon from '../components/Icon'
import RecentNotices from '../components/RecentNotices'
import Sidebar from '../components/Sidebar'
import StatCard from '../components/StatCard'
import SummaryPreview from '../components/SummaryPreview'
import { summarizeDocument } from '../services/api'

const stats = [
  { label: 'Notices processed', icon: <Icon name="file" size={19}/>, detail: 'Connect data to see your total.' },
  { label: 'Summaries available', icon: <Icon name="sparkles" size={19}/>, detail: 'No generated summaries yet.' },
  { label: 'Upcoming dates', icon: <Icon name="calendar" size={19}/>, detail: 'Important dates will appear here.' },
]

function InfoSection({ id, title, children }) {
  return <section className="scroll-mt-5 rounded-2xl border border-slate-200 bg-[#262930] p-5 shadow-sm sm:p-6" id={id} tabIndex="-1"><h2 className="text-sm font-semibold text-slate-900">{title}</h2><div className="mt-2 text-sm leading-6 text-slate-500">{children}</div></section>
}

function Dashboard() {
  const [activeItem, setActiveItem] = useState('Overview')
  const [result, setResult] = useState(null)
  const [requestError, setRequestError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState({ stage: 'uploading', percent: 0 })
  const navigateToSection = (label, sectionId) => {
    setActiveItem(label)
    const section = document.getElementById(sectionId)
    section?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    section?.focus({ preventScroll: true })
  }

  const processFile = async (file) => {
    if (isProcessing) return
    setIsProcessing(true)
    setRequestError('')
    setSuccessMessage('')
    setResult(null)
    setProgress({ stage: 'uploading', percent: 0 })
    try {
      const response = await summarizeDocument(file, setProgress)
      setResult(response)
      setSuccessMessage(`Notice processed successfully using ${response.summary_mode === 'local' ? 'Local Summary' : 'AI Summary'}.`)
    } catch (error) {
      setRequestError(error.message || 'The document could not be processed.')
    } finally {
      setIsProcessing(false)
    }
  }

  const clearResult = () => {
    if (!isProcessing) {
      setResult(null)
      setRequestError('')
      setSuccessMessage('')
    }
  }

  return <div className="min-h-screen bg-slate-50 md:flex" data-active-page={activeItem}><Sidebar activeItem={activeItem} onNavigate={navigateToSection}/><main className="min-w-0 flex-1 p-5 sm:p-8 lg:p-10"><header className="mb-8 flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-start sm:justify-between" id="overview" tabIndex="-1"><div><p className="text-sm font-medium text-brand-600">Academic workspace</p><h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Welcome to your notice dashboard</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Upload college notices, keep documents organised, and review clear summaries when processing is connected.</p></div><div className="inline-flex w-fit items-center gap-2 rounded-full border border-slate-200 bg-[#262930] px-3 py-1.5 text-sm text-slate-600 shadow-sm"><span className="h-2 w-2 rounded-full bg-emerald-500"/>Dashboard ready</div></header><div className="grid gap-4 sm:grid-cols-3">{stats.map((stat) => <StatCard key={stat.label} {...stat}/>)}</div><div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]"><div className="space-y-6"><div className="scroll-mt-5" id="upload-notice" tabIndex="-1"><FileUpload isProcessing={isProcessing} onClearResult={clearResult} onProcess={processFile} progress={progress} requestError={requestError} successMessage={successMessage}/></div><div className="scroll-mt-5" id="notice-history" tabIndex="-1"><RecentNotices/></div></div><SummaryPreview isProcessing={isProcessing} result={result}/></div><div className="mt-6 grid gap-6 lg:grid-cols-2"><InfoSection id="api-documentation" title="API documentation">The frontend sends selected documents to <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">POST /api/v1/summarize</code> using <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">VITE_API_BASE_URL</code>.</InfoSection><InfoSection id="settings" title="Settings">Personal settings are not connected yet. This section is available for navigation and will host dashboard preferences in a later phase.</InfoSection></div></main></div>
}

export default Dashboard
