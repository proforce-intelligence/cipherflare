/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true, 
  },
  images: {
    unoptimized: true,
  },

  
  async rewrites() {
    return [
      {
        // All requests starting with /api/...
        source: "/api/:path*",
        // Forward them to your FastAPI backend
        destination: "http://localhost:8000/api/:path*",
      },
    ]
  },
 
}

export default nextConfig