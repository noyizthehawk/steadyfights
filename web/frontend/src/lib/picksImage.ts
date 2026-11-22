/** Draws a user's picks for one event as a 1080x1350 PNG (Instagram portrait).
 *
 *  Canvas, in the browser: free to run, nothing to host. No headshots: they
 *  come from ufc.com, and a canvas holding another site's image refuses to
 *  export. The poster is fine because the backend re-serves it from our own
 *  domain (/api/events/{id}/poster), and the logo is ours.
 */

export type PickRow = {
  picked: string;
  over: string;
  side: "a" | "b";
  score: number | null;       // our career score for the fighter they picked
  form: number | null;        // ...and their recent form (last 3 fights)
  underdog: boolean;          // they picked the fighter with the worse betting odds
};

export type UserLine = {
  rank: number | null;   // null = unranked
  correct: number;
  settled: number;
};

const W = 1080;
const H = 1350;
const PAD = 72;
const RED = "#d33a2c";
const BLUE = "#60a5fa";
const GOLD = "#ffd75e";
const PIXEL = '"Press Start 2P", monospace';
const SANS = '"Helvetica Neue", Helvetica, Arial, sans-serif';
const MONO = 'ui-monospace, "SF Mono", Menlo, Consolas, monospace';

function loadImage(src: string, cors = false): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const img = new Image();
    if (cors) img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

/** Set the largest font size (down to `min`) at which `text` fits in `maxWidth`. */
function fit(ctx: CanvasRenderingContext2D, text: string, font: (px: number) => string, start: number, min: number, maxWidth: number) {
  let px = start;
  ctx.font = font(px);
  while (px > min && ctx.measureText(text).width > maxWidth) {
    px -= 1;
    ctx.font = font(px);
  }
  return px;
}

/** Break a title into at most two lines that each fit. */
function twoLines(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  if (ctx.measureText(text).width <= maxWidth) return [text];
  const words = text.split(" ");
  for (let i = words.length - 1; i > 0; i--) {
    const a = words.slice(0, i).join(" ");
    if (ctx.measureText(a).width <= maxWidth) return [a, words.slice(i).join(" ")];
  }
  return [text];
}

const POSTER_W = 300;
const POSTER_H = 200;

/** The poster as an iOS-style tile: straight, rounded corners, a hairline
 *  border and a soft shadow. Cover-cropped to fill the tile. */
function drawPoster(ctx: CanvasRenderingContext2D, img: HTMLImageElement, x: number, y: number) {
  const w = POSTER_W;
  const h = POSTER_H;
  const r = 28;
  const shape = () => {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
  };

  ctx.save();
  ctx.shadowColor = "rgba(0,0,0,0.55)";
  ctx.shadowBlur = 30;
  ctx.shadowOffsetY = 10;
  ctx.fillStyle = "#18181b";
  shape();
  ctx.fill();
  ctx.restore();

  ctx.save();
  shape();
  ctx.clip();
  const scale = Math.max(w / img.width, h / img.height);
  const sw = w / scale;
  const sh = h / scale;
  ctx.drawImage(img, (img.width - sw) / 2, (img.height - sh) / 2, sw, sh, x, y, w, h);
  ctx.restore();

  ctx.save();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "rgba(255,255,255,0.14)";
  shape();
  ctx.stroke();
  ctx.restore();
}

/** Our rating, in a gold ring (the Team of the Week look). */
function ring(ctx: CanvasRenderingContext2D, cx: number, cy: number, radius: number, value: number | null, color = GOLD) {
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.lineWidth = 3;
  ctx.strokeStyle = value === null ? "#3f3f46" : color;
  ctx.stroke();
  const text = value === null ? "–" : String(Math.round(value));
  ctx.font = `bold ${Math.round(radius * 0.9)}px ${MONO}`;
  ctx.fillStyle = value === null ? "#71717a" : "#fff";
  const w = ctx.measureText(text).width;
  ctx.fillText(text, cx - w / 2, cy + radius * 0.32);
}

