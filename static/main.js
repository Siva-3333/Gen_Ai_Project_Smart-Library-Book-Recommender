/**
 * Global Main Application Utilities.
 * Handles Toast notifications, navbar scroll shadows, and shared event listeners.
 */

(function () {
  "use strict";

  // Global Toast Dispatcher
  window.slToast = function (message, type = "info") {
    let container = document.getElementById("sl-toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "sl-toast-container";
      container.className = "toast-container position-fixed bottom-0 end-0 p-3";
      container.style.zIndex = "1095";
      document.body.appendChild(container);
    }

    const toastEl = document.createElement("div");
    toastEl.className = `toast align-items-center text-bg-${type === 'error' ? 'danger' : type} border-0 shadow-lg`;
    toastEl.setAttribute("role", "alert");
    toastEl.setAttribute("aria-live", "assertive");
    toastEl.setAttribute("aria-atomic", "true");

    const iconMap = {
      success: "check-circle-fill",
      danger: "exclamation-circle-fill",
      error: "exclamation-triangle-fill",
      warning: "exclamation-triangle-fill",
      info: "info-circle-fill",
    };
    const icon = iconMap[type] || "bell-fill";

    toastEl.innerHTML = `
      <div class="d-flex">
        <div class="toast-body d-flex align-items-center">
          <i class="bi bi-${icon} me-2 fs-5"></i>
          <div>${message}</div>
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    `;

    container.appendChild(toastEl);
    const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
    toast.show();

    toastEl.addEventListener("hidden.bs.toast", () => {
      toastEl.remove();
    });
  };

  // Navbar dynamic scroll shadow
  window.addEventListener("scroll", () => {
    const nav = document.querySelector(".navbar-custom");
    if (nav) {
      if (window.scrollY > 20) {
        nav.classList.add("scrolled");
      } else {
        nav.classList.remove("scrolled");
      }
    }
  });

  // Client-side quick search redirect for hero input
  window.addEventListener("DOMContentLoaded", () => {
    const heroForm = document.getElementById("hero-search-form");
    if (heroForm) {
      heroForm.addEventListener("submit", (e) => {
        const input = document.getElementById("hero-search-input");
        if (!input && !input.value.trim()) {
          e.preventDefault();
          window.slToast("Please enter a topic, book title, or question to search.", "warning");
        }
      });
    }

    // ── Instant Page Navigation Shimmer Loader ──
    const loader = document.createElement("div");
    loader.id = "sl-page-loader";
    document.body.appendChild(loader);

    function startLoader() {
      loader.classList.remove("finish");
      loader.classList.add("loading");
    }

    function finishLoader() {
      loader.classList.remove("loading");
      loader.classList.add("finish");
      setTimeout(() => {
        loader.classList.remove("finish");
      }, 400);
    }

    window.addEventListener("pageshow", finishLoader);

    // Intercept clicks on internal navigation links for instant tactile feedback
    document.addEventListener("click", (e) => {
      const link = e.target.closest("a");
      if (!link) return;

      const href = link.getAttribute("href");
      if (!href) return;

      // Ignore hash links, javascript:, new-tab targets, or external links
      if (href.startsWith("#") || href.startsWith("javascript:") || link.target === "_blank") return;
      if (href.startsWith("http") && !href.startsWith(window.location.origin)) return;

      // Start the top progress indicator
      startLoader();
    });

    // ── Pre-warming / Prefetching Cache on Nav Hover ──
    const prefetchedUrls = new Set();
    const navLinks = document.querySelectorAll(".nav-link-custom, .navbar-brand");

    navLinks.forEach((link) => {
      link.addEventListener("pointerenter", () => {
        const href = link.getAttribute("href");
        if (!href || href.startsWith("#") || prefetchedUrls.has(href)) return;

        prefetchedUrls.add(href);
        // Soft pre-warm fetch to prime server memory cache
        try {
          fetch(href, { method: "GET", priority: "low", credentials: "same-origin" }).catch(() => {});
        } catch (_) {}
      }, { passive: true });
    });
  });
})();

