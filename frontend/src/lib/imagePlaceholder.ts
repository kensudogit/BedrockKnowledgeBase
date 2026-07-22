/** Visible mock image used when API returns a tiny/empty PNG. */
export function buildPlaceholderDataUrl(prompt: string): string {
  const safe = prompt
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
  const line1 = safe.slice(0, 42);
  const line2 = safe.slice(42, 84);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#0f2744"/><stop offset="100%" stop-color="#0284c7"/>
  </linearGradient></defs>
  <rect width="512" height="512" fill="url(#g)"/>
  <text x="256" y="170" text-anchor="middle" fill="#e0f2fe" font-size="34" font-family="Segoe UI, sans-serif" font-weight="700">MOCK IMAGE</text>
  <text x="256" y="290" text-anchor="middle" fill="#ffffff" font-size="18" font-family="Segoe UI, sans-serif">${line1}</text>
  <text x="256" y="322" text-anchor="middle" fill="#ffffff" font-size="18" font-family="Segoe UI, sans-serif">${line2}</text>
</svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

export function isTinyOrEmptyDataUrl(dataUrl: string | undefined): boolean {
  if (!dataUrl) return true;
  if (dataUrl.includes("iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB")) return true;
  return false;
}
