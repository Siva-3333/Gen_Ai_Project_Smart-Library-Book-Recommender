/**
 * Authentication Module.
 *
 * Coordinates Firebase Authentication (email/password, Google sign-in, password reset)
 * with the Flask backend session synchronization.
 */

(function () {
  "use strict";

  // Helper to show inline alerts inside auth form
  function showAuthAlert(message, type = "danger") {
    const alertBox = document.getElementById("auth-alert");
    if (!alertBox) return;
    alertBox.className = `alert alert-${type} alert-dismissible fade show`;
    alertBox.innerHTML = `
      <i class="bi bi-${type === 'danger' ? 'exclamation-circle' : 'check-circle'}-fill me-2"></i>
      <span>${message}</span>
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    alertBox.classList.remove("d-none");
  }

  // Password visibility toggle
  function setupPasswordToggles() {
    const toggleBtns = document.querySelectorAll(".toggle-password-btn");
    toggleBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const inputId = btn.getAttribute("data-target");
        const input = document.getElementById(inputId);
        const icon = btn.querySelector("i");
        if (input) {
          if (input.type === "password") {
            input.type = "text";
            icon.className = "bi bi-eye-slash";
          } else {
            input.type = "password";
            icon.className = "bi bi-eye";
          }
        }
      });
    });
  }

  // Synchronize Firebase Auth with Flask session backend
  async function syncSession(user, displayName, favouriteCategories = null) {
    try {
      const payload = {
        uid: user.uid,
        email: user.email,
        displayName: displayName || user.displayName || user.email.split("@")[0],
        favouriteCategories: favouriteCategories,
      };

      const res = await fetch("/api/auth/session-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!data.success) {
        throw new Error(data.message || "Failed to establish server session.");
      }
      return data;
    } catch (err) {
      console.error("Session sync failed:", err);
      throw err;
    }
  }

  // Setup Login Form
  function setupLoginForm() {
    const form = document.getElementById("login-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("login-email").value.trim();
      const password = document.getElementById("login-password").value;
      const submitBtn = document.getElementById("login-submit-btn");

      if (!email || !password) {
        showAuthAlert("Please provide both email and password.");
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Logging in...';

      try {
        if (window.slFirebase.initialized && window.slFirebase.auth) {
          // Direct Firebase Authentication
          const cred = await window.slFirebase.auth.signInWithEmailAndPassword(email, password);
          await syncSession(cred.user, cred.user.displayName);
        } else {
          // Standalone Dev Fallback: Create safe developer session
          const dummyUid = "dev_" + btoa(email).replace(/=/g, "").slice(0, 16);
          await syncSession({ uid: dummyUid, email: email }, email.split("@")[0]);
        }

        const nextUrl = new URLSearchParams(window.location.search).get("next") || "/dashboard";
        window.location.href = nextUrl;
      } catch (err) {
        console.error("Login error:", err);
        let msg = err.message || "Authentication failed.";
        if (err.code === "auth/user-not-found" || err.code === "auth/wrong-password" || err.code === "auth/invalid-credential") {
          msg = "Invalid email or password. Please verify your credentials.";
        }
        showAuthAlert(msg);
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="bi bi-box-arrow-in-right me-2"></i>Sign In';
      }
    });
  }

  // Setup Registration Form
  function setupRegisterForm() {
    const form = document.getElementById("register-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fullName = document.getElementById("reg-name").value.trim();
      const email = document.getElementById("reg-email").value.trim();
      const password = document.getElementById("reg-password").value;
      const confirmPassword = document.getElementById("reg-confirm-password").value;
      const submitBtn = document.getElementById("register-submit-btn");

      // Collect selected categories
      const selectedCats = [];
      document.querySelectorAll('input[name="categories"]:checked').forEach((cb) => {
        selectedCats.push(cb.value);
      });

      // Validation
      if (!fullName) {
        showAuthAlert("Please enter your full name.");
        return;
      }
      if (!email) {
        showAuthAlert("Please enter a valid email address.");
        return;
      }
      if (password.length < 6) {
        showAuthAlert("Password must be at least 6 characters long.");
        return;
      }
      if (password !== confirmPassword) {
        showAuthAlert("Passwords do not match.");
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Creating Account...';

      try {
        if (window.slFirebase.initialized && window.slFirebase.auth) {
          const cred = await window.slFirebase.auth.createUserWithEmailAndPassword(email, password);
          await cred.user.updateProfile({ displayName: fullName });
          await syncSession(cred.user, fullName, selectedCats);
        } else {
          // Dev Fallback
          const dummyUid = "dev_" + btoa(email).replace(/=/g, "").slice(0, 16);
          await syncSession({ uid: dummyUid, email: email }, fullName, selectedCats);
        }

        window.location.href = "/dashboard";
      } catch (err) {
        console.error("Registration error:", err);
        let msg = err.message || "Failed to create account.";
        if (err.code === "auth/email-already-in-use") {
          msg = "This email is already registered. Please sign in or use another email.";
        }
        showAuthAlert(msg);
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="bi bi-person-plus-fill me-2"></i>Create Account';
      }
    });
  }

  // Setup Forgot Password Modal / Trigger
  function setupForgotPassword() {
    const btn = document.getElementById("forgot-password-link");
    if (!btn) return;

    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const emailInput = document.getElementById("login-email");
      const email = emailInput ? emailInput.value.trim() : "";

      if (!email) {
        showAuthAlert("Please enter your email address in the field above to reset your password.", "warning");
        if (emailInput) emailInput.focus();
        return;
      }

      if (window.slFirebase.initialized && window.slFirebase.auth) {
        try {
          await window.slFirebase.auth.sendPasswordResetEmail(email);
          showAuthAlert(`Password reset link sent to ${email}. Check your inbox!`, "success");
        } catch (err) {
          showAuthAlert(err.message || "Failed to send reset email.", "danger");
        }
      } else {
        showAuthAlert(`Password reset simulation sent to ${email}. Configure Firebase credentials to enable live reset emails.`, "info");
      }
    });
  }

  // Setup Google Sign-In
  function setupGoogleAuth() {
    const googleBtns = document.querySelectorAll(".btn-google-auth");
    if (!googleBtns.length) return;

    googleBtns.forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!window.slFirebase.initialized || !window.slFirebase.auth) {
          showAuthAlert("Google Authentication requires Firebase API credentials in .env.", "warning");
          return;
        }

        const provider = new firebase.auth.GoogleAuthProvider();

        try {
          btn.disabled = true;
          const origHtml = btn.innerHTML;
          btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Connecting Google...';

          const result = await window.slFirebase.auth.signInWithPopup(provider);

          btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Syncing Profile...';
          await syncSession(result.user, result.user.displayName);

          btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Opening Dashboard...';
          const nextUrl = new URLSearchParams(window.location.search).get("next") || "/dashboard";
          window.location.href = nextUrl;
        } catch (err) {
          console.error("Google sign-in error:", err);
          btn.disabled = false;
          btn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 18 18">
              <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.616z"/>
              <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z"/>
              <path fill="#FBBC05" d="M3.964 10.707c-.18-.54-.282-1.117-.282-1.707s.102-1.167.282-1.707V4.961H.957C.347 6.175 0 7.55 0 9s.347 2.825.957 4.039l3.007-2.332z"/>
              <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.961L3.964 7.293C4.672 5.166 6.656 3.58 9 3.58z"/>
            </svg>
            Continue with Google
          `;

          let msg = err.message || "Google sign-in failed.";
          if (err.code === "auth/popup-closed-by-user") {
            msg = "Sign-in popup was closed before completing.";
          } else if (err.code === "auth/operation-not-allowed") {
            msg = "Google Sign-In is disabled. Please enable 'Google' in Firebase Console -> Authentication -> Sign-in method.";
          } else if (err.code === "auth/unauthorized-domain") {
            msg = "This domain is not authorized. Try accessing via http://localhost:5000 or add this domain in Firebase Console -> Authentication -> Settings -> Authorized Domains.";
          }
          showAuthAlert(msg, "warning");
        }
      });
    });
  }

  window.addEventListener("DOMContentLoaded", () => {
    setupPasswordToggles();
    setupLoginForm();
    setupRegisterForm();
    setupForgotPassword();
    setupGoogleAuth();
  });
})();

