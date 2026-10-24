// Light/dark mode as a per-device preference ("system" follows the OS). Kept in localStorage on
// purpose: it's a display convenience for this browser, not account data. The <html class="dark">
// toggle is applied before first paint by THEME_INIT_SCRIPT (inlined in app/layout.tsx), so a
// dark-mode user never sees a white flash; Tailwind's `dark:` variant keys off that class (see
// the @custom-variant in globals.css).

export type ThemePreference = "system" | "light" | "dark";

export const THEME_STORAGE_KEY = "ownai.theme";

export const THEME_INIT_SCRIPT = `(function(){try{var p=localStorage.getItem("${THEME_STORAGE_KEY}");var d=p==="dark"||(p!=="light"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.classList.toggle("dark",d);}catch(e){}})();`;

export function getThemePreference(): ThemePreference {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system";
  }
}

function systemPrefersDark(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function applyTheme(preference: ThemePreference): void {
  const dark = preference === "dark" || (preference === "system" && systemPrefersDark());
  document.documentElement.classList.toggle("dark", dark);
}

export function setThemePreference(preference: ThemePreference): void {
  try {
    if (preference === "system") localStorage.removeItem(THEME_STORAGE_KEY);
    else localStorage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    // Storage blocked (private mode etc.) - still apply for this page view.
  }
  applyTheme(preference);
}

/** Keeps "system" in sync when the OS switches (e.g. automatic dark mode at sunset). */
export function watchSystemTheme(): () => void {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const onChange = () => {
    if (getThemePreference() === "system") applyTheme("system");
  };
  media.addEventListener("change", onChange);
  return () => media.removeEventListener("change", onChange);
}
