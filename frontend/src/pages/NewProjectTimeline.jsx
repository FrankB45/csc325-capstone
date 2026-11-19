import { useCallback, useRef, useState } from "react";
import { useProject } from "../hooks/useProject.js";
import { Link, useParams } from "react-router-dom";
import PageLayout from "../components/PageLayout/PageLayout.jsx";
import BackLink from "../components/BackLink/BackLink.jsx";
import DownloadButton from "../components/DownloadButton/DownloadButton.jsx";
import ModeToggle from "../components/ModeToggle/ModeToggle.jsx";
import CommitPreview from "../components/CommitPreview/CommitPreview.jsx";
import EmptyCommitSlot from "../components/EmptyCommitSlot/EmptyCommitSlot.jsx";
import Timeline from "../components/Timeline/Timeline.jsx";
import CommitOverlay from "../components/CommitOverlay/CommitOverlay.jsx";
import Modal from "../components/Modal/Modal.jsx";
import styles from "./ProjectTimeline.module.css";
import Toolbox from "../components/Toolbox/Toolbox.jsx";

const FULL_SCREENSHOT_VIEW_WIDTH = 1100;
const COMPARISON_PANEL_WIDTH = 760;
const SCREENSHOT_FRAME_PADDING = 5;
const SCREENSHOT_FRAME_GAP = 27;

const loadScreenshot = (src) => new Promise((resolve, reject) => {
  const image = new Image();
  image.onload = () => resolve(image);
  image.onerror = () => reject(new Error("A screenshot could not be loaded."));
  image.crossOrigin = "anonymous";
  image.src = src;
});

const createCanvas = (width, height) => {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Could not create the PNG image.");
  context.fillStyle = "#fefeff";
  context.fillRect(0, 0, width, height);
  return { canvas, context };
};

const canvasToBlob = (canvas) => new Promise((resolve, reject) => {
  canvas.toBlob((blob) => {
    if (blob) resolve(blob);
    else reject(new Error("Could not export the PNG image."));
  }, "image/png");
});

const savePng = async (canvas, filename) => {
  const blob = await canvasToBlob(canvas);
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
};

const saveScreenshot = (src, filename) => {
  const link = document.createElement("a");
  link.href = src;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
};

