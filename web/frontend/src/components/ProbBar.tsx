export function ProbBar({ name, pct }: { name: string; pct: number }) {
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