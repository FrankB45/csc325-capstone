import { useEffect, useId, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import PageLayout from "../components/PageLayout/PageLayout.jsx";
import NextButton from "../components/NextButton/NextButton.jsx";
import CancelButton from "../components/CancelButton/CancelButton.jsx";
import Spinner from "../components/Spinner/Spinner.jsx";
import CommitPicker from "../components/CommitPicker/CommitPicker.jsx";
import { useRepositoryLookup } from "../hooks/useRepositoryLookup.js";
import { MIN_COMMITS, MAX_COMMITS } from "../utils/commits.js";
import {
  findNewUpdateAttempt,
  isValidUpdateReview,
  NO_NEW_UPDATE_MESSAGE,
  postJSON,
  prepareProjectSetup,
  submitProjectUpdate,
} from "../utils/projectSetup.js";
import styles from "./NewProject.module.css";
import watermark from "../assets/octocat-watermark.svg";

const UNKNOWN_OUTCOME_MESSAGE =
  "We couldn't confirm whether the update was started. Your current results are unchanged. " +
  "Submitting again now could start a second update.";

const NewProject = (props) => {
  const {
    updateReview,
    onCancelReview,
    onUpdateAccepted,
    onUpdateUnconfirmed,
    onReturnToProject,
  } = props;
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
  // Update review only: "reviewing" | "saving" | "unconfirmed" | "checking".
  // "unconfirmed" means the update request may or may not have reached the server.
  const [updateState, setUpdateState] = useState("reviewing");
  const [hasSentUpdate, setHasSentUpdate] = useState(false);
  const isSaving = updateState === "saving";
  const isUnconfirmed = updateState === "unconfirmed" || updateState === "checking";
  const isLocked = isSaving || isUnconfirmed;

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

  // Save update is the confirmation. The request is sent once and never retried automatically.
  async function handleReviewSubmit(event) {
    event.preventDefault();
    if (updateState !== "reviewing" || requestRef.current || !canSubmit) return;

    const controller = new AbortController();
    requestRef.current = controller;
    setError("");
    setHasSentUpdate(true);
    setUpdateState("saving");

    try {
      const result = await submitProjectUpdate(
        { ...review, pagePath, selectedIds },
        controller.signal
      );
      if (controller.signal.aborted || requestRef.current !== controller) return;

      onUpdateAccepted(result.jobId);
    } catch (err) {
      if (controller.signal.aborted || requestRef.current !== controller) return;

      if (err.outcomeUnknown === false) {
        // The server clearly refused the update, so nothing was started.
        setError(err.message || "The update could not be started.");
        setUpdateState("reviewing");
      } else {
        setError(UNKNOWN_OUTCOME_MESSAGE);
        setUpdateState("unconfirmed");
        onUpdateUnconfirmed();
      }
    } finally {
      if (requestRef.current === controller) requestRef.current = null;
    }
  }

  // Reads the project once. A new update attempt means the earlier request did arrive.
  async function handleCheckAgain() {
    if (updateState !== "unconfirmed" || requestRef.current) return;

    const controller = new AbortController();
    requestRef.current = controller;
    setUpdateState("checking");

    try {
      const attempt = await findNewUpdateAttempt(
        review.sourceProjectId,
        review.sourceAttemptJobId,
        controller.signal
      );
      if (controller.signal.aborted || requestRef.current !== controller) return;

      if (attempt) {
        onUpdateAccepted(attempt.job_id);
      } else {
        setError(NO_NEW_UPDATE_MESSAGE);
        setUpdateState("unconfirmed");
      }
    } catch (err) {
      if (controller.signal.aborted || requestRef.current !== controller) return;

      setError(err.message || "Could not check the project. Please try again.");
      setUpdateState("unconfirmed");
    } finally {
      if (requestRef.current === controller) requestRef.current = null;
    }
  }

  const hasReviewCallbacks = [
    onCancelReview,
    onUpdateAccepted,
    onUpdateUnconfirmed,
    onReturnToProject,
  ].every((callback) => typeof callback === "function");

  if (isUpdateReview && (!review || !hasReviewCallbacks)) {
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
              disabled={isLocked}
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
            <p id={reviewNoticeId}>
              Saving starts a new analysis of the selected commits. Your current results stay visible until it succeeds.
            </p>
          ) : <p>Screenshots will appear after you create the project.</p>}

          {isSaving && (
            <p role="status">
              Starting update… Leaving this page stops waiting for the reply, but it does not
              cancel an update the server has already accepted.
            </p>
          )}

          {/* While saving or unconfirmed the selection is locked, so it matches what was sent. */}
          <CommitPicker
            commits={commits}
            selectedIds={selectedIds}
            onChange={(ids) => { if (!isLocked) setSelectedIds(ids); }}
          />

          {displayedError && (
            <p role="alert" className={styles.error}>
              {displayedError}
            </p>
          )}

          <div className={styles.actions}>
            {isUpdateReview ? (
              <>
                {isUnconfirmed ? (
                  <NextButton
                    type="button"
                    loading={updateState === "checking"}
                    loadingLabel="Checking for the update"
                    onClick={handleCheckAgain}
                  >
                    Check again
                  </NextButton>
                ) : (
                  <NextButton
                    loading={isSaving}
                    loadingLabel="Saving update"
                    disabled={!canSubmit}
                    aria-describedby={reviewNoticeId}
                  >
                    Save update
                  </NextButton>
                )}
                {/* After a request was sent, leaving also reloads the project's current state. */}
                <CancelButton
                  disabled={isSaving}
                  onClick={hasSentUpdate ? onReturnToProject : onCancelReview}
                >
                  {isUnconfirmed ? "Back to project" : "Cancel"}
                </CancelButton>
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
