import React, { useState, useEffect } from 'react'

function App() {
  const [apiStatus, setApiStatus] = useState('Checking backend connection...')

  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then(res => res.json())
      .then(data => setApiStatus(`Connected to backend (${data.status})`))
      .catch(() => setApiStatus('Backend currently disconnected (Start backend on port 8000)'))
  }, [])

  return (
    <div style={{ maxWidth: '640px', margin: '40px auto', padding: '24px', backgroundColor: '#fff', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
      <h1>AI Customer Support Agent</h1>
      <p style={{ color: '#666' }}>Phase 0: Initial Foundation &amp; Architecture</p>
      <div style={{ marginTop: '20px', padding: '12px', borderRadius: '4px', backgroundColor: '#eef2f6', fontSize: '14px' }}>
        <strong>Backend Status:</strong> {apiStatus}
      </div>
      <div style={{ marginTop: '24px', textAlign: 'left', fontSize: '14px', lineHeight: '1.6' }}>
        <h3>Upcoming Milestones:</h3>
        <ul>
          <li>Phase 1: Database &amp; Synthetic Commerce Data</li>
          <li>Phase 2: FastAPI Authentication &amp; Customer Context</li>
          <li>Phase 3: Real-time Chat UI</li>
          <li>Phase 4+: AI Support Agent, Tools, and Policy RAG</li>
        </ul>
      </div>
    </div>
  )
}

export default App
