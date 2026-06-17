
type FighterSelectProps = {
    label: string;
    value: string;
    onChange: (value: string) => void;
    options: string[];
  };
    
export function FighterSelect({ label, value, onChange, options }: FighterSelectProps) {
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