// A type-to-search fighter picker: a text <input> wired to a <datalist>, linked
// by a shared id via `list`.

// Props are described by a type. Now passing the wrong prop is a compile error.
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