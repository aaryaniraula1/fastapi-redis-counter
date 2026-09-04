import { useState } from 'react'
import './App.css'

function App() {
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const checkConnection = async () => {
    setMessage('')
    setError('')
    setLoading(true)

    try {
      const response = await fetch('http://127.0.0.1:8000/api/health')

      if (!response.ok) {
        throw new Error('Failed to connect to FastAPI')
      }

      const data = await response.json()
      setMessage(data.message)
    } catch (error) {
      setError(error.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main>
      <h1>Web Scraper UI</h1>
      <p>Vite frontend connected with FastAPI.</p>

      <button onClick={checkConnection} disabled={loading}>
        {loading ? 'Checking...' : 'Check API Connection'}
      </button>

      {message && <p>{message}</p>}
      {error && <p>{error}</p>}
    </main>
  )
}

export default App