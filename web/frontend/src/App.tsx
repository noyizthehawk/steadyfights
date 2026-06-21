import { Routes, Route, Link } from "react-router-dom";
import "./App.css";
import PredictorPage from "./pages/PredictorPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import FighterProfilePage from "./pages/FighterProfilePage";
import FightersPage from "./pages/FightersPage";
import PredictionGamePage from "./pages/PredictionGamePage";
import EventDetailPage from "./pages/EventDetailPage";

export default function App() {
  return (
    <>
      <nav className="nav">
        <div className="nav-left">
          <Link to="/">Predictor</Link>
          <Link to="/fighters">Career Analyzer</Link>
          <Link to="/prediction-game">Prediction Game</Link>
        </div>
        <div className="nav-right">
          <Link to="/login">Log in</Link>
          <Link to="/signup">Sign up</Link>
        </div>
      </nav>

      <Routes>
        <Route path="/" element={<PredictorPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/fighters" element={<FightersPage />} />
        <Route path="/fighters/:id/career" element={<FighterProfilePage />} />
        <Route path="/prediction-game" element={<PredictionGamePage />} />
        <Route path="/events/:slug" element={<EventDetailPage />} />
      </Routes>
    </>
  );
}
