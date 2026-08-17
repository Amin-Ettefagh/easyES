/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Django REST endpoints use canonical trailing slashes. Preserve them so
  // same-origin rewrites do not bounce between Next (no slash) and Django.
  skipTrailingSlashRedirect: true,
  // Standalone output makes the Docker image small: only the traced files ship.
  output: "standalone",
  // Keep browser API calls same-origin. This works on localhost, LAN IPs and
  // custom domains without baking a host-specific backend URL into JavaScript.
  async rewrites() {
    const apiBase =
      process.env.INTERNAL_API_BASE || "http://localhost:8000/api/v1";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiBase}/:path*/`,
      },
    ];
  },
};

module.exports = nextConfig;
