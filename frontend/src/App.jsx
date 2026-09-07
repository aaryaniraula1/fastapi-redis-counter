import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'


const API_BASE_URL = 'http://127.0.0.1:8000'
const JOBS_STORAGE_KEY = 'web_scraper_jobs'


const wait = (milliseconds) =>
  new Promise((resolve) => {
    setTimeout(resolve, milliseconds)
  })


const loadSavedJobs = () => {
  try {
    const storedValue =
      localStorage.getItem(JOBS_STORAGE_KEY)

    if (!storedValue) {
      return []
    }

    const savedJobs = JSON.parse(storedValue)

    if (!Array.isArray(savedJobs)) {
      return []
    }

    return savedJobs.map((job) => ({
      id: job.id,
      url: job.url,
      status: 'restoring',
      result: null,
      error: '',
    }))
  } catch {
    return []
  }
}


function App() {
  const [urlInput, setUrlInput] = useState('')
  const [jobs, setJobs] = useState(loadSavedJobs)
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const activePolls = useRef(new Set())


  const updateJob = useCallback(
    (jobId, updates) => {
      setJobs((currentJobs) =>
        currentJobs.map((job) =>
          job.id === jobId
            ? {
                ...job,
                ...updates,
              }
            : job
        )
      )
    },
    []
  )


  const removeJob = useCallback(
    (jobId) => {
      setJobs((currentJobs) =>
        currentJobs.filter(
          (job) => job.id !== jobId
        )
      )
    },
    []
  )


  const pollJob = useCallback(
    async (jobId) => {
      if (activePolls.current.has(jobId)) {
        return
      }

      activePolls.current.add(jobId)

      try {
        while (true) {
          const response = await fetch(
            `${API_BASE_URL}/api/jobs/${jobId}`
          )

          const data = await response.json()

          if (!response.ok) {
            if (response.status === 404) {
              removeJob(jobId)
              return
            }

            throw new Error(
              data.detail ||
                'Could not check job status'
            )
          }

          updateJob(jobId, {
            status: data.status,
            error: '',
          })

          if (data.status === 'finished') {
            updateJob(jobId, {
              status: 'finished',
              result: data.result,
              error: '',
            })

            return
          }

          if (data.status === 'failed') {
            updateJob(jobId, {
              status: 'failed',
              result: null,
              error:
                data.error ||
                'Scraping job failed',
            })

            return
          }

          await wait(1000)
        }

      } catch (error) {
        updateJob(jobId, {
          status: 'tracking-error',
          error: error.message,
        })

      } finally {
        activePolls.current.delete(jobId)
      }
    },
    [removeJob, updateJob]
  )


  useEffect(() => {
    const jobsToSave = jobs.map((job) => ({
      id: job.id,
      url: job.url,
    }))

    localStorage.setItem(
      JOBS_STORAGE_KEY,
      JSON.stringify(jobsToSave)
    )
  }, [jobs])


  useEffect(() => {
    jobs.forEach((job) => {
      if (
        job.status === 'restoring' ||
        job.status === 'queued' ||
        job.status === 'started'
      ) {
        pollJob(job.id)
      }
    })
  }, [jobs, pollJob])


  const getUrls = () => {
    const enteredUrls = urlInput
      .split(/\n|,/)
      .map((url) => url.trim())
      .filter(Boolean)

    return [...new Set(enteredUrls)]
  }


  const isValidUrl = (value) => {
    try {
      const parsedUrl = new URL(value)

      return (
        parsedUrl.protocol === 'http:' ||
        parsedUrl.protocol === 'https:'
      )
    } catch {
      return false
    }
  }


  const submitJobs = async (event) => {
    event.preventDefault()

    setFormError('')

    const urls = getUrls()

    if (urls.length === 0) {
      setFormError(
        'Enter at least one website URL.'
      )

      return
    }

    const invalidUrls = urls.filter(
      (url) => !isValidUrl(url)
    )

    if (invalidUrls.length > 0) {
      setFormError(
        'All URLs must start with http:// or https://'
      )

      return
    }

    setSubmitting(true)

    try {
      const requests = urls.map(
        async (url) => {
          try {
            const response = await fetch(
              `${API_BASE_URL}/api/scrape`,
              {
                method: 'POST',
                headers: {
                  'Content-Type':
                    'application/json',
                },
                body: JSON.stringify({
                  url,
                }),
              }
            )

            const data = await response.json()

            if (!response.ok) {
              throw new Error(
                data.detail ||
                  'Failed to create scraping job'
              )
            }

            return {
              success: true,
              job: {
                id: data.job_id,
                url,
                status: data.status,
                result: null,
                error: '',
              },
            }

          } catch (error) {
            return {
              success: false,
              url,
              error: error.message,
            }
          }
        }
      )

      const responses =
        await Promise.all(requests)

      const createdJobs = responses
        .filter(
          (response) => response.success
        )
        .map(
          (response) => response.job
        )

      const failedRequests = responses.filter(
        (response) => !response.success
      )

      if (createdJobs.length > 0) {
        setJobs((currentJobs) => [
          ...createdJobs,
          ...currentJobs,
        ])

        setUrlInput('')
      }

      if (failedRequests.length > 0) {
        setFormError(
          `${failedRequests.length} URL request(s) could not be queued.`
        )
      }

    } finally {
      setSubmitting(false)
    }
  }


  const finishedJobCount = jobs.filter(
    (job) => job.status === 'finished'
  ).length


  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <h1>Web Scraper UI</h1>

          <p className="subtitle">
            Submit URLs and track scraping tasks.
          </p>
        </div>

        <div className="summary">
          <div className="summary-card">
            <span>Completed</span>
            <strong>{finishedJobCount}</strong>
          </div>
        </div>
      </section>


      <section className="scrape-panel">
        <form onSubmit={submitJobs}>
          <label htmlFor="urls">
            Website URLs
          </label>

          <textarea
            id="urls"
            rows="5"
            value={urlInput}
            onChange={(event) =>
              setUrlInput(event.target.value)
            }
          />

          {formError && (
            <p className="form-error">
              {formError}
            </p>
          )}

          <button
            className="primary-button"
            type="submit"
            disabled={submitting}
          >
            {submitting
              ? 'Adding...'
              : 'Start Scraping'}
          </button>
        </form>
      </section>


      <section className="jobs-section">
        <div className="jobs-heading">
          <h2>Results</h2>
        </div>


        {jobs.length === 0 ? (
          <div className="empty-state">
            <p>No results yet.</p>
          </div>
        ) : (
          <div className="jobs-grid">
            {jobs.map((job) => (
              <article
                className="job-card"
                key={job.id}
              >
                <div className="job-card-header">
                  <span
                    className={
                      `status-badge status-${job.status}`
                    }
                  >
                    {job.status === 'tracking-error'
                      ? 'tracking error'
                      : job.status}
                  </span>

                  <span className="job-id">
                    {job.id}
                  </span>
                </div>


                <p className="job-url">
                  {job.url}
                </p>


                {job.status === 'queued' && (
                  <p className="job-message">
                    Waiting...
                  </p>
                )}


                {job.status === 'started' && (
                  <p className="job-message">
                    Scraping...
                  </p>
                )}


                {job.status === 'restoring' && (
                  <p className="job-message">
                    Restoring...
                  </p>
                )}


                {job.status === 'finished' &&
                  job.result && (
                    <div className="result-box">
                      <div>
                        <span>Title</span>

                        <p>
                          {job.result.title ||
                            'Not found'}
                        </p>
                      </div>

                      <div>
                        <span>Description</span>

                        <p>
                          {job.result.description ||
                            'Not found'}
                        </p>
                      </div>
                    </div>
                  )}


                {job.status === 'failed' && (
                  <div className="error-box">
                    {job.error ||
                      'Scraping failed'}
                  </div>
                )}


                {job.status ===
                  'tracking-error' && (
                  <div className="error-box">
                    {job.error}
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  )
}


export default App