// FleetFlow — theme toggle wiring.
//
// The no-FOUC bootstrap in the <head> already set the initial data-theme if the
// user has a stored preference. Here we handle: the toggle button click, the
// keyboard shortcut, and keeping things in sync across tabs.

(function () {
  "use strict";

  var STORAGE_KEY = "fleetflow.theme";
  var root = document.documentElement;

  function currentTheme() {
    var explicit = root.getAttribute("data-theme");
    if (explicit === "dark" || explicit === "light") {
      return explicit;
    }
    // Fall back to system preference if the user hasn't chosen.
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  }

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (_) {
      // Private mode / storage disabled — the toggle still works for the session.
    }
    // Repaint the browser UI chrome to match.
    var metas = document.querySelectorAll('meta[name="theme-color"]');
    metas.forEach(function (meta) {
      var media = meta.getAttribute("media");
      if (!media) return;
      if ((theme === "dark" && media.indexOf("dark") !== -1) || (theme === "light" && media.indexOf("light") !== -1)) {
        meta.setAttribute("content", meta.getAttribute("content"));
      }
    });
  }

  function toggleTheme() {
    var next = currentTheme() === "dark" ? "light" : "dark";
    applyTheme(next);
    updateAriaPressed(next);
  }

  function updateAriaPressed(theme) {
    var btn = document.getElementById("themeToggle");
    if (btn) {
      btn.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
    }
  }

  function bindToggle() {
    var btn = document.getElementById("themeToggle");
    if (!btn) return;
    updateAriaPressed(currentTheme());
    btn.addEventListener("click", toggleTheme);
  }

  // Keyboard shortcut: ⌘/Ctrl + Shift + L (same as VS Code).
  function bindShortcut() {
    document.addEventListener("keydown", function (event) {
      if ((event.metaKey || event.ctrlKey) && event.shiftKey && event.key.toLowerCase() === "l") {
        event.preventDefault();
        toggleTheme();
      }
    });
  }

  // Cross-tab sync — flip when another tab toggles.
  function bindStorageSync() {
    window.addEventListener("storage", function (event) {
      if (event.key === STORAGE_KEY && (event.newValue === "dark" || event.newValue === "light")) {
        root.setAttribute("data-theme", event.newValue);
        updateAriaPressed(event.newValue);
      }
    });
  }

  // Follow system changes when user hasn't set an explicit preference.
  function bindSystemSync() {
    if (!window.matchMedia) return;
    var mq = window.matchMedia("(prefers-color-scheme: dark)");
    var listener = function () {
      try {
        if (!localStorage.getItem(STORAGE_KEY)) {
          // No explicit override — repaint aria state only.
          updateAriaPressed(mq.matches ? "dark" : "light");
        }
      } catch (_) {}
    };
    if (mq.addEventListener) {
      mq.addEventListener("change", listener);
    } else if (mq.addListener) {
      mq.addListener(listener);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      bindToggle();
      bindShortcut();
      bindStorageSync();
      bindSystemSync();
    });
  } else {
    bindToggle();
    bindShortcut();
    bindStorageSync();
    bindSystemSync();
  }
})();
