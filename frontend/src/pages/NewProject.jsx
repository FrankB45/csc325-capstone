import { useEffect, useId, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import PageLayout from "../components/PageLayout/PageLayout.jsx";
import NextButton from "../components/NextButton/NextButton.jsx";
import CancelButton from "../components/CancelButton/CancelButton.jsx";
import Spinner from "../components/Spinner/Spinner.jsx";
import CommitPicker from "../components/CommitPicker/CommitPicker.jsx";
import { useRepositoryLookup } from "../hooks/useRepositoryLookup.js";
import { MIN_COMMITS, MAX_COMMITS } from "../utils/commits.js";
import { isValidUpdateReview, postJSON, prepareProjectSetup } from "../utils/projectSetup.js";
import styles from "./NewProject.module.css";
import watermark from "../assets/octocat-watermark.svg";

const NewProject = (props) => {
  const { updateReview, onCancelReview } = props;
  // Even an invalid explicit review prop must never fall back to project creation.
  const isUpdateReview = "updateReview" in props || "onCancelReview" in props;
  const review = isValidUpdateReview(updateReview) ? updateReview : null;
  const navigate = useNavigate();
  const urlId = useId();
  const titleId = useId();
  const errorId = useId();
  const pageId = useId();
  const reviewNoticeId = useId();

  const requestRef = useRef(null);

  const { repository, error: lookupError, lookup, reset } = useRepositoryLookup();
  const [step, setStep] = useState(review ? "setup" : "url"); // "url" | "setup" | "creating"
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState(review?.projectTitle || "");
  const [pages, setPages] = useState(() => review ? [...review.pages] : []);
  const [pagePath, setPagePath] = useState(review?.pagePath || "");
  const [commits, setCommits] = useState(() => review ? [...review.commits] : []);
  const [selectedIds, setSelectedIds] = useState(() => review ? [...review.selectedIds] : []);
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
    if (isUpdateReview || requestRef.current) return;

    const controller = new AbortController();
    requestRef.current = controller;
    setIsChecking(true);
    setError("");

    try {
      const repo = await lookup(url);
      if (!repo || controller.signal.aborted) return;

      const setup = await prepareProjectSetup(repo.url, controller.signal);

      if (controller.signal.aborted) return;

      setTitle(repo.name);
      setPages(setup.pages);
      setPagePath(setup.pagePath);
      setCommits(setup.commits);
      setSelectedIds(setup.selectedIds);
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
    if (isUpdateReview) return;
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

  function handleReviewSubmit(event) {
    event.preventDefault();
  }

  if (isUpdateReview && (!review || typeof onCancelReview !== "function")) {
    return (
      <PageLayout width="narrow" watermark>
        <h1 className={styles.title}>Review update</h1>
        <p role="alert" className={styles.error}>
          Update review could not be opened. Return to the project and check again.
        </p>
        {typeof onCancelReview === "function"
          ? <CancelButton onClick={onCancelReview} />
          : <CancelButton to="/gallery">Back to Gallery</CancelButton>}
      </PageLayout>
    );
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
        <h1 className={styles.title}>{isUpdateReview ? "Review update" : "New Project"}</h1>
        <form className={styles.form} onSubmit={isUpdateReview ? handleReviewSubmit : handleSetupSubmit}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor={urlId}>GitHub Repository URL</label>
            <input
              id={urlId}
              className={styles.input}
              value={isUpdateReview ? review.repositoryUrl : repository.url}
              readOnly
            />

            {!isUpdateReview && (
              <CancelButton onClick={changeUrl}>
                Change repository
              </CancelButton>
            )}

          </div>

          <div className={`${styles.field} ${styles.titleField}`}>
            <label className={styles.label} htmlFor={titleId}>Project Title</label>
            <input
              id={titleId}
              className={styles.input}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              readOnly={isUpdateReview}
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

          {isUpdateReview ? (
            <p id={reviewNoticeId} role="status">
              Review only. Saving updates is not available yet. Cancel returns to your saved project.
            </p>
          ) : <p>Screenshots will appear after you create the project.</p>}

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
            {isUpdateReview ? (
              <>
                <NextButton type="button" disabled aria-describedby={reviewNoticeId}>
                  Save update
                </NextButton>
                <CancelButton onClick={onCancelReview} />
              </>
            ) : (
              <>
                <NextButton disabled={!canSubmit}>Create project</NextButton>
                <CancelButton to="/" />
              </>
            )}
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