export async function renderPicksImage(opts: {
  eventTitle: string;
  date: Date;
  username: string;
  picks: PickRow[];
  user: UserLine | null;
  posterUrl: string | null;
}): Promise<Blob> {
  // The pixel face comes from Google Fonts; make sure it's loaded before
  // drawing, or the canvas silently falls back to monospace.
  try {
    await document.fonts.load(`40px ${PIXEL}`);
  } catch {
    /* fall back quietly */
  }
  const [logo, poster] = await Promise.all([
    loadImage("/email/header.png"),
    opts.posterUrl ? loadImage(opts.posterUrl, true) : Promise.resolve(null),
  ]);

  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d")!;
  ctx.textBaseline = "alphabetic";

  ctx.fillStyle = "#0a0a0a";
  ctx.fillRect(0, 0, W, H);

  // header: logo, red rule
  let y = PAD;
  if (logo) {
    const h = 64;
    ctx.drawImage(logo, PAD, y, (logo.width / logo.height) * h, h);
  } else {
    ctx.font = `28px ${PIXEL}`;
    ctx.fillStyle = "#fff";
    ctx.fillText("STEADYFIGHTS", PAD, y + 44);
  }
  y += 64 + 32;
  ctx.fillStyle = RED;
  // the rule stops short of the poster rather than running under it
  ctx.fillRect(PAD, y, W - PAD * 2 - (poster ? POSTER_W + 32 : 0), 4);

  // the stamp sits over the top right corner, crossing the rule
  const stampRight = poster !== null;
  if (poster) drawPoster(ctx, poster, W - PAD - POSTER_W, PAD);

  y += 62;
  ctx.font = `22px ${PIXEL}`;
  ctx.fillStyle = RED;
  ctx.fillText("MY PICKS", PAD, y);

  // title: keep clear of the stamp on the first line
  y += 30;
  ctx.font = `bold 58px ${SANS}`;
  const titleW = W - PAD * 2 - (stampRight ? 330 : 0);
  const lines = twoLines(ctx, opts.eventTitle, titleW);
  for (const line of lines) {
    y += 64;
    fit(ctx, line, (px) => `bold ${px}px ${SANS}`, 58, 34, titleW);
    ctx.fillStyle = "#fff";
    ctx.fillText(line, PAD, y);
  }
  y += 42;
  ctx.font = `24px ${MONO}`;
  ctx.fillStyle = "#a1a1aa";
  ctx.fillText(
    opts.date.toLocaleDateString(undefined, { weekday: "short", month: "long", day: "numeric", year: "numeric" }),
    PAD,
    y,
  );
  y = Math.max(y, stampRight ? PAD + POSTER_H + 20 : 0) + 40;

  // stats strip: the user's game record
  const u = opts.user;
  const pct = u && u.settled > 0 ? Math.round((100 * u.correct) / u.settled) : null;
  const stats: [string, string][] = [
    ["RANK", u?.rank ? `#${u.rank}` : "UNRANKED"],
    ["RECORD", u && u.settled > 0 ? `${u.correct}-${u.settled - u.correct}` : "DEBUT"],
    ["HIT RATE", pct !== null ? `${pct}%` : "—"],
    ["PICKS", String(opts.picks.length)],
  ];
  const boxW = (W - PAD * 2 - 16 * 3) / 4;
  stats.forEach(([label, value], i) => {
    const x = PAD + i * (boxW + 16);
    ctx.strokeStyle = "#27272a";
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, boxW, 96);
    ctx.font = `18px ${MONO}`;
    ctx.fillStyle = "#71717a";
    ctx.fillText(label, x + 18, y + 34);
    fit(ctx, value, (px) => `${px}px ${PIXEL}`, 26, 14, boxW - 36);
    ctx.fillStyle = i === 0 ? GOLD : "#fff";
    ctx.fillText(value, x + 18, y + 76);
  });
  y += 96 + 36;

  const labelY = y;   // column labels go here once the ring size is known
  y += 12;

  // the picks: rows share whatever height is left above the footer
  const footerTop = H - PAD - 40;
  const rows = opts.picks;
  const rowH = Math.min(104, Math.floor((footerTop - 24 - y) / Math.max(rows.length, 1)));
  const nameMax = rowH >= 90 ? 40 : rowH >= 70 ? 32 : 26;
  const overMax = Math.round(nameMax * 0.6);
  const radius = Math.min(34, Math.floor(rowH * 0.36));
  const textX = PAD + 32;
  const gap = 16;
  const careerX = W - PAD - radius - 2;
  const formX = careerX - radius * 2 - gap;
  const textW = W - PAD * 2 - 32 - radius * 4 - gap - 28;

  // column labels, centred over their rings
  ctx.font = `16px ${MONO}`;
  ctx.fillStyle = "#71717a";
  for (const [label, x] of [["FORM", formX], ["CAREER", careerX]] as const) {
    ctx.fillText(label, x - ctx.measureText(label).width / 2, labelY);
  }

  rows.forEach((r, i) => {
    const top = y + i * rowH;
    if (i > 0) {
      ctx.fillStyle = "#1f1f22";
      ctx.fillRect(PAD, top, W - PAD * 2, 2);
    }
    const mid = top + rowH / 2;
    ctx.fillStyle = r.side === "a" ? RED : BLUE;
    ctx.fillRect(PAD, mid - nameMax * 0.72, 10, nameMax * 1.45);

    const name = r.picked.toUpperCase();
    fit(ctx, name, (px) => `bold ${px}px ${SANS}`, nameMax, 18, textW);
    ctx.fillStyle = "#fff";
    ctx.fillText(name, textX, mid);

    const underdog = r.underdog;
    const over = `over ${r.over}`;
    fit(ctx, over, (px) => `${px}px ${MONO}`, overMax, 13, textW - (underdog ? 170 : 0));
    ctx.fillStyle = "#71717a";
    ctx.fillText(over, textX, mid + overMax + 8);
    if (underdog) {
      const ow = ctx.measureText(over).width;
      ctx.font = `${Math.max(11, Math.round(overMax * 0.62))}px ${PIXEL}`;
      ctx.fillStyle = GOLD;
      ctx.fillText("UNDERDOG", textX + ow + 18, mid + overMax + 7);
    }

    ring(ctx, formX, mid, radius, r.form, "#d4d4d8");
    ring(ctx, careerX, mid, radius, r.score);
  });

  // footer
  ctx.fillStyle = "#1f1f22";
  ctx.fillRect(PAD, footerTop, W - PAD * 2, 2);
  const fy = H - PAD + 4;
  ctx.font = `bold 28px ${MONO}`;
  ctx.fillStyle = "#fff";
  ctx.fillText(`@${opts.username}`, PAD, fy);
  ctx.font = `24px ${MONO}`;
  ctx.fillStyle = "#a1a1aa";
  const site = "steadyfights.com";
  ctx.fillText(site, W - PAD - ctx.measureText(site).width, fy);

  return new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Could not draw the image"))), "image/png"),
  );
}
