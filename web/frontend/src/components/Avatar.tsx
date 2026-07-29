// Round avatar. Shows the uploaded image when there is one, otherwise a colored
// circle with the user's first initial (so every user always has an avatar).

// Deterministic color from the name, so a given user's fallback is always the
// same shade rather than flickering between renders.
const COLORS = [
  "#dc2626", "#ea580c", "#d97706", "#65a30d", "#059669",
  "#0891b2", "#2563eb", "#7c3aed", "#c026d3", "#db2777",
];

function colorFor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return COLORS[Math.abs(hash) % COLORS.length];
}

type AvatarProps = {
  url?: string | null;
  name: string;
  size?: number; // pixels
};

export function Avatar({ url, name, size = 32 }: AvatarProps) {
  const initial = (name?.trim()?.[0] ?? "?").toUpperCase();

  if (url) {
    return (
      <img
        src={url}
        alt={name}
        width={size}
        height={size}
        className="shrink-0 rounded-full object-cover"
        style={{ width: size, height: size }}
      />
    );
  }

  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-full font-semibold text-white"
      style={{
        width: size,
        height: size,
        background: colorFor(name || "?"),
        fontSize: size * 0.45,
      }}
      aria-label={name}
    >
      {initial}
    </div>
  );
}
