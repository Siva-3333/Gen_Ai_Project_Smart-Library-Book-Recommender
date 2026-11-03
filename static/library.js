/**
 * Personal Library Module.
 * Handles adding books to library, changing reading status, and removal.
 */

(function () {
  "use strict";

  // Global helper to add book to library
  window.slAddToLibrary = async function (bookId, status = "want_to_read") {
    try {
      const res = await fetch("/api/library", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bookId: bookId, status: status }),
      });

      if (res.status === 401 || res.redirected) {
        window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
        return;
      }

      const data = await res.json();
      if (data.success) {
        window.slToast(data.message || "Book added to your library!", "success");

        // Update button visual state if on page
        const btn = document.querySelector(`[data-lib-btn="${bookId}"]`);
        if (btn) {
          btn.classList.remove("btn-outline-primary");
          btn.classList.add("btn-success");
          btn.innerHTML = '<i class="bi bi-bookmark-check-fill me-1"></i>Saved';
        }
      } else {
        window.slToast(data.message || "Failed to add book.", "warning");
      }
    } catch (err) {
      console.error("Library addition failed:", err);
      window.slToast("An error occurred while saving the book.", "error");
    }
  };

  // Status changer for My Library page
  window.slUpdateStatus = async function (bookId, newStatus) {
    try {
      const res = await fetch("/api/library/status", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bookId: bookId, status: newStatus }),
      });

      const data = await res.json();
      if (data.success) {
        window.slToast(data.message || "Status updated!", "success");
        // Reload after brief delay to show toast
        setTimeout(() => window.location.reload(), 600);
      } else {
        window.slToast(data.message || "Update failed.", "warning");
      }
    } catch (err) {
      console.error("Status update error:", err);
      window.slToast("Failed to update reading status.", "error");
    }
  };

  // Remove from library
  window.slRemoveFromLibrary = async function (bookId) {
    if (!confirm("Are you sure you want to remove this book from your library?")) {
      return;
    }

    try {
      const res = await fetch(`/api/library/${bookId}`, {
        method: "DELETE",
      });

      const data = await res.json();
      if (data.success) {
        window.slToast(data.message || "Book removed.", "info");
        const cardCol = document.getElementById(`lib-card-${bookId}`);
        if (cardCol) {
          cardCol.style.transition = "opacity 0.3s, transform 0.3s";
          cardCol.style.opacity = "0";
          cardCol.style.transform = "scale(0.9)";
          setTimeout(() => cardCol.remove(), 350);
        } else {
          setTimeout(() => window.location.reload(), 500);
        }
      } else {
        window.slToast(data.message || "Could not remove book.", "warning");
      }
    } catch (err) {
      console.error("Removal error:", err);
      window.slToast("Failed to remove book.", "error");
    }
  };

  // Setup click triggers on library buttons across any page
  window.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".btn-add-to-library").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const bookId = btn.getAttribute("data-book-id");
        const status = btn.getAttribute("data-status") || "want_to_read";
        if (bookId) {
          window.slAddToLibrary(bookId, status);
        }
      });
    });

    // Setup Edit Page Modal Save Trigger
    const saveBtn = document.getElementById("edit-modal-save-btn");
    if (saveBtn) {
      saveBtn.addEventListener("click", async () => {
        const bookId = document.getElementById("edit-modal-book-id").value;
        const pageInput = document.getElementById("edit-modal-page-input");
        const total = parseInt(document.getElementById("edit-modal-total-pages").textContent, 10) || 200;
        const pageVal = parseInt(pageInput.value, 10) || 0;

        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';

        await window.slUpdateReadingProgress(bookId, pageVal, total);

        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Save Progress';

        const modalEl = document.getElementById("sl-edit-page-modal");
        const bsModal = bootstrap.Modal.getInstance(modalEl);
        if (bsModal) bsModal.hide();
      });
    }
  });

  // ── Increment Completed Page by 1 (+1 Page Action) ──
  window.slIncrementPage = async function (bookId, e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }

    const btn = e ? e.currentTarget : null;
    let origHtml = "";
    if (btn) {
      origHtml = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    }

    try {
      const res = await fetch("/api/library/progress", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bookId: bookId, action: "increment" }),
      });

      if (res.status === 401 || res.redirected) {
        window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
        return;
      }

      const data = await res.json();
      if (data.success) {
        // Update all DOM elements for this book on the current page
        document.querySelectorAll(`[data-page-val="${bookId}"]`).forEach(el => {
          el.textContent = data.currentPage;
        });
        document.querySelectorAll(`[data-progress-bar="${bookId}"]`).forEach(el => {
          el.style.width = data.progressPercent + "%";
        });
        document.querySelectorAll(`[data-progress-percent="${bookId}"]`).forEach(el => {
          el.textContent = data.progressPercent + "%";
        });

        window.slToast(`Marked Page ${data.currentPage} completed! (${data.progressPercent}%) 📖`, "success");

        if (data.readingStatus === "completed") {
          window.slToast("🎉 Congratulations! You have completed this volume!", "success");
          setTimeout(() => window.location.reload(), 1200);
        }
      } else {
        window.slToast(data.message || "Failed to update page progress.", "warning");
      }
    } catch (err) {
      console.error("Increment page error:", err);
      window.slToast("Failed to mark page completed.", "error");
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = origHtml;
      }
    }
  };

  // ── Set Explicit Completed Page ──
  window.slUpdateReadingProgress = async function (bookId, currentPage, totalPages) {
    try {
      const res = await fetch("/api/library/progress", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bookId: bookId,
          currentPage: currentPage,
          totalPages: totalPages,
          action: "set",
        }),
      });

      if (res.status === 401 || res.redirected) {
        window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
        return;
      }

      const data = await res.json();
      if (data.success) {
        document.querySelectorAll(`[data-page-val="${bookId}"]`).forEach(el => {
          el.textContent = data.currentPage;
        });
        document.querySelectorAll(`[data-progress-bar="${bookId}"]`).forEach(el => {
          el.style.width = data.progressPercent + "%";
        });
        document.querySelectorAll(`[data-progress-percent="${bookId}"]`).forEach(el => {
          el.textContent = data.progressPercent + "%";
        });

        window.slToast(`Progress updated: Completed Page ${data.currentPage} of ${data.pageCount} (${data.progressPercent}%)`, "success");
        return data;
      } else {
        window.slToast(data.message || "Failed to update progress.", "warning");
      }
    } catch (err) {
      console.error("Update progress error:", err);
      window.slToast("An error occurred while updating page progress.", "error");
    }
  };

  // ── Quick Modal Page Adjustment ──
  window.slQuickAdjustModalPage = function (delta) {
    const pageInput = document.getElementById("edit-modal-page-input");
    const total = parseInt(document.getElementById("edit-modal-total-pages").textContent, 10) || 200;
    let current = parseInt(pageInput.value, 10) || 0;
    current = Math.min(total, Math.max(0, current + delta));
    pageInput.value = current;
    pageInput.dispatchEvent(new Event("input"));
  };

  // ── Open Global Interactive Page Edit Modal ──
  window.slOpenPageEditModal = function (bookId, title, currentPage, totalPages) {
    let modalEl = document.getElementById("sl-edit-page-modal");
    if (!modalEl) {
      console.warn("Edit page modal element not found.");
      return;
    }

    totalPages = parseInt(totalPages, 10) || 200;
    currentPage = parseInt(currentPage, 10) || 0;

    document.getElementById("edit-modal-book-id").value = bookId;
    document.getElementById("edit-modal-book-title").textContent = title || "Book Progress";
    const pageInput = document.getElementById("edit-modal-page-input");
    pageInput.value = currentPage;
    pageInput.max = totalPages;
    document.getElementById("edit-modal-total-pages").textContent = totalPages;

    function updatePreview() {
      const val = Math.min(totalPages, Math.max(0, parseInt(pageInput.value, 10) || 0));
      const pct = Math.min(100, Math.max(0, Math.round((val / totalPages) * 100)));
      document.getElementById("edit-modal-progress-bar").style.width = pct + "%";
      document.getElementById("edit-modal-pct-label").textContent = pct + "%";
    }

    pageInput.oninput = updatePreview;
    updatePreview();

    const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
    bsModal.show();
  };
})();

