// Fallback for the manifest share_target when the service worker (public/sw.js) isn't
// controlling the page yet, e.g. the very first share right after installing: passes the text
// parts on to /share via the query string. Images can't travel that way and are dropped - the
// service worker path, which handles them, is active from the next app start on.
export async function POST(request: Request): Promise<Response> {
  const form = await request.formData();
  const params = new URLSearchParams();
  for (const key of ["title", "text", "url"]) {
    const value = form.get(key);
    if (typeof value === "string" && value) params.set(key, value.slice(0, 4000));
  }
  // Relative Location on purpose: behind a reverse proxy, request.url carries the internal host.
  return new Response(null, { status: 303, headers: { Location: `/share?${params.toString()}` } });
}
