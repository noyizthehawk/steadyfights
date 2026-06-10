import { useEffect, useState } from "react";
import { getFighters, predict } from "./api";
import type { PredictResult } from "./api";
import "./App.css";

export default function App() {
  // --- STATE ---
  // The <...> is the TYPE of what this state holds. useState infers most things,
  // but for empty/null initial values we tell it explicitly.
  const [fighters, setFighters] = useState<string[]>([]); // names for the dropdowns
  const [fighterA, setFighterA] = useState<string>(""); // selected A
  const [fighterB, setFighterB] = useState<string>(""); // selected B
  const [result, setResult] = useState<PredictResult | null>(null); // prediction, or none yet
  const [loading, setLoading] = useState<boolean>(false); // request in flight?
  const [error, setError] = useState<string>(""); // error message to show

  // --- EFFECT --- runs once on mount: load the fighter list.
  useEffect(() => {
    getFighters()
      .then(setFighters)
      .catch((e: unknown) => setError(errorMessage(e)));
  }, []);

  // --- EVENT HANDLER ---
  async function handlePredict() {
    setError("");
    setResult(null);
    if (!fighterA || !fighterB) {
      setError("Pick both fighters.");
      return;
    }
    setLoading(true);
    try {
      const data = await predict(fighterA, fighterB);
      setResult(data);
    } catch (e: unknown) {
      // A caught value is `unknown` in TS — narrow it before using .message.
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <h1>STEADYFIGHTS</h1>
      <p className="subtitle">Best Model on the market</p>

      <div className="pickers">
        <FighterSelect
          label="Fighter A"
          value={fighterA}
          onChange={setFighterA}
          options={fighters}
        />
        <span className="vs">vs</span>
        <FighterSelect
          label="Fighter B"
          value={fighterB}
          onChange={setFighterB}
          options={fighters}
        />
      </div>

      <button className="predict-btn" onClick={handlePredict} disabled={loading}>
        {loading ? "Predicting…" : "Predict"}
      </button>

      {/* Conditional rendering: only show these if they exist. */}
      {error && <p className="error">{error}</p>}
      {result && <ResultCard result={result} />}
    </div>
  );
}

// Pull a readable message out of an unknown caught error.
function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "Something went wrong";
}

// Props are described by a type. Now passing the wrong prop is a compile error.
type FighterSelectProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
};

// A type-to-search fighter picker: a text <input> wired to a <datalist>, linked
// by a shared id via `list`.
function FighterSelect({ label, value, onChange, options }: FighterSelectProps) {
  const listId = `fighters-${label.replace(/\s+/g, "-")}`;
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="text"
        list={listId}
        value={value}
        placeholder="Type a name…"
        onChange={(e) => onChange(e.target.value)}
      />
      <datalist id={listId}>
        {options.map((name) => (
          <option key={name} value={name} />
        ))}
      </datalist>
    </label>
  );
}

function ResultCard({ result }: { result: PredictResult }) {
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
    </div>
  );
}

function ProbBar({ name, pct }: { name: string; pct: number }) {
  return (
    <div className="prob-row">
      <span className="prob-name">{name}</span>
      <div className="prob-track">
        <div className="prob-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="prob-pct">{pct}%</span>
    </div>
  );
}
