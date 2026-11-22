import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import Sidebar from './components/Sidebar.jsx'
import Chat from './components/Chat.jsx'
import GraphView from './components/GraphView.jsx'

export default function App() {
  const [docs, setDocs] = useState([])
  const [selected, setSelected] = useState(null) // null = all documents
  const [tab, setTab] = useState('chat')
  const [health, setHealth] = useState(null)

  const refresh = useCallback(() => api.documents().then(setDocs).catch(() => {}), [])

  useEffect(() => {
    refresh()
    api.health().then(setHealth).catch(() => setHealth({ neo4j: false }))
  }, [refresh])

  const warning =
    health && !health.neo4j ? 'Cannot reach Neo4j. Start it with: docker compose up -d neo4j'
    : health && !health.llm_configured ? 'No LLM configured. Set GEMINI_API_KEY in .env (or LLM_PROVIDER=ollama).'
    : null

  return (
    <div className="app">
      <Sidebar docs={docs} selected={selected} onSelect={setSelected} onChange={refresh} />
      <main>
        <header>
          <div className="tabs">
            {['chat', 'graph'].map((t) => (
              <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>
                {t === 'chat' ? 'Chat' : 'Knowledge graph'}
              </button>
            ))}
          </div>
          <span className="scope">
            {selected ? docs.find((d) => d.id === selected)?.title || 'Document' : 'All documents'}
          </span>
        </header>
        {warning && <div className="banner">{warning}</div>}
        <section>{tab === 'chat' ? <Chat docId={selected} /> : <GraphView docId={selected} docs={docs} />}</section>
      </main>
    </div>
  )
}
