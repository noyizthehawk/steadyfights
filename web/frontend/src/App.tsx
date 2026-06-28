import { Routes, Route, Link, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import "./App.css";
import PredictorPage from "./pages/PredictorPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import FighterProfilePage from "./pages/FighterProfilePage";
import FightersPage from "./pages/FightersPage";
import PredictionGamePage from "./pages/PredictionGamePage";
import EventDetailPage from "./pages/EventDetailPage";
import LeaderBoardPage from "./pages/LeaderBoardPage";
import UserCardPage from "./pages/UserCardPage";
import FriendsPage from "./pages/FriendsPage";
import TopCareerPage from "./pages/TopCareerPage";
import LandingPage from "./pages/LandingPage";
import UserEventDetailPage from "./pages/UserEventDetailPage";
import UserPastEvents from "./pages/UserPastEvents";
import { me, logout } from "./api";

export default function App() {
  // the logged-in user's email, or null when logged out
  const [email, setEmail] = useState<string | null>(null);
  // the logged-in user's id — used to link to their own past events
  const [userId, setUserId] = useState<number | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  // re-check auth on every route change so the nav updates right after login
  useEffect(() => {
    me()
      .then((u) => {
        setEmail(u.email);
        setUserId(u.id);
      })
      .catch(() => {
        setEmail(null);
        setUserId(null);
      });
  }, [location.pathname]);

  async function handleLogout() {
    await logout();
    setEmail(null);
    setUserId(null);
    setMenuOpen(false);
    navigate("/");
  }

  return (
    <>
      <nav className="nav">
        <div className="nav-left">
          <Link to="/">Home</Link>
          <Link to="/predictor">Predictor</Link>
          <Link to="/fighters">Fighter Cards</Link>
          <Link to="/prediction-game">Casual Checker</Link>
          <Link to="/leaderboard">Leaderboard</Link>
          <Link to="/friends">Friends</Link>
          <Link to="/top-career">Top Career</Link>
          {userId !== null && (
            <Link to={`/users/${userId}/events`}>Past Events</Link>
          )}
        </div>
        <div className="nav-right">
          {email ? (
            <div className="relative">
              <button
                className="nav-email cursor-pointer"
                onClick={() => setMenuOpen((o) => !o)}
              >
                {email} ▾
              </button>
              {menuOpen && (
                <div className="absolute right-0 z-50 mt-2 w-40 rounded-md border border-zinc-700 bg-zinc-900 shadow-lg">
                  <button
                    className="block w-full px-4 py-2 text-left text-sm text-white hover:bg-zinc-800"
                    onClick={handleLogout}
                  >
                    Log out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <Link to="/login">Log in</Link>
              <Link to="/signup">Sign up</Link>
            </>
          )}
        </div>
      </nav>

      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/fighters" element={<FightersPage />} />
        <Route path="/fighters/:id/career" element={<FighterProfilePage />} />
        <Route path="/prediction-game" element={<PredictionGamePage />} />
        <Route path="/events/:slug" element={<EventDetailPage />} />
        <Route path="/leaderboard" element={<LeaderBoardPage />} />
        <Route path="/users" element={<UserCardPage />} />
        <Route path="/users/:start" element={<UserCardPage />} />
        <Route path="/users/:userId/events" element={<UserPastEvents />} />
        <Route path="/users/:userId/events/:eventId" element={<UserEventDetailPage />} />
        <Route path="/friends" element={<FriendsPage />} />
        <Route path="/top-career" element={<TopCareerPage />} />
        <Route path="/predictor" element={<PredictorPage />} />
      </Routes>
    </>
  );
}