const captureProjectPage = async (fullScreenshotCommits = []) => {
  const { default: html2canvas } = await import("html2canvas");
  const page = document.querySelector("main");
  if (!page) throw new Error("Could not find the project page to export.");
  const stage = page.querySelector("[data-export-stage]");
  const timeline = page.querySelector("[data-export-timeline]");
  if (!timeline) throw new Error("Could not find the timeline to export.");
  let fullScreenshots = [];
  let previewCrops = [];
  let fullScreenshotLayoutHeight = 0;
  let fullScreenshotStageContentHeight = 0;
  const pageTop = page.getBoundingClientRect().top;
  const timelineBottom = timeline.getBoundingClientRect().bottom;
  const skippedBeforeTimelineHeight = Array.from(page.querySelectorAll("[data-export-ignore]"))
    .filter((element) => element.getBoundingClientRect().top < timeline.getBoundingClientRect().top)
    .reduce((height, element) => {
      const style = window.getComputedStyle(element);
      return height
        + element.getBoundingClientRect().height
        + Number.parseFloat(style.marginTop || "0")
        + Number.parseFloat(style.marginBottom || "0");
    }, 0);
  const content = page.querySelector("[data-export-content]");
  const bottomPadding = content
    ? Number.parseFloat(window.getComputedStyle(content).paddingBottom || "0")
    : 0;
  let captureHeight = Math.max(
    1,
    Math.ceil(timelineBottom - pageTop - skippedBeforeTimelineHeight + bottomPadding),
  );

  if (fullScreenshotCommits.length) {
    if (!stage) throw new Error("Could not find the commit preview area to export.");
    const stageWidth = Math.max(1, stage.clientWidth);
    const frameInset = SCREENSHOT_FRAME_PADDING * 2;
    const screenshotWidth = fullScreenshotCommits.length === 1
      ? Math.min(FULL_SCREENSHOT_VIEW_WIDTH, Math.max(1, stageWidth - frameInset))
      : Math.min(
        COMPARISON_PANEL_WIDTH,
        Math.max(1, (stageWidth - SCREENSHOT_FRAME_GAP - frameInset * 2) / 2),
      );
    fullScreenshots = await Promise.all(fullScreenshotCommits.map(async (commit) => {
      const image = await loadScreenshot(commit.image);
      const imageHeight = Math.max(
        1,
        Math.round(image.naturalHeight * screenshotWidth / image.naturalWidth),
      );
      const rendered = createCanvas(screenshotWidth, imageHeight);
      rendered.context.drawImage(image, 0, 0, screenshotWidth, imageHeight);
      return {
        commit,
        width: screenshotWidth,
        height: imageHeight,
        source: rendered.canvas.toDataURL("image/png"),
      };
    }));

    const stageStyle = window.getComputedStyle(stage);
    const stagePadding = Number.parseFloat(stageStyle.paddingTop)
      + Number.parseFloat(stageStyle.paddingBottom);
    fullScreenshotLayoutHeight = Math.max(...fullScreenshots.map((image) => image.height))
      + frameInset;
    const availableStageContentHeight = Math.max(
      0,
      stage.getBoundingClientRect().height - stagePadding,
    );
    fullScreenshotStageContentHeight = Math.max(
      fullScreenshotLayoutHeight,
      availableStageContentHeight,
    );
    const replacementHeight = fullScreenshotStageContentHeight + stagePadding;
    captureHeight += Math.ceil(Math.max(0, replacementHeight - stage.getBoundingClientRect().height));
  } else {
    const previewImages = Array.from(stage?.querySelectorAll("img") ?? []);
    previewCrops = await Promise.all(previewImages.map(async (preview) => {
      const source = await loadScreenshot(preview.currentSrc || preview.src);
      const bounds = preview.getBoundingClientRect();
      const width = Math.round(bounds.width);
      const height = Math.round(bounds.height);
      if (!width || !height) return null;

      const scale = Math.max(width / source.naturalWidth, height / source.naturalHeight);
      const sourceWidth = width / scale;
      const sourceHeight = height / scale;
      const sourceX = (source.naturalWidth - sourceWidth) / 2;
      const { canvas, context } = createCanvas(width, height);
      context.drawImage(source, sourceX, 0, sourceWidth, sourceHeight, 0, 0, width, height);
      return canvas.toDataURL("image/png");
    }));
  }

  return html2canvas(page, {
    backgroundColor: "#fefeff",
    height: captureHeight,
    useCORS: true,
    width: page.scrollWidth,
    windowHeight: Math.max(window.innerHeight, captureHeight),
    windowWidth: window.innerWidth,
    onclone: (clonedDocument) => {
      const clonedPage = clonedDocument.querySelector("main");
      clonedPage?.querySelectorAll("[data-export-ignore]").forEach((element) => element.remove());
      clonedPage?.querySelector('[aria-label="AI Assistant"]')?.remove();
      clonedPage?.querySelector('button[aria-label="Download PNG"]')?.remove();
      if (!fullScreenshots.length) {
        clonedPage?.querySelectorAll("[data-export-stage] img").forEach((image, index) => {
          if (previewCrops[index]) {
            image.src = previewCrops[index];
            image.style.objectFit = "fill";
          }
        });
      }
      clonedPage?.querySelectorAll('button[aria-label^="Scroll timeline"]').forEach((button) => {
        const label = button.getAttribute("aria-label") ?? "";
        const direction = label.endsWith("left") ? "left" : "right";
        const fill = clonedDocument.defaultView?.getComputedStyle(button).backgroundColor ?? "#ff7551";
        const svg = clonedDocument.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("viewBox", "0 0 37 62");
        svg.setAttribute("width", "37");
        svg.setAttribute("height", "62");
        svg.style.display = "block";
        svg.style.width = "100%";
        svg.style.height = "100%";

        const path = clonedDocument.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute(
          "d",
          direction === "left" ? "M37 0 0 31 37 62Z" : "M0 0 37 31 0 62Z",
        );
        path.setAttribute("fill", fill);
        svg.appendChild(path);
        button.style.backgroundColor = "transparent";
        button.style.clipPath = "none";
        button.replaceChildren(svg);
      });

      if (fullScreenshots.length) {
        const clonedStage = clonedPage?.querySelector("[data-export-stage]");
        const clonedContent = clonedPage?.querySelector("[data-export-content]");
        if (!clonedStage || !clonedContent) {
          throw new Error("Could not find the cloned commit preview area.");
        }
        const screenshotLayout = clonedDocument.createElement("div");
        screenshotLayout.style.display = "flex";
        screenshotLayout.style.flexDirection = fullScreenshots.length === 1 ? "column" : "row";
        screenshotLayout.style.justifyContent = "center";
        screenshotLayout.style.alignItems = fullScreenshots.length === 1 ? "center" : "flex-start";
        screenshotLayout.style.gap = `${SCREENSHOT_FRAME_GAP}px`;
        screenshotLayout.style.width = "100%";
        screenshotLayout.style.height = `${fullScreenshotLayoutHeight}px`;
        screenshotLayout.style.flex = "none";

        fullScreenshots.forEach(({ commit, width: imageWidth, height: imageHeight, source }) => {
          const panel = clonedDocument.createElement("div");
          const frameWidth = imageWidth + SCREENSHOT_FRAME_PADDING * 2;
          panel.style.boxSizing = "border-box";
          panel.style.width = `${frameWidth}px`;
          panel.style.height = `${imageHeight + SCREENSHOT_FRAME_PADDING * 2}px`;
          panel.style.flex = "none";   // was `0 0 ${frameWidth}px`
          panel.style.margin = "0";
          panel.style.padding = `${SCREENSHOT_FRAME_PADDING}px`;
          panel.style.borderRadius = "16px";
          panel.style.background = "linear-gradient(98.52deg, #F7B32B, #FF7F51)";
          panel.style.overflow = "hidden";
          const image = clonedDocument.createElement("img");
          image.src = source;
          image.alt = `Full screenshot for commit ${commit.sha.slice(0, 7)}`;
          image.style.display = "block";
          image.style.width = `${imageWidth}px`;
          image.style.height = `${imageHeight}px`;
          image.style.borderRadius = "11px";
          image.style.objectFit = "fill";
          panel.appendChild(image);
          screenshotLayout.appendChild(panel);
        });

        clonedStage.replaceChildren(screenshotLayout);
        clonedPage.style.minHeight = "0";
        clonedPage.style.height = "auto";
        clonedContent.style.flex = "none";
        clonedContent.style.minHeight = "0";
        clonedContent.style.height = "auto";
        clonedStage.style.boxSizing = "content-box";
        clonedStage.style.flex = "0 0 auto";
        clonedStage.style.height = `${fullScreenshotStageContentHeight}px`;
        clonedStage.style.minHeight = "0";
        clonedStage.style.maxHeight = "none";
        clonedStage.style.overflow = "visible";
        clonedStage.style.flexDirection = "column";
        clonedStage.style.alignItems = "center";
        clonedStage.style.justifyContent = "center";
      }
    },
  });
};

