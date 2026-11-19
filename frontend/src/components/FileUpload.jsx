import { useRef, useState } from 'react'
import Icon from './Icon'

const MAX_FILE_SIZE = 10 * 1024 * 1024
const ACCEPTED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png']

const formatFileSize = (bytes) => bytes < 1024 * 1024
  ? `${Math.max(1, Math.round(bytes / 1024))} KB`
  : `${(bytes / (1024 * 1024)).toFixed(1)} MB`

const getFileType = (file) => {
  if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) return 'PDF document'
  if (file.type === 'image/png' || file.name.toLowerCase().endsWith('.png')) return 'PNG image'
  return 'JPEG image'
}

function FileUpload({ isProcessing, progress, requestError, successMessage, onProcess, onClearResult }) {
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [validationError, setValidationError] = useState('')
  const [dragging, setDragging] = useState(false)
  const error = validationError || requestError

  const selectFile = (candidate) => {
    if (!candidate || isProcessing) return
    const extension = `.${candidate.name.split('.').pop()?.toLowerCase()}`
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setFile(null)
      setValidationError('Only PDF, JPG, JPEG, and PNG files are supported.')
      onClearResult()
      return
    }
    if (candidate.size === 0) {
      setFile(null)
      setValidationError('The selected file is empty.')
      onClearResult()
      return
    }
    if (candidate.size > MAX_FILE_SIZE) {
      setFile(null)
      setValidationError('Please choose a file smaller than 10 MB.')
      onClearResult()
      return
    }
    setValidationError('')
    setFile(candidate)
    onClearResult()
  }

  const removeFile = () => {
    if (isProcessing) return
    setFile(null)
    setValidationError('')
    if (inputRef.current) inputRef.current.value = ''
    onClearResult()
  }

  const submit = () => {
    if (!file || isProcessing) return
    onProcess(file)
  }

  return <section className="rounded-2xl border border-slate-200 bg-[#262930] p-5 shadow-sm sm:p-6"><div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start"><div><h2 className="text-sm font-semibold text-slate-900">Upload a notice</h2><p className="mt-1 text-sm text-slate-500">Upload a PDF or notice image up to 10 MB.</p></div><span className="w-fit rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700">PDF, JPG, JPEG, PNG</span></div>
    {!file ? <div className={`mt-5 rounded-xl border-2 border-dashed p-7 text-center transition sm:p-9 ${dragging ? 'border-brand-600 bg-brand-50' : 'border-slate-200 bg-slate-50/70 hover:border-brand-200 hover:bg-brand-50/40'}`} onDragEnter={(event) => { event.preventDefault(); if (!isProcessing) setDragging(true) }} onDragLeave={(event) => { event.preventDefault(); setDragging(false) }} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); setDragging(false); selectFile(event.dataTransfer.files[0]) }}><div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-[#262930] text-brand-600 shadow-sm"><Icon name="upload" size={22}/></div><p className="mt-4 text-sm font-semibold text-slate-800">Drag and drop your notice here</p><p className="mt-1 text-sm text-slate-500">or choose a supported document from your device</p><button className="mt-5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-[#142620] shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-200 disabled:cursor-not-allowed disabled:bg-slate-300" disabled={isProcessing} onClick={() => inputRef.current?.click()} type="button">Browse files</button><input accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" className="sr-only" onChange={(event) => selectFile(event.target.files[0])} ref={inputRef} type="file"/></div> : <div className="mt-5 rounded-xl border border-brand-200 bg-brand-50/60 p-4"><div className="flex flex-col gap-4 sm:flex-row sm:items-center"><div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-[#262930] text-brand-600 shadow-sm"><Icon name="file" size={20}/></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-slate-800">{file.name}</p><p className="mt-0.5 text-xs text-slate-500">{getFileType(file)} &middot; {formatFileSize(file.size)}</p></div><button aria-label="Remove selected file" className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-[#262930] px-3 py-2 text-sm font-medium text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50" disabled={isProcessing} onClick={removeFile} type="button"><Icon name="close" size={16}/>Remove</button></div><div className="mt-4 border-t border-brand-100 pt-4">{isProcessing ? <div><div className="flex justify-between text-xs font-medium text-brand-700"><span>{progress.stage === 'uploading' ? 'Uploading document...' : 'Extracting text and generating summary...'}</span><span>{progress.stage === 'uploading' ? `${progress.percent}%` : 'Please wait'}</span></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-brand-100"><div className={`h-full bg-brand-600 transition-all ${progress.stage === 'processing' ? 'w-full animate-pulse' : ''}`} style={{ width: progress.stage === 'processing' ? undefined : `${progress.percent}%` }}/></div></div> : <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-xs text-slate-500">Your document will be sent securely to the processing API.</p><button className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-[#142620] shadow-sm transition hover:bg-brand-700" onClick={submit} type="button">Process notice</button></div>}</div></div>}
    {!file && <div className="mt-4 flex justify-between border-t border-slate-100 pt-4"><p className="text-xs text-slate-500">Select a supported file to continue.</p><button className="cursor-not-allowed rounded-lg bg-slate-200 px-4 py-2 text-sm font-medium text-slate-500" disabled type="button">Process notice</button></div>}
    {error && <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert"><span>{error}</span>{file && requestError && !isProcessing && <button className="font-semibold underline" onClick={submit} type="button">Retry</button>}</div>}
    {successMessage && !error && <div className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700" role="status">{successMessage}</div>}</section>
}

export default FileUpload
