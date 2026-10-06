# PP Neue Montreal

Commercial typeface from Pangram Pangram, not redistributable, so the files are
not in the repo. Drop them here and they are picked up automatically:

    PPNeueMontreal-Book.woff2          (400, upright)
    PPNeueMontreal-Italic.woff2        (400, italic)   <- the rundown uses this
    PPNeueMontreal-Medium.woff2        (500, upright)
    PPNeueMontreal-MediumItalic.woff2  (500, italic)

Only the italic is strictly needed for the rundown; the upright faces are
declared so the family is usable elsewhere later.

Served from /public, so they are referenced as /fonts/<name>.woff2 at runtime
rather than hashed through the bundler. Until the files exist the @font-face
rules simply fail and the rundown falls back to the system sans stack in
src/index.css — italic still renders, just not in Montreal.
