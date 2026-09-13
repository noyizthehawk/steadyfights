// A fighter's country flag, using ufc.com's own image.
//
// Not an emoji derived from an ISO code: flag emoji have no glyphs in the
// Windows emoji font, so Chrome and Edge there render bare letters. An <img>
// looks the same on every platform, and img_a/img_b already hotlink this same
// CDN for fighter headshots — one approach for both beats two.

export function Flag({
    src,
    country,
    className = "",
}: {
    src: string | null;
    country: string | null;
    className?: string;
}) {
    // Nothing on rows the scraper hasn't revisited yet. A missing flag should
    // read as absent, not as a broken image or a grey placeholder box.
    if (!src) return null;
    const label = country ?? "";
    return (
        <img
            src={src}
            alt={label}
            title={label}
            // fixed box so a row's height doesn't shift as flags load, and
            // object-contain keeps odd aspect ratios from stretching. 3:2 is
            // the ratio most national flags use, so most fill the box exactly.
            className={`h-4 w-6 shrink-0 rounded-[2px] object-contain ${className}`}
            loading="lazy"
            // their CDN, so a 404 or a moved path should vanish quietly rather
            // than leave a broken-image icon in the middle of the card
            onError={(e) => {
                e.currentTarget.style.display = "none";
            }}
        />
    );
}
