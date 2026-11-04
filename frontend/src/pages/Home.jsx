import Header from "../components/Header/Header.jsx";
import NewProjectButton from "../components/New Project Button/NewProjectButton.jsx";
import ViewGalleryButton from "../components/View Gallery Button/ViewGalleryButton.jsx";

function Home() {
  return (
    <div>
      <Header />
      <NewProjectButton />
      <ViewGalleryButton />
    </div>
  );
}

export default Home;
