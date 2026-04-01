/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    // Default API origin; override via .env.local with NEXT_PUBLIC_API_URL
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/:path*`,
      },
    ]
  },
  // Suppress hydration warnings for browser extension attributes
  reactStrictMode: true,
}

module.exports = nextConfig