const drawWrappedText = (context, text, x, y, maxWidth, lineHeight, maxLines) => {
  const lines = [];
  let line = "";
  text.split(/\s+/).forEach((word) => {
    const candidate = line ? `${line} ${word}` : word;
    if (line && context.measureText(candidate).width > maxWidth) {
      lines.push(line);
      line = word;
    } else {
      line = candidate;
    }
  });
  if (line) lines.push(line);

  if (lines.length > maxLines) {
    let lastLine = lines[maxLines - 1];
    while (lastLine && context.measureText(`${lastLine}…`).width > maxWidth) {
      lastLine = lastLine.slice(0, -1);
    }
    lines[maxLines - 1] = `${lastLine}…`;
  }
  lines.slice(0, maxLines).forEach((value, index) => {
    context.fillText(value, x, y + index * lineHeight);
  });
};

const comparisonCanvas = (commits, images) => {
  const gap = 24;
  const padding = 24;
  const headerHeight = 126;
  const imageHeights = images.map((image) => (
    image.naturalHeight * COMPARISON_PANEL_WIDTH / image.naturalWidth
  ));
  const width = padding * 2 + COMPARISON_PANEL_WIDTH * 2 + gap;
  const height = padding * 2 + headerHeight + Math.max(...imageHeights);
  const { canvas, context } = createCanvas(width, height);

  commits.forEach((commit, index) => {
    const x = padding + index * (COMPARISON_PANEL_WIDTH + gap);
    context.fillStyle = "#0b2545";
    context.font = "700 20px Arial, sans-serif";
    context.textAlign = "left";
    context.fillText(`Commit ${index + 1}`, x, 28);
    context.font = "600 16px Arial, sans-serif";
    context.fillText(
      `${commit.sha.slice(0, 7)} · ${new Date(commit.date).toLocaleDateString("en-US")}`,
      x,
      56,
    );
    context.font = "15px Arial, sans-serif";
    drawWrappedText(context, commit.message, x, 82, COMPARISON_PANEL_WIDTH, 19, 2);
    context.drawImage(
      images[index],
      x,
      padding + headerHeight,
      COMPARISON_PANEL_WIDTH,
      imageHeights[index],
    );
  });
  return canvas;
};

