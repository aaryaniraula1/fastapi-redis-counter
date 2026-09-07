import { useState } from 'react'
import './App.css'


const API_BASE_URL = 'http://127.0.0.1:8000'

const wait = (milliseconds) =>
  new Promise((resolve) => {
    setTimeout(resolve, milliseconds)
  })


function App() {
  const [url, setUrl] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [jobId, setJobId] = useState('')
  const [jobStatus, setJobStatus] = useState('')


  const pollJob = async (currentJobId) => {
    for (let attempt = 0; attempt < 120; attempt += 1) {
      const response = await fetch(
        `${API_BASE_URL}/api/jobs/${currentJobId}`
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail || 'Failed to check scraping job'
        )
      }

      setJobStatus(data.status)

      if (data.status === 'finished') {
        return data.result
      }

      if (data.status === 'failed') {
        throw new Error(
          data.error || 'Scraping job failed'
        )
      }

      await wait(1000)
    }

    throw new Error(
      'Scraping job did not finish in time'
    )
  }


  const scrapeWebsite = async (event) => {
    event.preventDefault()

    setResult(null)
    setError('')
    setJobId('')
    setJobStatus('')
    setLoading(true)

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/scrape`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ url }),
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail || 'Failed to create scraping job'
        )
      }

      setJobId(data.job_id)
      setJobStatus(data.status)

      const scrapedResult = await pollJob(
        data.job_id
      )

      setResult(scrapedResult)

    } catch (error) {
      setError(error.message)

    } finally {
      setLoading(false)
    }
  }


  return (
    <main>
      <h1>Web Scraper UI</h1>

      <p>
        Enter a website URL to create a background scraping job.
      </p>

      <form onSubmit={scrapeWebsite}>
        <input
          type="url"
          placeholder="https://example.com"
          value={url}
          onChange={(event) =>
            setUrl(event.target.value)
          }
          required
        />

        <button
          type="submit"
          disabled={loading}
        >
          {loading ? 'Scraping...' : 'Scrape'}
        </button>
      </form>

      {jobId && (
        <p>
          <strong>Job ID:</strong> {jobId}
        </p>
      )}

      {jobStatus && (
        <p>
          <strong>Job status:</strong> {jobStatus}
        </p>
      )}

      {error && (
        <p>{error}</p>
      )}

      {result && (
        <section>
          <h2>Scraped Result</h2>

          <p>
            <strong>URL:</strong> {result.url}
          </p>

          <p>
            <strong>Title:</strong>{' '}
            {result.title || 'Not found'}
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