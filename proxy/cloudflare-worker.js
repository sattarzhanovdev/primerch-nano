/**
 * Cloudflare Worker image proxy.
 *
 * Purpose:
 * - Fetches images from a strict allowlist of hosts (prevents open-proxy abuse)
 * - Adds caching headers
 * - Adds permissive CORS headers (safe for <img>, helpful for devtools)
 *
 * Deploy with Wrangler. Configure ALLOWED_HOSTS if you need more.
 */

export default {
  async fetch(request, env) {
    const reqUrl = new URL(request.url);
    const target = reqUrl.searchParams.get("url");

    if (!target) {
      return new Response("Missing query param: url", { status: 400 });
    }

    let upstreamUrl;
    try {
      upstreamUrl = new URL(target);
    } catch {
      return new Response("Invalid url", { status: 400 });
    }

    if (!["http:", "https:"].includes(upstreamUrl.protocol)) {
      return new Response("Unsupported protocol", { status: 400 });
    }

    const defaultHosts = [
      "files.gifts.ru",
      "tempfile.redpandaai.co",
      "tempfile.aiquickdraw.com",
      "mc.yandex.ru",
    ];
    const allowedHosts = String(env.ALLOWED_HOSTS || defaultHosts.join(","))
      .split(",")
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean);

    const host = upstreamUrl.hostname.toLowerCase();
    if (!allowedHosts.includes(host)) {
      return new Response(`Host not allowed: ${host}`, { status: 403 });
    }

    // Propagate range requests if any (some CDNs use it for progressive loading).
    const headers = new Headers();
    const range = request.headers.get("range");
    if (range) headers.set("range", range);
    headers.set("user-agent", "Mozilla/5.0 (image-proxy)");
    headers.set("accept", "image/*,*/*;q=0.8");

    const upstream = await fetch(upstreamUrl.toString(), {
      headers,
      cf: {
        cacheEverything: true,
        cacheTtl: 60 * 60, // 1 hour
      },
    });

    const outHeaders = new Headers(upstream.headers);
    outHeaders.set("access-control-allow-origin", "*");
    outHeaders.set("cache-control", "public, max-age=3600");
    outHeaders.delete("set-cookie");

    return new Response(upstream.body, {
      status: upstream.status,
      headers: outHeaders,
    });
  },
};