const projectPageWithFullScreenshots = async (commits) => {
  return captureProjectPage(commits);
};

const ProjectTimelineView = ({ project, commits }) => {
  const analysis = project.analysis;
  const availablePages = analysis?.available_pages ?? [analysis?.page_path].filter(Boolean);
  const [requestedPage, setSelectedPage] = useState(
  analysis?.page_path || analysis?.default_page || availablePages[0] || "",
);
const selectedPage =
  availablePages.length > 0 && !availablePages.includes(requestedPage)
    ? availablePages[0]
    : requestedPage;
  const [mode, setMode] = useState("standard"); // "standard" | "compare"
  const [picks, setPicks] = useState(() => {
    const latestCaptured = commits.filter((commit) => commit.image).at(-1);

    return latestCaptured
      ? [latestCaptured.id, null]
      : [commits[0]?.id ?? null, null];
  });  
  const [activeSlot, setActiveSlot] = useState(null);
  const [overlayCommit, setOverlayCommit] = useState(null);
  const [downloadError, setDownloadError] = useState("");
  const [downloadDialogOpen, setDownloadDialogOpen] = useState(false);
  const modeRowRef = useRef(null);


  // Compare slots stay fixed: 1 is left and 2 is right.
  const shownIds = mode === "standard" ? picks.filter(Boolean).slice(-1) : picks.filter(Boolean);
  const shown = shownIds.map((id) => commits.find((commit) => commit.id === id)).filter(Boolean);
  const slotById = mode === "compare"
    ? Object.fromEntries(picks.flatMap((id, index) => id ? [[id, index + 1]] : []))
    : {};
  const compareSlotCommits = picks.map((id) => id
    ? commits.find((commit) => commit.id === id) ?? null
    : null);

  function handleModeChange(next) {
    const previousTop = modeRowRef.current?.getBoundingClientRect().top;
    setMode(next);
    setActiveSlot(null);
    setDownloadDialogOpen(false);
    setDownloadError("");
    if (next === "standard") setPicks((p) => [p.filter(Boolean).at(-1) ?? null, null]);
    if (previousTop !== undefined) {
      requestAnimationFrame(() => {
        const nextTop = modeRowRef.current?.getBoundingClientRect().top;
        if (nextTop !== undefined) window.scrollBy(0, nextTop - previousTop);
      });
    }
  }

  function handleSelect(id) {
    if (mode === "standard") {
      setPicks([id, null]);
      return;
    }
    if (!activeSlot) return;

    const targetIndex = activeSlot - 1;
    setPicks((prev) => {
      const next = [...prev];
      const otherIndex = 1 - targetIndex;
      if (next[otherIndex] === id) {
        if (!next[targetIndex]) return prev;
        next[otherIndex] = next[targetIndex];
      }
      next[targetIndex] = id;
      return next;
    });
    setActiveSlot(null);
  }

  const closeDownloadDialog = useCallback(() => setDownloadDialogOpen(false), []);

  async function handleDownload(type, commitToExport) {
    setDownloadError("");
    try {
      let canvas;
      let filename;

      if (type === "commit") {
        if (!commitToExport?.image) throw new Error("Select a commit with a screenshot to download.");
        saveScreenshot(commitToExport.image, `${project.id}-${commitToExport.sha}.png`);
        setDownloadDialogOpen(false);
        return;
      } else if (type === "comparison") {
        if (shown.length !== 2 || shown.some((commit) => !commit.image)) {
          throw new Error("Select two commits with screenshots to compare.");
        }
        const images = await Promise.all(shown.map((commit) => loadScreenshot(commit.image)));
        canvas = comparisonCanvas(shown, images);
        filename = `${project.id}-comparison.png`;
      } else if (type === "timeline") {
        canvas = await captureProjectPage();
        filename = `${project.id}-timeline.png`;
      } else if (type === "timeline-with-screenshots") {
        const screenshotCommits = mode === "compare" ? shown : [commitToExport ?? shown[0]].filter(Boolean);
        if (!screenshotCommits.length || screenshotCommits.some((commit) => !commit.image)) {
          throw new Error("Select commit screenshots before creating this download.");
        }
        canvas = await projectPageWithFullScreenshots(screenshotCommits);
        const suffix = screenshotCommits.map((commit) => commit.sha.slice(0, 7)).join("-");
        filename = `${project.id}-timeline-${suffix}.png`;
      } else {
        throw new Error("Choose a PNG export format.");
      }

      await savePng(canvas, filename);
      setDownloadDialogOpen(false);
    } catch (error) {
      console.error("Could not create the PNG download.", error);
      setDownloadError(error instanceof Error
        ? error.message
        : "Could not create the PNG download. Please try again.");
    }
  }



  return (
    <PageLayout width="timeline" watermark="center">
      <div className={styles.page} data-export-content>
        <p role="status" data-export-ignore>
          {analysis.status.replaceAll("_", " ")} —{" "}
          {analysis.progress.processed} / {analysis.progress.total} processed
          {" · "}
          {analysis.progress.failed} failed
          {selectedPage ? ` · HTML page: ${selectedPage}` : ""}
        </p>

        {analysis.error_message && (
          <p role="alert" data-export-ignore>{analysis.error_message}</p>
        )}
        <div className={styles.top}>
          <div>
            <div data-export-ignore>
              <BackLink to="/gallery">Back to Gallery</BackLink>
            </div>

            <div className={styles.titleRow}>
              <div className={styles.titleMeta}>
                <h1 className={styles.title}>{project.name}</h1>

                {availablePages.length > 1 && (
                  <label className={styles.pagePicker}>
                    HTML page
                    <select
                      value={selectedPage}
                      onChange={(event) => setSelectedPage(event.target.value)}
                      aria-label="Switch HTML page"
                    >
                      {availablePages.map((page) => (
                        <option key={page} value={page}>{page}</option>
                      ))}
                    </select>
                  </label>
                )}
              </div>

              <DownloadButton
                label="Download PNG"
                onClick={() => {
                  setDownloadError("");
                  setDownloadDialogOpen(true);
                }}
                disabled={!commits.length}
              />
            </div>
          </div>
        </div>

        <section
          className={styles.stage}
          aria-label="Selected commits"
          aria-live="polite"
          data-export-stage
        >
          {mode === "standard" ? (
            <div className={styles.single}>
              {shown[0] && <CommitPreview commit={shown[0]} onOpen={setOverlayCommit} selectedPage={selectedPage} />}
            </div>
          ) : (
            <div className={styles.pair}>
              {shown.map((c) => (
                <CommitPreview key={c.id} commit={c} onOpen={setOverlayCommit} selectedPage={selectedPage} />
              ))}
              {shown.length < 2 && (
                <EmptyCommitSlot
                  isPicking={activeSlot === 2}
                  onAdd={() => setActiveSlot(2)}
                />
              )}
            </div>
          )}
        </section>

        <div data-export-timeline>
          <Timeline
            commits={commits}
            selectedIds={shownIds}
            slotById={slotById}
            activeSlot={activeSlot}
            comparisonMode={mode === "compare"}
            onSelect={handleSelect}
            onAssignSlot={setActiveSlot}
          />
        </div>

        {commits.length > 1 && (
          <div ref={modeRowRef} className={styles.modeRow} data-export-ignore>
            <ModeToggle value={mode} onChange={handleModeChange} />
          </div>
        )}
        {overlayCommit && <CommitOverlay commit={overlayCommit} onClose={() => setOverlayCommit(null)} />}
        {downloadDialogOpen && (
          <Modal title="Download PNG" onClose={closeDownloadDialog}>
            <section className={styles.downloadDialog} aria-labelledby="download-title">
              <h2 id="download-title">Choose what to download</h2>
              <div className={styles.downloadOptions}>
                {mode === "compare"
                  ? compareSlotCommits.map((commit, index) => (
                    <button
                      key={index}
                      type="button"
                      disabled={!commit?.image}
                      onClick={() => handleDownload("commit", commit)}
                    >
                      Screenshot of selected commit {index + 1}
                    </button>
                  ))
                  : (
                    <button
                      type="button"
                      disabled={!shown[0]?.image}
                      onClick={() => handleDownload("commit", shown[0])}
                    >
                      Screenshot of commit
                    </button>
                  )}
                {mode === "compare" && (
                  <button
                    type="button"
                    disabled={shown.length !== 2 || shown.some((commit) => !commit.image)}
                    onClick={() => handleDownload("comparison")}
                  >
                    Two commits side by side with commit info
                  </button>
                )}
                <button type="button" onClick={() => handleDownload("timeline")}>
                  Timeline (project timeline page screenshot)
                </button>
                <button
                  type="button"
                  disabled={mode === "compare"
                    ? shown.length !== 2 || shown.some((commit) => !commit.image)
                    : !shown[0]?.image}
                  onClick={() => handleDownload("timeline-with-screenshots", shown[0])}
                >
                  {mode === "compare"
                    ? "Timeline with full screenshots of both commits"
                    : "Timeline with full commit screenshot"}
                </button>
              </div>
              {downloadError && <p role="alert">{downloadError}</p>}
            </section>
          </Modal>
        )}
        <Toolbox
          jobId={analysis.job_id}
          pagePath={analysis.page_path}
          mode={mode}
          commits={compareSlotCommits}
        />
      </div>
    </PageLayout>
  );
};

const ProjectTimelineLoader = ({ projectId }) => {
  const { project, error, isLoading } = useProject(projectId);

  if (isLoading) {
    return (
      <PageLayout width="narrow">
        <p role="status">Loading project…</p>
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout width="narrow">
        <p role="alert">{error}</p>
        <button onClick={() => window.location.reload()}>
          Retry
        </button>
      </PageLayout>
    );
  }

  if (!project.analysis) {
    return (
      <PageLayout width="narrow">
        <h1>{project.name}</h1>
        <p>This project has no analysis yet.</p>
        <Link to="/new-project">Create a new analysis</Link>
      </PageLayout>
    );
  }

  const commits = project.analysis.commits.map((commit) => ({
    ...commit,
    id: commit.sha,
    image: commit.screenshot_url,
  }));

  return (
    <ProjectTimelineView
      key={project.analysis.job_id}
      project={project}
      commits={commits}
    />
  );
};

const ProjectTimeline = () => {
  const { projectId } = useParams();

  return (
    <ProjectTimelineLoader
      key={projectId}
      projectId={projectId}
    />
  );
};

export default ProjectTimeline;
