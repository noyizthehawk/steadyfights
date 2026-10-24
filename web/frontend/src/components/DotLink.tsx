import { Link } from "react-router-dom";

/** A link in the app's dot language, with its label underneath: a quiet dot
 *  at rest that fills red with the soft ring on hover / keyboard focus. Used
 *  wherever a plain text link would be (My events, Every pick, back to Bout
 *  Brain). The padding is the hit area. */
export function DotLink({ to, label }: { to: string; label: string }) {
  return (
    <Link to={to} className="group/dot -m-2 inline-flex flex-col items-center gap-1.5 p-2 outline-none">
      <span
        aria-hidden
        className="block h-2.5 w-2.5 rounded-full bg-white/25 transition-all duration-200 group-hover/dot:scale-110 group-hover/dot:bg-[#d33a2c] group-hover/dot:shadow-[0_0_0_4px_#d33a2c33] group-focus-visible/dot:bg-[#d33a2c] group-focus-visible/dot:shadow-[0_0_0_4px_#d33a2c33]"
      />
      <span
        className="text-[11px] italic leading-none text-zinc-500 transition-colors group-hover/dot:text-zinc-200 group-focus-visible/dot:text-zinc-200"
        style={{ fontFamily: "var(--font-rundown)" }}
      >
        {label}
      </span>
    </Link>
  );
}
