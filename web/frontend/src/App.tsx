import { Routes, Route, Link } from "react-router-dom";
import "./App.css";
import PredictorPage from "./pages/PredictorPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import FighterProfilePage from "./pages/FighterProfilePage";
import FightersPage from "./pages/FightersPage";

export default function App() {
  return (
    <>
      <nav className="nav">
        <Link to="/">Predictor</Link>
        <Link to="/fighters">Career Analyzer</Link>
        <Link to="/login">Log in</Link>
        <Link to="/signup">Sign up</Link>
      </nav>

      <Routes>
        <Route path="/" element={<PredictorPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/fighters" element={<FightersPage />} />
        <Route path="/fighters/:id/career" element={<FighterProfilePage />} />
      </Routes>
    </>
  );
}
