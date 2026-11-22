async function request(path, options) {
  const res = await fetch(`/api${path}`, options)
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail || detail } catch { /* not JSON */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.json()
}

export const api = {
  health: () => request('/health'),
  documents: () => request('/documents').then((r) => r.documents),
  upload: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/documents', { method: 'POST', body: form })
  },
  job: (id) => request(`/jobs/${id}`),
  remove: (id) => request(`/documents/${id}`, { method: 'DELETE' }),
  graph: (docId) => request(`/graph${docId ? `?doc_id=${docId}` : ''}`),
  chat: (question, docId) =>
    request('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, doc_id: docId || null }),
    }),
}
