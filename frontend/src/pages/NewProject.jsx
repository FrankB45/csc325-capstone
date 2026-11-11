import { useEffect, useId, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import PageLayout from "../components/PageLayout/PageLayout.jsx";
import NextButton from "../components/NextButton/NextButton.jsx";
import CancelButton from "../components/CancelButton/CancelButton.jsx";
import Spinner from "../components/Spinner/Spinner.jsx";
import CommitPicker from "../components/CommitPicker/CommitPicker.jsx";
import { useRepositoryLookup } from "../hooks/useRepositoryLookup.js";
import { MIN_COMMITS, MAX_COMMITS } from "../utils/commits.js";
import styles from "./NewProject.module.css";
import watermark from "../assets/octocat-watermark.svg";

async function postJSON(path, body, signal) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

  const data = await response.json();

  if (!response.ok) {
    const message = data.error || data.detail || data.reason;
    const fields = Object.entries(data)
      .map(([field, errors]) =>
        field + ": " + (Array.isArray(errors) ? errors.join(" ") : JSON.stringify(errors))
      )
      .join(" ");

    throw new Error(
      (Array.isArray(message) ? message.join(" ") : message) ||
      fields ||
      "The request failed. Please try again."
    );
  }

  return data;
}

const NewProject = () => {
  const navigate = useNavigate();
  const urlId = useId();
  const titleId = useId();
  const errorId = useId();
  const pageId = useId();

  const requestRef = useRef(null);

  const { repository, error: lookupError, lookup, reset } = useRepositoryLookup();
  const [step, setStep] = useState("url"); // "url" | "setup" | "creating"
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [pages, setPages] = useState([]);
  const [pagePath, setPagePath] = useState("");
  const [commits, setCommits] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [isChecking, setIsChecking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => () => requestRef.current?.abort(), []);

  const displayedError = error || lookupError;

  const canSubmit =
    title.trim().length > 0 &&
    pages.includes(pagePath) &&
    selectedIds.length >= MIN_COMMITS &&
    selectedIds.length <= MAX_COMMITS;

  async function handleUrlSubmit(event) {
    event.preventDefault();
    if (requestRef.current) return;

    const controller = new AbortController();
    requestRef.current = controller;
    setIsChecking(true);
    setError("");

    try {
      const repo = await lookup(url);
      if (!repo || controller.signal.aborted) return;

      const report = await postJSON(
        "/api/repo/compatibility/",
        { url: repo.url },
        controller.signal
      );

      if (!report.setup_available) {
        const checks = [
          [report.history?.history_status, report.history?.reason],
          [report.html?.html_status, report.html?.reason],
          [report.dependencies?.status, report.dependencies?.reason],
        ];
        const problem = checks.find(([status]) => status !== "passed");

        throw new Error(
          problem?.[1] || report.reason || "This repository is not supported."
        );
      }

      const history = await postJSON(
        "/api/repo/commits/",
        { url: repo.url },
        controller.signal
      );

      if (controller.signal.aborted) return;

      const availablePages = report.html.html_pages;

      if (!availablePages.length || !history.commits.length) {
        throw new Error("No pages or commits are available for capture.");
      }

      setTitle(repo.name);
      setPages(availablePages);
      setPagePath(
        availablePages.find((path) => path.toLowerCase() === "index.html") ||
        availablePages[0]
      );

      setCommits(
        history.commits.map((commit) => ({
          ...commit,
          id: commit.sha,
        }))
      );

      setSelectedIds(history.preselected);
      setStep("setup");
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err.message || "Could not prepare the project.");
      }
    } finally {
      if (requestRef.current === controller) requestRef.current = null;
      if (!controller.signal.aborted) setIsChecking(false);
    }
  }

  async function handleSetupSubmit(event) {
    event.preventDefault();
    if (!canSubmit || requestRef.current) return;

    const controller = new AbortController();
    requestRef.current = controller;
    setError("");
    setStep("creating");

    try {
      const result = await postJSON(
        "/api/analyses/",
        {
          url: repository.url,
          name: title.trim(),
          page_path: pagePath,
          commit_shas: selectedIds,
        },
        controller.signal
      );

      if (!controller.signal.aborted) {
        navigate("/projects/" + result.project_id + "/timeline");
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err.message || "Could not create the project.");
        setStep("setup");
      }
    } finally {
      if (requestRef.current === controller) requestRef.current = null;
    }
  }

  function changeUrl() {
    reset();
    setError("");
    setPages([]);
    setPagePath("");
    setCommits([]);
    setSelectedIds([]);
    setStep("url");
  }

  if (step === "creating") {
    return (
      <PageLayout width="full">
        <div className={styles.page}>
          <img
            className={styles.watermark}
            src={watermark}
            alt=""
            aria-hidden="true"
          />

          <div className={styles.creating} role="status">
            <h1 className={styles.creatingTitle}>Creating project</h1>
            <Spinner size={56} label="Creating project" />
          </div>
        </div>
      </PageLayout>
    );
  }

  // The read-only URL on the setup step is "click to change": it returns to step 1 with the URL kept.
  function changeUrl() {
    reset();
    setStep("url");
  }

  if (step === "creating") {
    return (
      <PageLayout width="full">
        <div className={styles.page}>
          {/* decorative background mark, clipped by the right edge of the page */}
          <img className={styles.watermark} src={watermark} alt="" aria-hidden="true" />
          <div className={styles.creating} role="status">
            <h1 className={styles.creatingTitle}>Creating Timeline</h1>
            <Spinner size={56} label="Creating timeline" />
          </div>
        </div>
      </PageLayout>
    );
  }

  if (step === "setup") {
    return (
      <PageLayout width="narrow" watermark>
        <h1 className={styles.title}>New Project</h1>
        <form className={styles.form} onSubmit={handleSetupSubmit}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor={urlId}>GitHub Repository URL</label>
            <input
              id={urlId}
              className={styles.input}
              value={repository.url}
              readOnly
            />

            <CancelButton onClick={changeUrl}>
              Change repository
            </CancelButton>

          </div>

          <div className={`${styles.field} ${styles.titleField}`}>
            <label className={styles.label} htmlFor={titleId}>Project Title</label>
            <input
              id={titleId}
              className={styles.input}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              maxLength={200}
              required
            />
          </div>

          <div className={styles.field + " " + styles.titleField}>
            <label className={styles.label} htmlFor={pageId}>
              HTML Page
            </label>

            <select
              id={pageId}
              className={styles.input}
              value={pagePath}
              onChange={(event) => setPagePath(event.target.value)}
              required
            >
              {pages.map((path) => (
                <option key={path} value={path}>
                  {path}
                </option>
              ))}
            </select>
          </div>

          <p>Screenshots will appear after you create the project.</p>

          <CommitPicker
            commits={commits}
            selectedIds={selectedIds}
            onChange={setSelectedIds}
          />

          {displayedError && (
            <p role="alert" className={styles.error}>
              {displayedError}
            </p>
          )}

          <div className={styles.actions}>
            <NextButton disabled={!canSubmit}>
              Create project
            </NextButton>

            <CancelButton to="/" />
          </div>
        </form>
      </PageLayout>
    );
  }

  return (
    <PageLayout width="narrow" watermark>
      <h1 className={styles.title}>New Project</h1>
      <form className={styles.form} onSubmit={handleUrlSubmit} noValidate>
        <div className={`${styles.field} ${styles.urlStep}`}>
          <label className={styles.label} htmlFor={urlId}>GitHub Repository URL</label>
          <input
            id={urlId}
            className={
              styles.input + (displayedError ? " " + styles.inputInvalid : "")
            }
            type="url"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://github.com/your-username/your-repository"
            spellCheck={false}
            readOnly={isChecking}
            aria-invalid={Boolean(displayedError)}
            aria-describedby={displayedError ? errorId : undefined}
          />

          {displayedError && (
            <p id={errorId} role="alert" className={styles.error}>
              {displayedError}
            </p>
          )}
        </div>

        <div className={styles.actions}>
          <NextButton
            loading={isChecking}
            loadingLabel="Checking repository"
          />
          <CancelButton to="/" />
        </div>
      </form>
    </PageLayout>
  );
};

export default NewProject;
