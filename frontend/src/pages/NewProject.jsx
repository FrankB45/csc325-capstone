import { useEffect, useId, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import PageLayout from "../components/PageLayout/PageLayout.jsx";
import NextButton from "../components/NextButton/NextButton.jsx";
import CancelButton from "../components/CancelButton/CancelButton.jsx";
import Spinner from "../components/Spinner/Spinner.jsx";
import CommitPicker from "../components/CommitPicker/CommitPicker.jsx";
import { useRepositoryLookup } from "../hooks/useRepositoryLookup.js";
import { MOCK_COMMITS } from "../data/mock.js";
import { MIN_COMMITS, preselectCommits } from "../utils/commits.js";
import styles from "./NewProject.module.css";
import watermark from "../assets/octocat-watermark.svg";

const NewProject = () => {
  const navigate = useNavigate();
  const urlId = useId();
  const titleId = useId();
  const errorId = useId();

  const { status, repository, error, lookup, reset } = useRepositoryLookup();
  const [step, setStep] = useState("url"); // "url" | "setup" | "creating"
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");

  // TODO: load the repository's real commits + preview screenshot from the backend; mock data for now.
  const commits = MOCK_COMMITS;
  const previewImage = commits[commits.length - 1].image;
  const defaultSelection = useMemo(() => preselectCommits(commits), [commits]);
  const [selectedIds, setSelectedIds] = useState(defaultSelection);

  // TODO: POST the project (url, title, selectedIds) to the backend, then navigate to the new project's id.
  useEffect(() => {
    if (step !== "creating") return;
    const timer = setTimeout(() => navigate("/projects/personal-website/timeline"), 2000);
    return () => clearTimeout(timer);
  }, [step, navigate]);

  async function handleUrlSubmit(e) {
    e.preventDefault();
    const repo = await lookup(url);
    if (repo) {
      setTitle(repo.name);
      setStep("setup");
    }
  }

  function handleSetupSubmit(e) {
    e.preventDefault();
    if (selectedIds.length >= MIN_COMMITS && title.trim()) setStep("creating");
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
              className={`${styles.input} ${styles.inputReadonly}`}
              value={repository?.url ?? url}
              readOnly
              title="Click to change the repository"
              onClick={changeUrl}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  changeUrl();
                }
              }}
            />
          </div>

          <div className={`${styles.field} ${styles.titleField}`}>
            <label className={styles.label} htmlFor={titleId}>Project Title</label>
            <input
              id={titleId}
              className={styles.input}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          <div className={styles.preview}>
            <img src={previewImage} alt={`Preview of ${title || "the project"}`} />
          </div>

          <CommitPicker commits={commits} selectedIds={selectedIds} onChange={setSelectedIds} />

          <div className={styles.actions}>
            <NextButton disabled={selectedIds.length < MIN_COMMITS || !title.trim()} />
            <CancelButton to="/" />
          </div>
        </form>
      </PageLayout>
    );
  }

  const isInvalid = status === "invalid";

  return (
    <PageLayout width="narrow" watermark>
      <h1 className={styles.title}>New Project</h1>
      <form className={styles.form} onSubmit={handleUrlSubmit} noValidate>
        <div className={`${styles.field} ${styles.urlStep}`}>
          <label className={styles.label} htmlFor={urlId}>GitHub Repository URL</label>
          <input
            id={urlId}
            className={`${styles.input} ${isInvalid ? styles.inputInvalid : ""}`}
            type="url"
            inputMode="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/your-username/your-repository"
            spellCheck={false}
            readOnly={status === "loading"}
            aria-invalid={isInvalid}
            aria-describedby={isInvalid ? errorId : undefined}
          />
          {isInvalid && (
            <p id={errorId} role="alert" className={styles.error}>
              Error: {error}
            </p>
          )}
        </div>

        <div className={styles.actions}>
          <NextButton loading={status === "loading"} loadingLabel="Checking repository" />
          <CancelButton to="/" />
        </div>
      </form>
    </PageLayout>
  );
};

export default NewProject;
