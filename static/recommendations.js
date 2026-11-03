/**
 * Intelligent Recommendation & Conversational AI Assistant Client Module.
 * Integrates:
 * - Hybrid Recommender with 5-weight factors (35/25/15/15/10)
 * - Sentence Transformers + FAISS vector search
 * - Interactive AI Book Discovery Assistant with multi-turn context memory
 */

(function () {
  "use strict";

  // Conversational Assistant State Memory
  let chatHistory = [];
  let conversationContext = {
    subject: "",
    category: "",
    reading_level: "All Levels",
  };

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // =========================================================================
  // VIEW SWITCHER: HYBRID RECOMMENDER <-> AI DISCOVERY ASSISTANT
  // =========================================================================
  function initViewSwitcher() {
    const btnRecommender = document.getElementById("nav-btn-recommender");
    const btnAssistant = document.getElementById("nav-btn-assistant");
    const viewRecommender = document.getElementById("recommender-view-container");
    const viewAssistant = document.getElementById("assistant-view-container");

    if (!btnRecommender || !btnAssistant || !viewRecommender || !viewAssistant) return;

    btnRecommender.addEventListener("click", function () {
      btnRecommender.className = "btn btn-primary-sl rounded-pill px-4 py-2";
      btnAssistant.className = "btn btn-outline-primary rounded-pill px-4 py-2";
      viewRecommender.classList.remove("d-none");
      viewAssistant.classList.add("d-none");
    });

    btnAssistant.addEventListener("click", function () {
      btnAssistant.className = "btn btn-primary-sl rounded-pill px-4 py-2";
      btnRecommender.className = "btn btn-outline-primary rounded-pill px-4 py-2";
      viewAssistant.classList.remove("d-none");
      viewRecommender.classList.add("d-none");
      const chatInput = document.getElementById("assistant-chat-input");
      if (chatInput) chatInput.focus();
    });
  }

  // =========================================================================
  // HYBRID RECOMMENDER CARD & ACCORDION RENDERING (35/25/15/15/10)
  // =========================================================================
  function renderQueryAnalysis(analysis) {
    const container = document.getElementById("query-analysis-container");
    if (!container) return;

    container.innerHTML = `
      <div class="glass-card p-4" style="border-radius: var(--sl-radius-lg);">
        <div class="d-flex align-items-center mb-3">
          <i class="bi bi-cpu-fill text-primary me-2 fs-5"></i>
          <h5 class="mb-0 fw-bold">Natural Language Query Analysis</h5>
        </div>
        <div class="row g-3 text-muted small">
          <div class="col-6 col-md-3">
            <span class="d-block text-secondary fw-bold text-uppercase" style="font-size: 0.72rem; letter-spacing: 0.05em;">Target Subject</span>
            <span class="badge bg-primary text-white fs-6 mt-1 px-3 py-1 rounded-pill">${escapeHtml(analysis.subject || "General")}</span>
          </div>
          <div class="col-6 col-md-3">
            <span class="d-block text-secondary fw-bold text-uppercase" style="font-size: 0.72rem; letter-spacing: 0.05em;">Domain Category</span>
            <span class="badge bg-info text-dark fs-6 mt-1 px-3 py-1 rounded-pill">${escapeHtml(analysis.category || "General")}</span>
          </div>
          <div class="col-6 col-md-3">
            <span class="d-block text-secondary fw-bold text-uppercase" style="font-size: 0.72rem; letter-spacing: 0.05em;">Detected Level</span>
            <span class="badge bg-warning text-dark fs-6 mt-1 px-3 py-1 rounded-pill">${escapeHtml(analysis.reading_level || "All Levels")}</span>
          </div>
          <div class="col-6 col-md-3">
            <span class="d-block text-secondary fw-bold text-uppercase" style="font-size: 0.72rem; letter-spacing: 0.05em;">Learning Purpose</span>
            <span class="badge bg-secondary text-white fs-6 mt-1 px-3 py-1 rounded-pill">${escapeHtml(analysis.purpose || "Learning")}</span>
          </div>
        </div>
      </div>
    `;
    container.classList.remove("d-none");
  }

  function renderBooks(recommendations) {
    const grid = document.getElementById("recommendations-grid");
    if (!grid) return;

    if (!recommendations || recommendations.length === 0) {
      grid.innerHTML = `
        <div class="col-12 text-center py-5">
          <i class="bi bi-search display-3 text-muted mb-3"></i>
          <h4>No matching books found</h4>
          <p class="text-muted">Try rephrasing your search or using broader terms.</p>
        </div>
      `;
      return;
    }

    let html = "";
    recommendations.forEach((book) => {
      const breakdown = book.score_breakdown || {};
      const score = book.recommendation_score || 80;
      const safeTitle = escapeHtml(book.title);
      const safeCategory = escapeHtml(book.category || "General");
      const safeAuthors = escapeHtml(book.authors_str || "Unknown Author");
      const safeReason = escapeHtml(book.recommendation_reason || "Grounded match based on semantic and discipline alignment.");

      html += `
        <div class="col-12 col-md-6 col-lg-4 col-xl-3">
          <div class="book-card-v2">
            <!-- Recommendation Match Score Pill -->
            <span class="rec-score-pill-v2">
              <i class="bi bi-lightning-charge-fill"></i>${score}% Match
            </span>

            <!-- Bookmark Action Ribbon -->
            <button
              type="button"
              class="bookmark-badge"
              title="Add to My Shelf"
              onclick="window.slAddToLibrary('${book.id}', 'want_to_read')"
              data-lib-btn="${book.id}"
            >
              <i class="bi bi-bookmark-plus"></i>
            </button>

            <!-- 3D Book Cover Stage -->
            <div class="book-card-cover-stage">
              <a href="/book/${book.id}">
                <img
                  src="${book.thumbnail}"
                  alt="${safeTitle}"
                  class="book-cover-3d"
                  loading="lazy"
                  onerror="this.src='/static/images/default-book.svg'"
                />
              </a>
            </div>

            <!-- Body Content -->
            <div class="book-card-content">
              <span class="book-category-tag">${safeCategory}</span>
              <h5 class="book-card-title" title="${safeTitle}">
                <a href="/book/${book.id}" class="text-decoration-none text-reset">
                  ${safeTitle}
                </a>
              </h5>
              <div class="book-card-author">${safeAuthors}</div>

              <!-- Recommendation Reason Pill -->
              <div class="p-2 mb-3 rounded border small text-muted" style="background-color: var(--sl-bg-subtle); border-color: var(--sl-border-subtle) !important; font-size: 0.76rem;">
                <i class="bi bi-info-circle-fill text-primary me-1"></i>
                ${safeReason}
              </div>

              <!-- Weighted Score Accordion (Exact 35/25/15/15/10 Weights) -->
              <details class="mb-3 score-breakdown-card">
                <summary class="text-muted small fw-semibold cursor-pointer" style="cursor: pointer;">
                  View Hybrid Factors (35/25/15/15/10)
                </summary>
                <div class="pt-2">
                  <div class="d-flex justify-content-between text-muted" style="font-size: 0.72rem;">
                    <span>Semantic Similarity (35%)</span>
                    <strong>${breakdown.semantic_similarity || score}%</strong>
                  </div>
                  <div class="progress mb-2" style="height: 4px;">
                    <div class="progress-bar bg-primary" style="width: ${breakdown.semantic_similarity || score}%;"></div>
                  </div>

                  <div class="d-flex justify-content-between text-muted" style="font-size: 0.72rem;">
                    <span>Subject Relevance (25%)</span>
                    <strong>${breakdown.subject_relevance || score}%</strong>
                  </div>
                  <div class="progress mb-2" style="height: 4px;">
                    <div class="progress-bar bg-info" style="width: ${breakdown.subject_relevance || score}%;"></div>
                  </div>

                  <div class="d-flex justify-content-between text-muted" style="font-size: 0.72rem;">
                    <span>Category Match (15%)</span>
                    <strong>${breakdown.category_matching || score}%</strong>
                  </div>
                  <div class="progress mb-2" style="height: 4px;">
                    <div class="progress-bar bg-warning" style="width: ${breakdown.category_matching || score}%;"></div>
                  </div>

                  <div class="d-flex justify-content-between text-muted" style="font-size: 0.72rem;">
                    <span>User Preferences (15%)</span>
                    <strong>${breakdown.user_preference || 80}%</strong>
                  </div>
                  <div class="progress mb-2" style="height: 4px;">
                    <div class="progress-bar bg-success" style="width: ${breakdown.user_preference || 80}%;"></div>
                  </div>

                  <div class="d-flex justify-content-between text-muted" style="font-size: 0.72rem;">
                    <span>Reading Level (10%)</span>
                    <strong>${breakdown.reading_level || 80}%</strong>
                  </div>
                  <div class="progress" style="height: 4px;">
                    <div class="progress-bar bg-secondary" style="width: ${breakdown.reading_level || 80}%;"></div>
                  </div>
                </div>
              </details>

              <div class="mt-auto d-flex gap-2 pt-2 border-top" style="border-color: var(--sl-border-subtle) !important;">
                <a href="/book/${book.id}" class="btn btn-secondary-sl btn-sm flex-grow-1">
                  <i class="bi bi-eye"></i> Details
                </a>
                <button
                  type="button"
                  class="btn btn-primary-sl btn-sm"
                  onclick="window.slAddToLibrary('${book.id}', 'want_to_read')"
                  title="Save to Library"
                >
                  <i class="bi bi-plus-lg"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
    });

    grid.innerHTML = html;
  }

  // =========================================================================
  // AI BOOK DISCOVERY ASSISTANT (CONVERSATIONAL MULTI-TURN RAG)
  // =========================================================================
  function initAssistant() {
    const chatForm = document.getElementById("assistant-chat-form");
    const chatInput = document.getElementById("assistant-chat-input");
    const chatStream = document.getElementById("assistant-chat-stream");
    const btnReset = document.getElementById("btn-reset-chat");
    const quickPrompts = document.querySelectorAll(".assistant-quick-prompt");

    if (!chatForm || !chatInput || !chatStream) return;

    function appendUserMessage(text) {
      const msgDiv = document.createElement("div");
      msgDiv.className = "d-flex justify-content-end mb-3";
      msgDiv.innerHTML = `
        <div class="p-3 rounded-3 shadow-sm text-white" style="max-width: 80%; background: linear-gradient(135deg, #0D9488 0%, #2563EB 100%);">
          <div class="small fw-medium">${escapeHtml(text)}</div>
        </div>
      `;
      chatStream.appendChild(msgDiv);
      chatStream.scrollTop = chatStream.scrollHeight;
    }

    function appendAssistantLoading() {
      const loadDiv = document.createElement("div");
      loadDiv.id = "assistant-loading-indicator";
      loadDiv.className = "d-flex gap-2 mb-3";
      loadDiv.innerHTML = `
        <div class="text-primary fs-4 flex-shrink-0"><i class="bi bi-robot"></i></div>
        <div class="p-3 rounded-3 shadow-sm d-flex align-items-center gap-2" style="background: var(--sl-bg-card); border: 1px solid var(--sl-border);">
          <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
          <span class="small text-muted">Retrieving candidate volumes &amp; computing FAISS embeddings...</span>
        </div>
      `;
      chatStream.appendChild(loadDiv);
      chatStream.scrollTop = chatStream.scrollHeight;
      return loadDiv;
    }

    function appendAssistantResponse(replyText, books) {
      const loader = document.getElementById("assistant-loading-indicator");
      if (loader) loader.remove();

      const msgDiv = document.createElement("div");
      msgDiv.className = "d-flex gap-2 mb-3";

      let booksHtml = "";
      if (books && books.length > 0) {
        booksHtml = `<div class="row g-2 mt-2">`;
        books.forEach((b) => {
          const score = b.recommendation_score || b.semantic_similarity_percent || 85;
          booksHtml += `
            <div class="col-12 col-md-6">
              <div class="p-2 rounded-3 border d-flex gap-2 align-items-center" style="background-color: var(--sl-bg-subtle); border-color: var(--sl-border-subtle) !important;">
                <img
                  src="${b.thumbnail || '/static/images/default-book.svg'}"
                  alt="${escapeHtml(b.title)}"
                  width="45"
                  height="60"
                  class="rounded-1 shadow-sm flex-shrink-0"
                  style="object-fit: cover;"
                  onerror="this.src='/static/images/default-book.svg'"
                />
                <div class="overflow-hidden flex-grow-1">
                  <div class="d-flex align-items-center gap-1 mb-1">
                    <span class="badge bg-primary text-white" style="font-size: 0.65rem;">${score}% Match</span>
                    <span class="badge bg-secondary text-white" style="font-size: 0.65rem;">${escapeHtml(b.category || "Book")}</span>
                  </div>
                  <a href="/book/${b.id}" class="fw-bold text-body text-decoration-none small d-block text-truncate">
                    ${escapeHtml(b.title)}
                  </a>
                  <div class="text-muted" style="font-size: 0.72rem;">${escapeHtml(b.authors_str || "Author")}</div>
                </div>
                <button
                  type="button"
                  class="btn btn-sm btn-outline-primary rounded-circle flex-shrink-0"
                  style="width: 32px; height: 32px; padding: 0;"
                  onclick="window.slAddToLibrary('${b.id}', 'want_to_read')"
                  title="Add to Shelf"
                >
                  <i class="bi bi-bookmark-plus"></i>
                </button>
              </div>
            </div>
          `;
        });
        booksHtml += `</div>`;
      }

      msgDiv.innerHTML = `
        <div class="text-primary fs-4 flex-shrink-0"><i class="bi bi-robot"></i></div>
        <div class="p-3 rounded-3 shadow-sm" style="max-width: 88%; background: var(--sl-bg-card); border: 1px solid var(--sl-border);">
          <div class="fw-semibold text-body mb-1">AI Discovery Assistant</div>
          <div class="small text-muted" style="line-height: 1.5;">${escapeHtml(replyText)}</div>
          ${booksHtml}
        </div>
      `;

      chatStream.appendChild(msgDiv);
      chatStream.scrollTop = chatStream.scrollHeight;
    }

    async function sendChatMessage(message) {
      if (!message.trim()) return;

      appendUserMessage(message);
      chatHistory.push({ role: "user", content: message });
      chatInput.value = "";
      appendAssistantLoading();

      try {
        const response = await fetch("/api/ai-assistant/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: message,
            history: chatHistory.slice(-8),
            context: conversationContext,
          }),
        });

        const data = await response.json();
        if (data.success) {
          if (data.context) {
            conversationContext = Object.assign(conversationContext, data.context);
          }
          chatHistory.push({ role: "assistant", content: data.reply });
          appendAssistantResponse(data.reply, data.books);
        } else {
          appendAssistantResponse("I encountered an issue retrieving books. Please try rephrasing your goal.", []);
        }
      } catch (err) {
        appendAssistantResponse("A network error occurred connecting to the RAG pipeline. Please verify your connection.", []);
      }
    }

    chatForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const text = chatInput.value.trim();
      if (text) {
        sendChatMessage(text);
      }
    });

    quickPrompts.forEach((btn) => {
      btn.addEventListener("click", function () {
        const promptText = btn.getAttribute("data-text");
        if (promptText) {
          sendChatMessage(promptText);
        }
      });
    });

    if (btnReset) {
      btnReset.addEventListener("click", function () {
        chatHistory = [];
        conversationContext = { subject: "", category: "", reading_level: "All Levels" };
        chatStream.innerHTML = `
          <div class="d-flex gap-2 mb-3">
            <div class="text-primary fs-4 flex-shrink-0"><i class="bi bi-robot"></i></div>
            <div class="p-3 rounded-3 shadow-sm" style="max-width: 85%; background: var(--sl-bg-card); border: 1px solid var(--sl-border);">
              <div class="fw-semibold text-body mb-1">AI Discovery Assistant</div>
              <div class="small text-muted" style="line-height: 1.5;">
                Chat history reset. How can I help you discover books today?
              </div>
            </div>
          </div>
        `;
      });
    }
  }

  // =========================================================================
  // SAMPLE PILL CLICK HANDLERS
  // =========================================================================
  function initSamplePills() {
    const pills = document.querySelectorAll(".sample-query-pill");
    const input = document.getElementById("rec-query-input");
    const form = document.getElementById("recommendation-form");

    pills.forEach((p) => {
      p.addEventListener("click", function () {
        const q = p.getAttribute("data-query");
        if (input && form) {
          input.value = q;
          form.submit();
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initViewSwitcher();
    initAssistant();
    initSamplePills();
  });
})();
