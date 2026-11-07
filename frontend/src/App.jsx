import Home from "./pages/Home.jsx";
import Info from "./pages/Info.jsx";
import NewProject from "./pages/NewProject.jsx";
import Gallery from "./pages/Gallery.jsx";
import ProjectTimeline from "./pages/NewProjectTimeline.jsx";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/info" element={<Info />} />
        <Route path="/new-project" element={<NewProject />} />
        <Route path="/gallery" element={<Gallery />} />
        <Route path="/projects/:projectId/timeline" element={<ProjectTimeline />} />
        <Route path="/gallery/:projectId/timeline" element={<ProjectTimeline />} />
        <Route path="/gallery/:projectId" element={<Info />} />
      
      </Routes>
    </BrowserRouter>
  );
}

export default App;
