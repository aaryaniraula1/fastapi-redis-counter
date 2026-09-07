import { useCallback, useEffect, useState } from 'react'
import './App.css'


const API_BASE_URL = 'http://127.0.0.1:8000'

const ACTIVE_JOB_KEY =
  'web_scraper_active_job_id'


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


  const pollJob = useCallback(
    async (
      currentJobId,
      shouldStop = () => false
    ) => {
      for (
        let attempt = 0;
        attempt < 120;
        attempt += 1
      ) {
        if (shouldStop()) {
          return null
        }

        const response = await fetch(
          `${API_BASE_URL}/api/jobs/${currentJobId}`
        )

        const data = await response.json()

        if (!response.ok) {
          if (response.status === 404) {
            localStorage.removeItem(
              ACTIVE_JOB_KEY
            )

            setJobId('')
            setJobStatus('')
          }

          throw new Error(
            data.detail ||
              'Failed to check scraping job'
          )
        }

        if (shouldStop()) {
          return null
        }

        setJobStatus(data.status)

        if (data.status === 'finished') {
          return data.result
        }

        if (data.status === 'failed') {
          throw new Error(
            data.error ||
              'Scraping job failed'
          )
        }

        await wait(1000)
      }

      throw new Error(
        'Scraping job did not finish in time'
      )
    },
    []
  )


  useEffect(() => {
    const savedJobId = localStorage.getItem(
      ACTIVE_JOB_KEY
    )

    if (!savedJobId) {
      return
    }

    let cancelled = false


    const resumeJob = async () => {
      setJobId(savedJobId)
      setResult(null)
      setError('')
      setLoading(true)

      try {
        const restoredResult = await pollJob(
          savedJobId,
          () => cancelled
        )

        if (
          !cancelled &&
          restoredResult
        ) {
          setResult(restoredResult)
        }

      } catch (error) {
        if (!cancelled) {
          setError(error.message)
        }

      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }


    resumeJob()


    return () => {
      cancelled = true
    }
  }, [pollJob])


  const scrapeWebsite = async (event) => {
    event.preventDefault()

    setResult(null)
    setError('')
    setJobId('')
    setJobStatus('')
    setLoading(true)

    localStorage.removeItem(
      ACTIVE_JOB_KEY
    )

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/scrape`,
        {
          method: 'POST',
          headers: {
            'Content-Type':
              'application/json',
          },
          body: JSON.stringify({ url }),
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail ||
            'Failed to create scraping job'
        )
      }

      setJobId(data.job_id)
      setJobStatus(data.status)

      localStorage.setItem(
        ACTIVE_JOB_KEY,
        data.job_id
      )

      const scrapedResult =
        await pollJob(data.job_id)

      if (scrapedResult) {
        setResult(scrapedResult)
      }

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
        Enter a website URL to create a
        background scraping job.
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
          {loading
            ? 'Scraping...'
            : 'Scrape'}
        </button>
      </form>

      {jobId && (
        <p>
          <strong>Job ID:</strong>{' '}
          {jobId}
        </p>
      )}

      {jobStatus && (
        <p>
          <strong>Job status:</strong>{' '}
          {jobStatus}
        </p>
      )}

      {error && (
        <p>{error}</p>
      )}

      {result && (
        <section>
          <h2>Scraped Result</h2>

          <p>
            <strong>URL:</strong>{' '}
            {result.url}
          </p>

          <p>
            <strong>Title:</strong>{' '}
            {result.title || 'Not found'}
          </p>

          <p>
            <strong>Description:</strong>{' '}
            {result.description ||
              'Not found'}
          </p>
        </section>
      )}
    </main>
  )
}


export default App