export type ThemePreference = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'lora-theme'
export function readThemePreference(): ThemePreference {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY)
    if (saved === 'light' || saved === 'dark' || saved === 'system') return saved
  } catch { /* The UI still works when storage is unavailable. */ }
  return 'system'
}

export function applyTheme(preference: ThemePreference) {
  const theme = preference === 'system'
    ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    : preference
  document.documentElement.dataset.theme = theme
  document.documentElement.style.colorScheme = theme
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#171719' : '#fcfcfd')
}

export function saveThemePreference(preference: ThemePreference) {
  try { window.localStorage.setItem(STORAGE_KEY, preference) } catch { /* Session-only theme is fine. */ }
  applyTheme(preference)
}
