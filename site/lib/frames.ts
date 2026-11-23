// 3D-printed frame colours. `color` drives every .frame on the page through the --frame CSS variable.
export const FRAMES = [
  { id: "terracotta", label: "Terracotta", color: "#a85a3c", note: "Warm clay, like an old flower pot" },
  { id: "charcoal", label: "Charcoal", color: "#2d2c2a", note: "Near-black, disappears on dark walls" },
  { id: "chalk", label: "Chalk", color: "#e9e3d6", note: "Off-white, quiet on light walls" },
  { id: "sage", label: "Sage", color: "#86957a", note: "Soft grey-green" },
  { id: "ink", label: "Ink Blue", color: "#2e3f5c", note: "Deep fountain-pen blue" },
] as const;

export type FrameId = (typeof FRAMES)[number]["id"];
export const DEFAULT_FRAME: FrameId = "terracotta";
const KEY = "inkcal-frame";

// A tiny external store so every component (and a reload) agrees on the chosen colour.
const listeners = new Set<() => void>();
let current: FrameId | null = null;

const isFrame = (v: string | null): v is FrameId => FRAMES.some((f) => f.id === v);

/** ?frame=sage in the URL wins (for sharing a colour), then the visitor's last pick. */
function read(): FrameId {
  const fromUrl = new URLSearchParams(window.location.search).get("frame");
  if (isFrame(fromUrl)) return fromUrl;
  try {
    const v = localStorage.getItem(KEY);
    if (isFrame(v)) return v;
  } catch {}
  return DEFAULT_FRAME;
}

export const frameStore = {
  subscribe(cb: () => void) {
    listeners.add(cb);
    return () => void listeners.delete(cb);
  },
  get: (): FrameId => (current ??= read()),
  server: (): FrameId => DEFAULT_FRAME,
  set(id: FrameId) {
    current = id;
    try {
      localStorage.setItem(KEY, id);
    } catch {}
    listeners.forEach((cb) => cb());
  },
};

/** Paint every .frame on the page in this colour. */
export function applyFrame(id: FrameId) {
  const f = FRAMES.find((x) => x.id === id) ?? FRAMES[0];
  document.documentElement.style.setProperty("--frame", f.color);
}
