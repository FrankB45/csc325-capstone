import Home from "./pages/Home.jsx";
import Info from "./pages/Info.jsx";
import NewProject from "./pages/NewProject.jsx";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/info" element={<Info />} />
        <Route path="/new-project" element={<NewProject />} />
        <Route path="/gallery/:projectId" element={<Info />} />
      
      </Routes>
    </BrowserRouter>
  );
}

export default App;
