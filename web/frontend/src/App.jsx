import { useEffect, useState } from "react";
import { getFighters, predict } from "./api";
import "./App.css";

export default function App() {
  // --- STATE ---
  // useState gives you a value + a setter. When you call the setter, React
  // re-renders the component with the new value. That's the whole model.
  const [fighters, setFighters] = useState([]); // all names for the dropdowns
  const [fighterA, setFighterA] = useState(""); // currently selected A
  const [fighterB, setFighterB] = useState(""); // currently selected B
  const [result, setResult] = useState(null); // prediction response, or null
  const [loading, setLoading] = useState(false); // is a request in flight?
  const [error, setError] = useState(""); // any error message to show

  // --- EFFECT ---
  // useEffect with an empty [] dependency array runs ONCE after first render.
  // Perfect for loading the fighter list when the page opens.
  useEffect(() => {
    getFighters()
      .then(setFighters)
      .catch((e) => setError(e.message));
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
    } catch (e) {
      setError(e.message);
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

// A type-to-search fighter picker. It's a normal text <input> wired to a
// <datalist>: as you type, the browser filters `options` and shows matches.
// The <input> and its <datalist> are linked by a shared id via `list`.
function FighterSelect({ label, value, onChange, options }) {
  // Each input needs its OWN datalist id, or both pickers would share one.
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

// The result display. Renders two probability bars and the model's pick.
function ResultCard({ result }) {
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

function ProbBar({ name, pct }) {
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
