// Temporary data so the screens render without a backend.
// Replace with real API calls (see hooks/useProjects.js).
import screenshot from "../assets/c332a341bb567f90830be6cd8d3e7295a99c24c9.png";

export const MOCK_PROJECTS = [
  {
    id: "personal-website",
    name: "Personal Website",
    lastModified: "2025-08-13",
    commitCount: 11,
    thumbnail: screenshot,
    description:
      "Welcome to my personal portfolio. I am a Full-Stack Developer specializing in building scalable web applications, intuitive user interfaces, and efficient software solutions.",
  },
  {
    id: "to-do-list",
    name: "To-Do List",
    lastModified: "2024-12-28",
    commitCount: 7,
    thumbnail: screenshot,
    description:
      "Streamline your day and get things done. To-Do List is a simple, intuitive task manager built to help you organize daily tasks, set priorities, and stay focused.",
  },
  {
    id: "weather-app",
    name: "Weather App",
    lastModified: "2025-09-26",
    commitCount: 9,
    thumbnail: screenshot,
    description: "",
  },
];

const MESSAGES = [
  "Initial commit",
  "Add navigation bar",
  "Style hero section",
  "Add projects grid",
  "Responsive layout",
  "Add contact form",
  "Polish footer",
  "Update colors",
  "Fix mobile menu",
  "Add dark section",
  "Final tweaks",
];

export const MOCK_COMMITS = MESSAGES.map((message, i) => ({
  id: `c${i + 1}`,
  sha: (0xa1b2c3 + i * 7919).toString(16).padStart(7, "0"),
  message,
  date: new Date(2025, 0, 5 + i * 9).toISOString(),
  image: screenshot,
}));

export function getMockCommits(projectId) {
  return MOCK_PROJECTS.some((project) => project.id === projectId) ? MOCK_COMMITS : [];
}
