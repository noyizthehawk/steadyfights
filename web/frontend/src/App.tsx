import { Routes, Route, Link } from "react-router-dom";
import "./App.css";
import PredictorPage from "./pages/PredictorPage";
import LoginPage from "./pages/LoginPage";

// App is now the route table: it maps each URL to a page.
// <Link> navigates WITHOUT a full page reload (the React way); a plain <a> would
// reload everything and wipe your app's state.
export default function App() {
  return (
    <>
      <nav className="nav">
        <Link to="/">Predictor</Link>
        <Link to="/login">Log in</Link>
      </nav>

      <Routes>
        <Route path="/" element={<PredictorPage />} />
        <Route path="/login" element={<LoginPage />} />
        {/* Add when you build it: <Route path="/signup" element={<SignupPage />} /> */}
      </Routes>
    </>
  );
}
