/** Path to a file in public/, prefixed with the GitHub Pages base path (basePath doesn't rewrite plain <img> src). */
export const asset = (path: string) => `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}${path}`;
