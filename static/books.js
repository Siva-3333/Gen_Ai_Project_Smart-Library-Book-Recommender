/**
 * Explore & Book Details Client Module.
 * Provides interactive search debounce, filters, reviews management,
 * and related books browsing.
 */

(function () {
  "use strict";

  // Debounce helper
  function debounce(func, delay = 400) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => func.apply(this, args), delay);
    };
  }

  // Setup review submission on book details page
  function setupReviewForm() {
    const form = document.getElementById("book-review-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const bookId = form.getAttribute("data-book-id");
      const rating = form.querySelector('input[name="rating"]:checked');
      const textInput = document.getElementById("review-text");
      const submitBtn = document.getElementById("submit-review-btn");

      if (!rating) {
        window.slToast("Please select a star rating (1-5).", "warning");
        return;
      }
      if (!textInput || !textInput.value.trim()) {
        window.slToast("Please write a short review.", "warning");
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Posting...';

      try {
        const res = await fetch(`/api/reviews/${bookId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            rating: rating.value,
            reviewText: textInput.value.trim(),
          }),
        });

        if (res.status === 401 || res.redirected) {
          window.location.href = `/login?next=/book/${bookId}`;
          return;
        }

        const data = await res.json();
        if (data.success) {
          window.slToast("Thank you! Your review has been saved.", "success");
          setTimeout(() => window.location.reload(), 600);
        } else {
          window.slToast(data.message || "Failed to submit review.", "error");
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="bi bi-send-fill me-1"></i>Submit Review';
        }
      } catch (err) {
        console.error("Review submission error:", err);
        window.slToast("An error occurred while posting your review.", "error");
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="bi bi-send-fill me-1"></i>Submit Review';
      }
    });
  }

  // Delete review helper
  window.slDeleteReview = async function (bookId) {
    if (!confirm("Are you sure you want to delete your review?")) return;

    try {
      const res = await fetch(`/api/reviews/${bookId}`, {
        method: "DELETE",
      });
      const data = await res.json();
      if (data.success) {
        window.slToast("Review deleted.", "info");
        setTimeout(() => window.location.reload(), 500);
      } else {
        window.slToast(data.message || "Failed to delete review.", "warning");
      }
    } catch (err) {
      console.error("Delete review error:", err);
      window.slToast("Network error.", "error");
    }
  };

  window.addEventListener("DOMContentLoaded", () => {
    setupReviewForm();
  });
})();

