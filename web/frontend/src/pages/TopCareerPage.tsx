import { useEffect, useState } from "react";
import { getTopCareers, type TopCareer } from "../api";
import { useNavigate } from "react-router-dom";

export default function TopCareerPage() {
    const [n, setN] = useState<number>(10); // at default, show the top 10
    const [topCareers, setTopCareers] = useState<TopCareer[]>([]);
    const [error, setError] = useState<string>("");
    const navigate = useNavigate()
    // run on mount and rerun if n changes
    useEffect(() => {
        getTopCareers(n)
        .then(setTopCareers)
        .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));     
    }, [n]);

    function rankColor(rank: number) {
        if (rank === 1) return "text-yellow-400";
        if (rank === 2) return "text-zinc-300";
        if (rank === 3) return "text-amber-600";
        return "text-zinc-500";
      }
      
      return (
        <div className="page">
          <h1 className="mb-1 text-2xl font-bold text-white">Top Careers</h1>
          <p className="mb-6 text-sm text-zinc-400">
            Ranked by career score across a fighter's UFC run
          </p>
      
          {/* the "n" control — changing this re-runs the effect */}
          <div className="mb-6 flex items-center gap-3">
            <label htmlFor="topN" className="text-sm text-zinc-400">
              Show
            </label>
            <select
              id="topN"
              value={n}
              onChange={(e) => setN(Number(e.target.value))}
              className="rounded-lg bg-zinc-800 px-3 py-2 text-white outline-none focus:ring-2 focus:ring-[#d33a2c]"
            >
              {[5, 10, 25, 50].map((opt) => (
                <option key={opt} value={opt}>
                  Top {opt}
                </option>
              ))}
            </select>
          </div>
      
          {error && <p className="error">{error}</p>}
      
          <ol className="space-y-2">
            {topCareers.map((career, i) => (
              <li
                key={career.fighter}
                className="flex items-center gap-4 rounded-lg bg-zinc-800 p-3 transition-transform hover:scale-105 hover:bg-zinc-700"
              >
                <span className={`w-8 text-center text-lg font-bold ${rankColor(i + 1)}`}>
                  {i + 1}
                </span>
      
                <span className="flex-1 font-semibold text-white">{career.fighter}</span>
      
                <div className="text-right">
                  <div className="font-bold text-[#d33a2c]">{career.career_score}</div>
                  <div className="text-xs text-zinc-400">{career.total_fights} fights</div>
                </div>
              </li>
            ))}
          </ol>
      
          {topCareers.length === 0 && !error && (
            <p className="text-zinc-500">No careers to show.</p>
          )}
        </div>
      );

    
    

    


}