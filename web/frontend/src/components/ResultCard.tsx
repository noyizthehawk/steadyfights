import { ProbBar } from "./ProbBar";
import type { PredictResult } from "../api";
export function ResultCard({ result }: { result: PredictResult }) {
    return (
      <div className="result">
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
  
        <div className="factors">
          {result.factors.map((f) => (
            <div key={f.label}>
              <strong>{f.label}</strong>: {f.favors} by {f.detail}
            </div>
          ))}
        </div>
      </div>
    );
  }
