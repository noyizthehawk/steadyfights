import { useEffect, useState } from "react";
import { getLeaderboard, type LeaderboardRow } from "../api";
import { useNavigate } from "react-router-dom";
import { rankColor } from "../lib/rankColor";

export default function LeaderboardPage() {
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const [error, setError] = useState<string>("");
  const navigate = useNavigate();

  //get page on mount
  useEffect(() => {
    getLeaderboard()
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load leaderboard"));
  }, []);

  return (
    <div className="page">
      <h1 className="mb-1 text-2xl font-bold text-white">Leaderboard</h1>
      <p className="mb-6 text-sm text-zinc-400">Ranked by win rate over finished fights</p>

      {error && <p className="error">{error}</p>}

      <ol className="space-y-2">
        {rows.map((row, i) => (
          <li
            key={row.name}
            onClick={() => navigate(`/users/${i}`)}
            className="flex cursor-pointer items-center gap-4 rounded-lg bg-zinc-800 p-3 transition-colors hover:bg-zinc-700 transition-transform hover:scale-105"
          >
            <span className={`w-8 text-center text-lg font-bold ${rankColor(i + 1)}`}>
              {i + 1}
            </span>

            <span className="flex-1 font-semibold text-white">{row.name}</span>

            <div className="text-right">
              <div className="font-bold text-[#d33a2c]">
                {row.winrate === null ? "—" : `${row.winrate}%`}
              </div>
              <div className="text-xs text-zinc-400">
                {row.correct} of {row.settled} correct
              </div>
            </div>
          </li>
        ))}
      </ol>

      {rows.length === 0 && !error && (
        <p className="text-zinc-500">No rankings yet.</p>
      )}
    </div>
  );
}
