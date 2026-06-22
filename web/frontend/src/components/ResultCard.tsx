import { ProbBar } from "./ProbBar";
import type { PredictResult } from "../api";
export function ResultCard({ result }: { result: PredictResult }) {
    return (
      <div className="result border border-zinc-700 rounded-lg p-4 mx-auto max-w-xl mt-6 h-fit">
        <div className="matchup">
          {result.fighter_a} <small>({result.style_a})</small> vs{" "}
          {result.fighter_b} <small>({result.style_b})</small>
        </div>
  
        <ProbBar name={result.fighter_a} pct={result.prob_a} />
        <ProbBar name={result.fighter_b} pct={result.prob_b} />
  
        <div className="pick">
          Model pick: <strong>{result.pick}</strong> ({result.confidence}%
          confidence)
        </div>
  
        <div className="tale-of-the-tape">
          <h3 className="font-bold">Tale of the Tape</h3>
          {result.factors.map((f) => (
            <div className="tape-row" key={f.label}>
              {/* Bold whichever fighter's value wins this stat. */}
              <span className={f.favors === result.fighter_a ? "tape-val winner" : "tape-val"}>
                {f.value_a}
              </span>
              <span className="tape-label">{f.label}</span>
              <span className={f.favors === result.fighter_b ? "tape-val winner" : "tape-val"}>
                {f.value_b}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
