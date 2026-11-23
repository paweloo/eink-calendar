import type { NextConfig } from "next";

// GitHub Pages serves a project site under /<repo>; the deploy workflow sets this from the Pages settings.
// Leave it empty for local dev or a custom domain.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export", // plain static files in out/ (GitHub Pages has no server)
  basePath,
  images: { unoptimized: true },
  reactCompiler: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
