import PageLayout from "../components/PageLayout/PageLayout.jsx";
import FaqItem from "../components/FaqItem/FaqItem.jsx";
import AssistantChat from "../components/AssistantChat/AssistantChat.jsx";
import styles from "./Info.module.css";

const STEPS = [
  { n: "01", title: "Paste a repo link", text: "Submit a public GitHub URL for a static HTML/CSS/JS site." },
  { n: "02", title: "AI selects commits", text: "The AI groups commits into milestones and picks the most visually significant ones." },
  { n: "03", title: "Browse the timeline", text: "Tap any dot to see a screenshot of the site at that commit. Compare any two snapshots side by side." },
];

const FAQ = [
  {
    q: "What is Git Gallery?",
    a: "Git Gallery is a visual version control explorer designed for non-technical stakeholders. Instead of reading code diffs, you browse screenshots of your website at every commit — so designers, managers, and clients can follow a project’s evolution without any Git knowledge.",
  },
  {
    q: "What kind of repositories does Git Gallery support?",
    a: "Git Gallery works with public GitHub repositories that contain a simple HTML, CSS, and JavaScript website. The repo must have an index.html at the root and no server-side rendering — it needs to run as a static site so we can screenshot it reliably.",
  },
  {
    q: "How does the AI assistant work?",
    a: "The AI reviews commit messages and code changes to group consecutive commits into thematic milestones (e.g. “Foundation”, “Content”, “Polish”). When you select two commits to compare, it describes the visible differences in plain language — no code reading required.",
  },
  {
    q: "Can I use private repositories?",
    a: "Not yet. Git Gallery currently requires a publicly accessible repository so it can fetch and render the site for screenshots. Support for private repos with a personal access token is on our roadmap.",
  },
  {
    q: "How many commits can a project have?",
    a: "There is no hard limit, but for best performance we recommend repositories with fewer than 200 commits. Very large histories are summarised — the AI picks the most visually significant commits so the timeline stays navigable.",
  },
  {
    q: "Is my repository data stored anywhere?",
    a: "Git Gallery only reads publicly available data from GitHub. Screenshots are generated on-demand and cached temporarily. We do not store your source code or commit history on our servers beyond the current session.",
  },
];

const REQUIREMENTS = [
  "Public GitHub repository",
  "Static site: HTML, CSS, JavaScript only",
  "index.html at the repository root",
  "No server-side rendering or build step required",
  "No external assets loaded from authenticated sources",
];

const CheckIcon = () => (
  <svg className={styles.check} viewBox="0 0 16 16" width="14" height="14" fill="none" aria-hidden="true">
    <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.2" />
    <path d="M5 8.2l2 2 4-4.2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

// TODO: send the question to the backend AI endpoint.
const askAssistant = async () => "The assistant isn’t connected to the backend yet.";

const Info = () => (
  <PageLayout width="xwide">
    <div className={styles.page}>
      <h1 className={styles.title}>About Git Gallery</h1>
      <p className={styles.intro}>
        Git Gallery turns a developer tool — version control — into a visual story anyone can follow.
        Below you’ll find answers to common questions, and an AI assistant ready to help.
      </p>

      <h2 className={styles.heading}>How it works</h2>
      <ol className={styles.steps}>
        {STEPS.map((s) => (
          <li key={s.n} className={`${styles.gradientBox} ${styles.step}`}>
            <span className={styles.stepNumber}>{s.n}</span>
            <h3 className={styles.stepTitle}>{s.title}</h3>
            <p className={styles.stepText}>{s.text}</p>
          </li>
        ))}
      </ol>

      <h2 className={styles.heading}>Frequently Asked Questions</h2>
      <div className={styles.faq}>
        {FAQ.map((f) => (
          <FaqItem key={f.q} question={f.q}>{f.a}</FaqItem>
        ))}
      </div>

      <h2 className={`${styles.heading} ${styles.assistantHeading}`}>Ask the AI Assistant</h2>
      <p className={styles.sub}>Can’t find your answer above? Ask the assistant anything about Git Gallery.</p>
      <AssistantChat onAsk={askAssistant} />

      <section className={`${styles.gradientBox} ${styles.requirements}`} aria-labelledby="repo-reqs">
        <h2 id="repo-reqs" className={styles.reqTitle}>Repository requirements</h2>
        <ul className={styles.reqList}>
          {REQUIREMENTS.map((r) => (
            <li key={r}><CheckIcon />{r}</li>
          ))}
        </ul>
      </section>
    </div>
  </PageLayout>
);

export default Info;
