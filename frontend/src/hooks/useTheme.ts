import { useCallback, useEffect, useState } from "react";

type Theme = "light" | "dark";

const STORAGE_KEY = "buddy-theme";

function currentTheme(): Theme {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

export function useTheme() {
  // Initialised from the DOM because index.html already resolved the theme
  // before React mounted.
  const [theme, setTheme] = useState<Theme>(currentTheme);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((previous) => (previous === "dark" ? "light" : "dark"));
  }, []);

  return { theme, toggle };
}
