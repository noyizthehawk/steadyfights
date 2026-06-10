import "./App.css";
import PredictorPage from "./pages/PredictorPage";

// App is now just the "shell": it loads global styles and renders the page.
// When we add routing, the router goes here and decides which page to show.
export default function App() {
  return <PredictorPage />;
}
