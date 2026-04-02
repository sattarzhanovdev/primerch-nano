# External Image Proxy (Cloudflare Worker)

Use this when your hosting blocks outbound requests (e.g., PythonAnywhere free) and images from `base.json` don't load.

## Deploy (Wrangler)

1) Install Wrangler locally:

```bash
npm i -g wrangler
wrangler login
```

2) Create a new Worker (or use an existing one) and paste `proxy/cloudflare-worker.js`.

3) Deploy:

```bash
wrangler deploy proxy/cloudflare-worker.js --name primerch-image-proxy
```

You will get a URL like:

`https://primerch-image-proxy.<your-subdomain>.workers.dev`

## Configure the app

On your server set:

`EXTERNAL_IMAGE_PROXY_BASE=https://primerch-image-proxy.<your-subdomain>.workers.dev`

Restart/reload your web app.

The frontend will automatically load catalog images via:

`{EXTERNAL_IMAGE_PROXY_BASE}?url=<encoded_original_url>`

## Security

The Worker uses a strict allowlist of hosts (see `ALLOWED_HOSTS` in the code).  
Do not remove it, otherwise you'll create an open proxy.

