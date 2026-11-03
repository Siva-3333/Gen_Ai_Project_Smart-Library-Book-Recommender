/**
 * Firebase Client Configuration and Initialization.
 *
 * Reads client credentials injected by Flask into window.FIREBASE_CONFIG,
 * initializes Firebase Authentication and Cloud Firestore, and provides
 * safe fallback handlers.
 */

(function () {
  "use strict";

  window.slFirebase = {
    initialized: false,
    auth: null,
    db: null,
    error: null,
  };

  const config = window.FIREBASE_CONFIG || {};

  // Check if at least apiKey and projectId are configured
  const isConfigured = Boolean(config.apiKey && config.projectId);

  if (isConfigured && typeof firebase !== "undefined") {
    try {
      if (!firebase.apps.length) {
        firebase.initializeApp(config);
      }
      window.slFirebase.auth = firebase.auth();
      window.slFirebase.db = firebase.firestore();
      window.slFirebase.initialized = true;
      console.log("Firebase Web Client initialized successfully.");
    } catch (err) {
      console.error("Firebase initialization failed:", err);
      window.slFirebase.error = err.message;
    }
  } else {
    const reason = !isConfigured
      ? "Firebase client credentials are not yet set in .env. Using Flask session backend."
      : "Firebase CDN SDK not loaded.";
    console.info("Smart Library Notice:", reason);
    window.slFirebase.error = reason;
  }
})();

