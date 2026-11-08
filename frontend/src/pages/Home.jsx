import PageLayout from "../components/PageLayout/PageLayout.jsx";
import NewProjectButton from "../components/New Project Button/NewProjectButton.jsx";
import ViewGalleryButton from "../components/View Gallery Button/ViewGalleryButton.jsx";
import wordmark from "../assets/GitGallery-wordmark.svg";
import watermark from "../assets/octocat-watermark.svg";
import styles from "./Home.module.css";

const FEATURES = [
  {
    title: "Visual Timeline",
    text: "Browse every commit as a visual screenshot, not a wall of diffs. Understand the evolution of your project at a glance.",
  },
  {
    title: "AI-Powered Insights",
    text: "AI groups commits into milestones, highlights what changed visually, and explains each change in plain language.",
  },
];

const Home = () => (
  <PageLayout width="full">
    <div className={styles.page}>
      {/* decorative background mark, clipped by the right edge of the page */}
      <img className={styles.watermark} src={watermark} alt="" aria-hidden="true" />

      <div className={styles.content}>
        <section className={styles.hero}>
          <h1 className={styles.title}>
            <img className={styles.wordmark} src={wordmark} alt="GitGallery" />
          </h1>
          <p className={styles.tagline}>Visual commit history for designers &amp; stakeholders</p>

          <div className={styles.actions}>
            <NewProjectButton />
            <ViewGalleryButton />
          </div>
        </section>

        <section className={styles.features} aria-label="Features">
          {FEATURES.map((f) => (
            <article key={f.title} className={styles.feature}>
              <h2 className={styles.featureTitle}>{f.title}</h2>
              <p className={styles.featureText}>{f.text}</p>
            </article>
          ))}
        </section>
      </div>
    </div>
  </PageLayout>
);

export default Home;
