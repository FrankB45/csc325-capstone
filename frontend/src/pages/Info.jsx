import PageLayout from "../components/PageLayout/PageLayout.jsx";
import styles from "./Info.module.css";

// NOTE: placeholder copy based on the README — replace with the final text from Figma.
const STEPS = [
  { title: "Add a repository", text: "Paste the link to a public GitHub repository (a simple HTML, CSS and JavaScript website)." },
  { title: "Choose commits", text: "Pick 1–10 commits to capture. We preselect a sensible set that includes the first and last." },
  { title: "Explore the timeline", text: "Browse screenshots, compare two commits side by side, and ask the AI Assistant what changed." },
];

const FAQ = [
  { q: "What is Git Gallery?", a: "Git Gallery turns a repository’s commit history into a visual timeline so designers and stakeholders can see how a site changed over time." },
  { q: "Which repositories work?", a: "Public GitHub repositories containing a simple HTML, CSS and JavaScript website." },
  { q: "How many commits can I capture?", a: "Between 1 and 10 per project." },
];

const Info = () => (
  <PageLayout width="narrow">
    <h1 className={styles.title}>About Git Gallery</h1>
    <p className={styles.lead}>
      Git shows developers text differences. Git Gallery shows everyone else what actually changed on the page.
    </p>

    <ol className={styles.steps}>
      {STEPS.map((s) => (
        <li key={s.title} className={styles.step}>
          <h2 className={styles.stepTitle}>{s.title}</h2>
          <p>{s.text}</p>
        </li>
      ))}
    </ol>

    <h2 className={styles.faqTitle}>Frequently Asked Questions</h2>
    {FAQ.map((f) => (
      <details key={f.q} className={styles.faq}>
        <summary>{f.q}</summary>
        <p>{f.a}</p>
      </details>
    ))}
  </PageLayout>
);

export default Info;
