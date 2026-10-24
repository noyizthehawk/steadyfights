import { Link } from "react-router-dom";

/** The logo: a red rounded square with "SF." in black. It IS the home link — it
 *  replaced "Home" in the nav. Pops in on first load (.nav-logo-mark in
 *  App.css); the nav never unmounts, so that plays once per visit. */
export function LogoMark() {
  return (
    <Link
      to="/"
      aria-label="steadyfights — home"
      className="nav-logo-mark group flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#d33a2c] transition-transform duration-200 hover:scale-110"
    >
      <span className="text-[9px] leading-none text-black" style={{ fontFamily: "var(--font-display)" }}>
        SF.
      </span>
    </Link>
  );
}
