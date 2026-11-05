import PageLayout from "../components/PageLayout/PageLayout.jsx";
import NewProjectButton from "../components/New Project Button/NewProjectButton.jsx";
import ViewGalleryButton from "../components/View Gallery Button/ViewGalleryButton.jsx";

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

function Home() {
  return (
    <PageLayout>
      <div className="hero">
        <h1 className="wordmark">GitGallery</h1>
        <p className="tagline">The visual way to explore your Git history</p>
        <div className="actions">
          <NewProjectButton />
          <ViewGalleryButton />
        </div>
      </div>
      <div className="features">
        {FEATURES.map((feature, index) => (
          <div key={index} className="feature">
            <h2 className="featureTitle">{feature.title}</h2>
            <p className="featureText">{feature.text}</p>
          </div>
        ))}
      </div>
    </PageLayout>
  );
}

export default Home;
