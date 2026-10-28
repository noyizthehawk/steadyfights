import { useState, type ImgHTMLAttributes } from "react";

// Shown when the scrape found no poster, or the scraped URL no longer loads
// (ufc.com rotates its CDN paths, so a stored link can go dead).
export const DEFAULT_POSTER = "/default-poster.png";

export function EventPoster({
    src,
    alt,
    className,
    ...rest
}: { src: string | null } & Omit<ImgHTMLAttributes<HTMLImageElement>, "src">) {
    // Remember the failure so a broken URL swaps once instead of looping.
    const [failed, setFailed] = useState(false);
    return (
        <img
            {...rest}
            src={src && !failed ? src : DEFAULT_POSTER}
            alt={alt}
            className={className}
            onError={() => setFailed(true)}
        />
    );
}
