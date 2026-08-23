import { Routes, Route, Link, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import "./App.css";
import PredictorPage from "./pages/PredictorPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import FighterProfilePage from "./pages/FighterProfilePage";
import FightersPage from "./pages/FightersPage";
import AccountPage from "./pages/AccountPage";
import { FighterSearch } from "./components/FighterSearch";
import { Avatar } from "./components/Avatar";
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
import Footer from "./components/Footer";

// The main page links, defined once and rendered in TWO places: the horizontal
// desktop row and the mobile hamburger dropdown. Editing this array updates both.
const navLinks = [
  { to: "/", label: "Home" },
  { to: "/predictor", label: "Bout Brain" },
  { to: "/fighters", label: "Fighter Cards" },
  { to: "/prediction-game", label: "Casual Checker" },
  { to: "/leaderboard", label: "Leaderboard" },
  { to: "/rooms", label: "Rooms" },
  { to: "/top-career", label: "Top Career" },
];

export default function App() {
  // the logged-in user's username, or null when logged out
  const [username, setUsername] = useState<string | null>(null);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null); // wraps the username button + dropdown
  const [navOpen, setNavOpen] = useState(false);
  const navRef = useRef<HTMLDivElement>(null); // wraps the hamburger button + mobile menu
  const location = useLocation();
  const navigate = useNavigate();

  // re-check auth on every route change so the nav updates right after login
  useEffect(() => {
    me()
      .then((u) => {
        setUsername(u.username);
        setAvatarUrl(u.avatar_url);
      })
      .catch(() => {
        setUsername(null);
        setAvatarUrl(null);
      });
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

  // same click-outside behavior for the mobile nav dropdown
  useEffect(() => {
    if (!navOpen) return;
    function onClickOutside(e: MouseEvent) {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setNavOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [navOpen]);

  async function handleLogout() {
    await logout();
    setUsername(null);
    setAvatarUrl(null);
    setMenuOpen(false);
    navigate("/");
  }

  return (
    <>
      <nav className="nav">
        {/* Mobile only (CSS hides it above 768px): hamburger + dropdown */}
        <div className="nav-mobile" ref={navRef}>
          <button
            className="nav-hamburger"
            onClick={() => setNavOpen((o) => !o)}
            aria-label="Toggle navigation menu"
          >
            ☰
          </button>
          {navOpen && (
            <div className="absolute left-0 z-50 mt-2 w-48 rounded-md border border-zinc-700 bg-zinc-900 shadow-lg">
              {navLinks.map((l) => (
                <Link
                  key={l.to}
                  to={l.to}
                  className="block w-full px-4 py-2 text-left text-sm text-white hover:bg-zinc-800"
                  onClick={() => setNavOpen(false)}
                >
                  {l.label}
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Desktop only (CSS hides it below 768px): the horizontal link row */}
        <div className="nav-left">
          {navLinks.map((l) => (
            <Link key={l.to} to={l.to}>
              {l.label}
            </Link>
          ))}
        </div>

        {/* Global fighter search — available from every page */}
        <FighterSearch />

        <div className="nav-right">
          {username ? (
            <div className="relative" ref={menuRef}>
              <button
                className="nav-email flex cursor-pointer items-center gap-2"
                onClick={() => setMenuOpen((o) => !o)}
              >
                <Avatar url={avatarUrl} name={username ?? "?"} size={28} />
                {username} ▾
              </button>
              {menuOpen && (
                <div className="absolute right-0 z-50 mt-2 w-40 rounded-md border border-zinc-700 bg-zinc-900 shadow-lg">
                  <Link
                    to="/account"
                    className="block w-full px-4 py-2 text-left text-sm text-white hover:bg-zinc-800"
                    onClick={() => setMenuOpen(false)}
                  >
                    Account
                  </Link>
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
        <Route path="/account" element={<AccountPage />} />
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

      <Footer />
    </>
  );
}
