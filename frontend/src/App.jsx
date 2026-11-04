import { useCallback, useEffect, useState } from 'react'
import './App.css'
import RepositoryValidation from './components/RepositoryValidation'
import galleryLogo from './assets/GitGallery Logo.svg'

function formatStatus(status) {
  return status
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function ProjectCard({ project, onOpen }) {
  return (
    <article className="project-card">
      <div className="project-card__topline">
        <span className={`status status--${project.analysis_status}`}>
          {formatStatus(project.analysis_status)}
        </span>
      </div>
      <h2>{project.project_name}</h2>
      <p className="project-card__repository">
        {project.repository_owner}/{project.repository_name}
      </p>
      <div className="project-card__preview" aria-hidden="true">
        <span>Preview will appear after analysis</span>
      </div>
      <div className="project-card__footer">
        <span className="project-card__versions">
          {project.processed_versions} / {project.total_versions} versions
        </span>
        <span className="project-card__analysis-count">
          {project.saved_analysis_count || 0} saved analyses
        </span>
        <button className="text-button" onClick={onOpen}>
          Details <span aria-hidden="true">&rarr;</span>
        </button>
      </div>
    </article>
  )
}

function ProjectDetails({ project, onBack, onProjectUpdated }) {
  const [refreshError, setRefreshError] = useState('')
  const [analyses, setAnalyses] = useState([])
  const [analysesError, setAnalysesError] = useState('')

  useEffect(() => {
    let active = true
    async function loadAnalyses() {
      try {
        const response = await fetch(
          `/api/projects/${encodeURIComponent(project.id)}/analyses/`,
        )
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data.error || 'Could not load saved analyses.')
        }
        if (!Array.isArray(data.analyses)) {
          throw new Error('Saved analyses returned an invalid response.')
        }
        if (active) {
          setAnalyses(data.analyses)
          setAnalysesError('')
        }
      } catch (error) {
        if (active) {
          setAnalysesError(error.message || 'Could not load saved analyses.')
        }
      }
    }

    loadAnalyses()
    return () => {
      active = false
    }
  }, [project.id, project.analysis_status])

  useEffect(() => {
    if (project.analysis_status !== 'processing') {
      return undefined
    }

    let active = true
    async function refreshProject() {
      try {
        const response = await fetch(`/api/projects/${encodeURIComponent(project.id)}/`)
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data.error || 'Could not refresh the project status.')
        }
        if (active) {
          setRefreshError('')
          onProjectUpdated(data)
        }
      } catch (error) {
        if (active) {
          setRefreshError(error.message || 'Could not refresh the project status.')
        }
      }
    }

    refreshProject()
    const intervalId = window.setInterval(refreshProject, 5000)
    return () => {
      active = false
      window.clearInterval(intervalId)
    }
  }, [project.id, project.analysis_status, onProjectUpdated])

  return (
    <section className="project-details">
      <button className="text-button" onClick={onBack}>
        &larr; Back to gallery
      </button>
      <p className="eyebrow">Project analysis</p>
      <h1>{project.project_name}</h1>
      <p className="project-details__repository">
        {project.repository_owner}/{project.repository_name}
      </p>
      <div className="project-details__status">
        <span className={`status status--${project.analysis_status}`}>
          {formatStatus(project.analysis_status)}
        </span>
        <span aria-live="polite">
          {project.processed_versions} of {project.total_versions} versions
          processed
        </span>
      </div>
      {refreshError && (
        <p className="project-details__error" role="alert">
          {refreshError}
        </p>
      )}
      <a
        className="button button--secondary"
        href={project.repository_url}
        target="_blank"
        rel="noreferrer"
      >
        View repository
      </a>
      <p className="project-details__notice">
        {project.analysis_status === 'not_started'
          ? 'This repository is in the shared gallery. An analysis has not started yet.'
          : 'Analysis status and saved results are shared with users of this installation.'}
      </p>
      <section className="saved-analyses" aria-labelledby="saved-analyses-title">
        <h2 id="saved-analyses-title">Saved analyses</h2>
        {analysesError ? (
          <p className="project-details__error" role="alert">{analysesError}</p>
        ) : analyses.length === 0 ? (
          <p className="saved-analyses__empty">No saved analyses for this project yet.</p>
        ) : (
          <ul className="saved-analyses__list">
            {analyses.map((analysis) => (
              <li className="saved-analysis" key={analysis.id}>
                <div className="saved-analysis__heading">
                  <span className={`status status--${analysis.analysis_status}`}>
                    {formatStatus(analysis.analysis_status)}
                  </span>
                  <time dateTime={analysis.created_at}>
                    {new Date(analysis.created_at).toLocaleString()}
                  </time>
                </div>
                <p>
                  {analysis.processed_versions} of {analysis.total_versions} versions
                  processed
                </p>
                <details>
                  <summary>View saved result data</summary>
                  <pre>{JSON.stringify(analysis.results, null, 2)}</pre>
                </details>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  )
}

function App() {
  const [projects, setProjects] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [selectedProject, setSelectedProject] = useState(null)
  const [retryCount, setRetryCount] = useState(0)

  const handleProjectUpdated = useCallback((project) => {
    setProjects((currentProjects) => {
      const alreadyListed = currentProjects.some(
        (currentProject) => currentProject.id === project.id,
      )
      return alreadyListed
        ? currentProjects.map((currentProject) =>
            currentProject.id === project.id ? project : currentProject,
          )
        : [project, ...currentProjects]
    })
    setSelectedProject(project)
  }, [])

  function handleProjectCreated(project) {
    handleProjectUpdated(project)
    setIsSubmitting(false)
    setRetryCount((count) => count + 1)
  }

  useEffect(() => {
    const controller = new AbortController()

    async function loadProjects() {
      setIsLoading(true)
      setError('')

      try {
        const response = await fetch('/api/projects/', {
          signal: controller.signal,
        })
        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.error || 'Could not load the project gallery.')
        }
        if (!Array.isArray(data.projects)) {
          throw new Error('The project gallery returned an invalid response.')
        }

        setProjects(data.projects)
      } catch (loadError) {
        if (loadError.name !== 'AbortError') {
          setError(loadError.message || 'Could not load the project gallery.')
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }

    loadProjects()
    return () => controller.abort()
  }, [retryCount])

  return (
    <main className="app-shell">
      <header className="site-header">
        <a className="brand" href="/" aria-label="Git Gallery home">
          <img src={galleryLogo} alt="Git Gallery" />
        </a>
        <a className="site-header__info" href="#about" aria-label="About Git Gallery">
          i
        </a>
      </header>

      {isSubmitting ? (
        <section className="submission-page">
          <button
            className="text-button"
            onClick={() => setIsSubmitting(false)}
          >
            &larr; Back to gallery
          </button>
          <h1>Submit a repository</h1>
          <p>Check whether a public GitHub repository is ready for Git Gallery.</p>
          <RepositoryValidation onProjectCreated={handleProjectCreated} />
        </section>
      ) : selectedProject ? (
        <ProjectDetails
          project={selectedProject}
          onBack={() => setSelectedProject(null)}
          onProjectUpdated={handleProjectUpdated}
        />
      ) : (
        <section className="gallery-page">
          <div className="gallery-heading">
            <h1>Gallery</h1>
            <button
              className="button button--primary"
              onClick={() => setIsSubmitting(true)}
            >
              New Project
            </button>
          </div>

          {isLoading ? (
            <p className="notice" role="status">Loading projects...</p>
          ) : error ? (
            <div className="notice notice--error" role="alert">
              <p>{error}</p>
              <button
                className="text-button"
                onClick={() => setRetryCount((count) => count + 1)}
              >
                Try again
              </button>
            </div>
          ) : projects.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state__icon" aria-hidden="true">+</div>
              <h2>No projects are available yet</h2>
              <p>
                Submitted repositories will appear here for everyone using this
                Git Gallery installation.
              </p>
              <button
                className="button button--primary"
                onClick={() => setIsSubmitting(true)}
              >
                Submit a repository
              </button>
            </div>
          ) : (
            <div className="project-grid">
              {projects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onOpen={() => setSelectedProject(project)}
                />
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  )
}

export default App
