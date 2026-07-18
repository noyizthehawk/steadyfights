import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <span className="footer-logo">SteadyFights</span>
          <p className="footer-tagline">
            UFC predictions, pick&apos;em battles, and bragging rights.
          </p>
        </div>

        <nav className="footer-links">
          <Link to="/predictor">Predictor</Link>
          <Link to="/prediction-game">Casual Checker</Link>
          <Link to="/rooms">Rooms</Link>
          <Link to="/leaderboard">Leaderboard</Link>
        </nav>
      </div>

      <div className="footer-legal">
        <p>
          Coins are for entertainment only and cannot be redeemed for cash or
          prizes. Not affiliated with UFC®.
        </p>
        <p>© {new Date().getFullYear()} SteadyFights</p>
      </div>
    </footer>
  );
}
