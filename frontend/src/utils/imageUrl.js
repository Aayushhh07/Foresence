/** Resolve NDVI image URL (absolute API host for /static paths). */
export function resolveImageUrl(url) {
  if (!url) return null;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  const base = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
  return `${base}${url.startsWith('/') ? url : `/${url}`}`;
}
