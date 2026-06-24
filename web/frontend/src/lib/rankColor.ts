// Tailwind text color for a 1-based leaderboard rank: medals for the top 3,
// muted zinc for everyone else. Shared by the leaderboard + top-careers lists.
export function rankColor(rank: number): string {
  if (rank === 1) return "text-yellow-400";
  if (rank === 2) return "text-zinc-300";
  if (rank === 3) return "text-amber-600";
  return "text-zinc-500";
}
