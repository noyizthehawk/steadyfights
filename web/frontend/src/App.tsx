import { Routes, Route, Link, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import "./App.css";
import PredictorPage from "./pages/PredictorPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import FighterProfilePage from "./pages/FighterProfilePage";
import FightersPage from "./pages/FightersPage";
import PredictionGamePage from "./pages/PredictionGamePage";
import EventDetailPage from "./pages/EventDetailPage";
import LeaderBoardPage from "./pages/LeaderBoardPage";
import ProfilePage from "./pages/ProfilePage";
import FriendsPage from "./pages/FriendsPage";
import TopCareerPage from "./pages/TopCareerPage";
import LandingPage from "./pages/LandingPage";
import UserEventDetailPage from "./pages/UserEventDetailPage";
import UserPastEvents from "./pages/UserPastEvents";
import RoomsPage from "./pages/RoomsPage";
import CreateRoomPage from "./pages/CreateRoomPage";
import RoomDetailPage from "./pages/RoomDetailPage";
import CoinsPage from "./pages/CoinsPage";
import CoinsSuccessPage from "./pages/CoinsSuccessPage";
import CoinsCancelPage from "./pages/CoinsCancelPage";
import { me, logout } from "./api";

export default function App() {
  // the logged-in user's email, or null when logged out
  const [email, setEmail] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null); // wraps the username button + dropdown
  const location = useLocation();
  const navigate = useNavigate();

  // re-check auth on every route change so the nav updates right after login
  useEffect(() => {
    me()
      .then((u) => setEmail(u.email))
      .catch(() => setEmail(null));
  }, [location.pathname]);

  // close the user dropdown when clicking anywhere outside it
  useEffect(() => {
    if (!menuOpen) return;
    function onClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [menuOpen]);

  async function handleLogout() {
    await logout();
    setEmail(null);
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
          <Link to="/rooms">Rooms</Link>
          <Link to="/top-career">Top Career</Link>
        </div>
        <div className="nav-right">
          {email ? (
            <div className="relative" ref={menuRef}>
              <button
                className="nav-email cursor-pointer"
                onClick={() => setMenuOpen((o) => !o)}
              >
                {email} ▾
              </button>
              {menuOpen && (
                <div className="absolute right-0 z-50 mt-2 w-40 rounded-md border border-zinc-700 bg-zinc-900 shadow-lg">
                  <Link
                    to="/friends"
                    className="block w-full px-4 py-2 text-left text-sm text-white hover:bg-zinc-800"
                    onClick={() => setMenuOpen(false)}
                  >
                    Friends
                  </Link>
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
        <Route path="/users/:userId" element={<ProfilePage />} />
        <Route path="/users/:userId/events" element={<UserPastEvents />} />
        <Route path="/users/:userId/events/:eventId" element={<UserEventDetailPage />} />
        <Route path="/friends" element={<FriendsPage />} />
        {/* /rooms/new is deliberately NOT in the nav — reached from the lobby button */}
        <Route path="/rooms" element={<RoomsPage />} />
        <Route path="/rooms/new" element={<CreateRoomPage />} />
        {/* /rooms/new must stay ABOVE this param route so "new" isn't read as an id */}
        <Route path="/rooms/:roomId" element={<RoomDetailPage />} />
        <Route path="/coins" element={<CoinsPage />} />
        {/* Stripe checkout redirects — must match success_url/cancel_url in coins.py */}
        <Route path="/success" element={<CoinsSuccessPage />} />
        <Route path="/cancel" element={<CoinsCancelPage />} />
        <Route path="/top-career" element={<TopCareerPage />} />
        <Route path="/predictor" element={<PredictorPage />} />
      </Routes>
    </>
  );
}
