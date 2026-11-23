// Images in /public/screens are rendered by the device's own code: run scripts/site-screens.sh to refresh them.

export const THEMES = [
  { id: "classic", label: "Classic", note: "Black ink, red for today" },
  { id: "mono", label: "Mono", note: "Black and white only" },
  { id: "bold", label: "Bold", note: "Heavier type, more red" },
  { id: "dark", label: "Dark", note: "White on black, red accents" },
] as const;

export const VIEWS = [
  { id: "month", label: "Month", note: "The whole month, with today’s schedule beside it" },
  { id: "week", label: "Week", note: "Seven columns, every event at a glance" },
  { id: "agenda", label: "Agenda", note: "The days ahead as a list" },
] as const;

export type ThemeId = (typeof THEMES)[number]["id"];
export type ViewId = (typeof VIEWS)[number]["id"];

export const viewSrc = (view: ViewId, theme: ThemeId) => `/screens/view-${view}-${theme}.png`;
export const screenSrc = (name: "welcome" | "link" | "ready" | "message", theme: ThemeId = "classic") =>
  `/screens/screen-${name}-${theme}.png`;
