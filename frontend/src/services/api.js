const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? 'http://localhost:5000' : '')

/** Makes a request to the Flask API and returns parsed JSON. */
export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: 'application/json', ...options.headers },
    ...options,
  })

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.message ?? 'Unable to complete the request.')
  }

  return data
}

export function getHealthStatus() {
  return apiRequest('/api/health')
}

/** Upload one document and report browser upload progress before server processing begins. */
export function summarizeDocument(file, onProgress) {
  return new Promise((resolve, reject) => {
    const formData = new FormData()
    formData.append('file', file)

    const request = new XMLHttpRequest()
    request.open('POST', `${API_BASE_URL}/api/v1/summarize`)
    request.timeout = 45_000
    request.setRequestHeader('Accept', 'application/json')
    request.upload.addEventListener('progress', (event) => {
      if (!event.lengthComputable) return
      const percent = Math.round((event.loaded / event.total) * 100)
      onProgress?.({ stage: percent === 100 ? 'processing' : 'uploading', percent })
    })
    request.upload.addEventListener('loadend', () => onProgress?.({ stage: 'processing', percent: 100 }))
    request.addEventListener('load', () => {
      let data = {}
      try { data = JSON.parse(request.responseText) } catch { /* Handled below. */ }
      if (request.status >= 200 && request.status < 300 && data.success === true && data.summary) {
        resolve(data)
      } else {
        reject(new Error(data.message ?? 'The document could not be processed.'))
      }
    })
    request.addEventListener('error', () => reject(new Error('Unable to reach the College Notice API.')))
    request.addEventListener('timeout', () => reject(new Error('The processing request timed out. Please try again.')))
    request.addEventListener('abort', () => reject(new Error('The processing request was cancelled.')))
    request.send(formData)
  })
}
