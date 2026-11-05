import { useEffect, useId, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import PageLayout from "../components/PageLayout/PageLayout.jsx";
import Button from "../components/New Project Button/NewProjectButton.jsx";
import Spinner from "../components/Spinner/Spinner.jsx";
import CommitPicker from "../components/CommitPicker/CommitPicker.jsx";
import { useRepositoryLookup } from "../hooks/useRepositoryLookup.js";
import { MOCK_COMMITS } from "../data/mock.js";
import { MIN_COMMITS, preselectCommits } from "../utils/commits.js";
import styles from "./NewProject.module.css";

const NewProject = () => {
  const navigate = useNavigate();
  const urlId = useId();
  const titleId = useId();
  const errorId = useId();

  const { status, repository, error, lookup, reset } = useRepositoryLookup();
  const [step, setStep] = useState("url"); // "url" | "setup" | "creating"
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");

  // TODO: load the repository's real commits from the backend; mock list for now.
  const commits = MOCK_COMMITS;
  const defaultSelection = useMemo(() => preselectCommits(commits), [commits]);
  const [selectedIds, setSelectedIds] = useState(defaultSelection);

  // TODO: POST the project (url, title, selectedIds) to the backend, then navigate to the new project's id.
  useEffect(() => {
    if (step !== "creating") return;
    const timer = setTimeout(() => navigate("/projects/personal-website"), 2000);
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

  if (step === "creating") {
    return (
      <PageLayout width="narrow">
        <div className={styles.creating} role="status">
          <h1 className={styles.creatingTitle}>Creating Timeline</h1>
          <Spinner size={56} label="Creating timeline" />
        </div>
      </PageLayout>
    );
  }

  if (step === "setup") {
    return (
      <PageLayout width="narrow">
        <h1 className={styles.title}>New Project</h1>
        <form className={styles.form} onSubmit={handleSetupSubmit}>
          <div className={styles.field}>
            <span className={styles.label}>GitHub Repository URL</span>
            <p className={styles.readonly}>{repository?.url ?? url}</p>
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor={titleId}>Project Title</label>
            <input
              id={titleId}
              className={styles.input}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          <CommitPicker commits={commits} selectedIds={selectedIds} onChange={setSelectedIds} />

          <div className={styles.actions}>
            <NewProjectButton type="submit" size="md" disabled={selectedIds.length < MIN_COMMITS || !title.trim()}>
              Create Project
            </NewProjectButton>
            <Button
              variant="ghost"
              onClick={() => {
                reset();
                setStep("url");
              }}
            >
              Back
            </Button>
          </div>
        </form>
      </PageLayout>
    );
  }

  const isInvalid = status === "invalid";

  return (
    <PageLayout width="narrow">
      <h1 className={styles.title}>New Project</h1>
      <form className={styles.form} onSubmit={handleUrlSubmit} noValidate>
        <div className={styles.field}>
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
            disabled={status === "loading"}
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
          <Button type="submit" size="md" loading={status === "loading"}>Next</Button>
          <Button to="/" variant="ghost">Cancel</Button>
        </div>
      </form>
    </PageLayout>
  );
};

export default NewProject;
