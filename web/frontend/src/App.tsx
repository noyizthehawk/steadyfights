import { Routes, Route, Link } from "react-router-dom";
import "./App.css";
import PredictorPage from "./pages/PredictorPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";

export default function App() {
  return (
    <>
      <nav className="nav">
        <Link to="/">Predictor</Link>
        <Link to="/login">Log in</Link>
        <Link to="/signup">Sign up</Link>
      </nav>

      <Routes>
        <Route path="/" element={<PredictorPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
      </Routes>
    </>
  );
}
