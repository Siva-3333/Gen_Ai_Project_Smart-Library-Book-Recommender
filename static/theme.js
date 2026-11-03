/**
 * Theme Switcher (Dark / Light Mode)
 * Persists theme state in localStorage and toggles Bootstrap 5 data-bs-theme attribute.
 */

(function () {
  "use strict";

  const THEME_KEY = "sl_theme_preference_v2";

  function getStoredTheme() {
    return localStorage.getItem(THEME_KEY);
  }

  function setStoredTheme(theme) {
    localStorage.setItem(THEME_KEY, theme);
  }

  function getPreferredTheme() {
    const stored = getStoredTheme();
    if (stored) {
      return stored;
    }
    // Professional Light Theme Default
    return "light";
  }

  function setTheme(theme) {
    document.documentElement.setAttribute("data-bs-theme", theme);
    updateThemeIcon(theme);
  }

  function updateThemeIcon(theme) {
    const icon = document.getElementById("theme-toggle-icon");
    const toggleBtn = document.getElementById("theme-toggle-btn");
    if (!icon) return;
    if (theme === "dark") {
      icon.className = "bi bi-sun-fill";
      if (toggleBtn) {
        toggleBtn.setAttribute("title", "Switch to Light Mode");
        toggleBtn.setAttribute("aria-label", "Switch to Light Mode");
      }
    } else {
      icon.className = "bi bi-moon-stars-fill";
      if (toggleBtn) {
        toggleBtn.setAttribute("title", "Switch to Dark Mode");
        toggleBtn.setAttribute("aria-label", "Switch to Dark Mode");
      }
    }
  }

  // Set theme immediately to avoid flash of wrong theme
  const initialTheme = getPreferredTheme();
  setTheme(initialTheme);

  window.addEventListener("DOMContentLoaded", () => {
    updateThemeIcon(getPreferredTheme());

    const toggleBtn = document.getElementById("theme-toggle-btn");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => {
        // Trigger smooth 360-degree morph spin animation
        toggleBtn.classList.remove("theme-animating");
        void toggleBtn.offsetWidth; // Force DOM reflow
        toggleBtn.classList.add("theme-animating");
        setTimeout(() => {
          toggleBtn.classList.remove("theme-animating");
        }, 650);

        const current = document.documentElement.getAttribute("data-bs-theme") || "light";
        const next = current === "dark" ? "light" : "dark";
        setStoredTheme(next);
        setTheme(next);
      });
    }
  });

  // Expose global helper
  window.slTheme = {
    get: getPreferredTheme,
    set: (t) => { setStoredTheme(t); setTheme(t); }
  };
})();

