import { useState } from 'react'
import './App.css'

function App() {
  const [url, setUrl] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const scrapeWebsite = async (event) => {
    event.preventDefault()

    setResult(null)
    setError('')
    setLoading(true)

    try {
      const response = await fetch('http://127.0.0.1:8000/api/scrape', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to scrape website')
      }

      setResult(data)
    } catch (error) {
      setError(error.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main>
      <h1>Web Scraper UI</h1>

      <p>Enter a website URL to scrape basic page information.</p>

      <form onSubmit={scrapeWebsite}>
        <input
          type="url"
          placeholder="https://example.com"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          required
        />

        <button type="submit" disabled={loading}>
          {loading ? 'Scraping...' : 'Scrape'}
        </button>
      </form>

      {error && <p>{error}</p>}

      {result && (
        <section>
          <h2>Scraped Result</h2>

          <p>
            <strong>URL:</strong> {result.url}
          </p>

          <p>
            <strong>Title:</strong> {result.title || 'Not found'}
          </p>

          <p>
            <strong>Description:</strong>{' '}
            {result.description || 'Not found'}
          </p>
        </section>
      )}
    </main>
  )
}

export default App