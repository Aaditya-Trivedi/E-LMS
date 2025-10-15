// ========================================
// Bootstrap Form Validation
// ========================================

function validateForm() {
  const username = document.getElementById("modalSignupUsername1");
  const mobile   = document.getElementById("modalSignupMobile");
  const email    = document.getElementById("modalSignupEmail1");
  const password = document.getElementById("modalSignupPassword3");

  const nameRegex   = /^[A-Za-z\s]+$/;
  const mobileRegex = /^[0-9]{10}$/;
  const emailRegex  = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  // Clear old state
  [username, mobile, email, password].forEach(el => {
    el.classList.remove("is-invalid", "is-valid");
  });

  let isValid = true;

  // Username
  if (!username.value.trim() || !nameRegex.test(username.value.trim())) {
    username.classList.add("is-invalid");
    isValid = false;
  } else username.classList.add("is-valid");

  // Mobile
  if (!mobile.value.trim() || !mobileRegex.test(mobile.value.trim())) {
    mobile.classList.add("is-invalid");
    isValid = false;
  } else mobile.classList.add("is-valid");

  // Email
  if (!email.value.trim() || !emailRegex.test(email.value.trim())) {
    email.classList.add("is-invalid");
    isValid = false;
  } else email.classList.add("is-valid");

  // Password
  if (!password.value.trim() || password.value.length < 6) {
    password.classList.add("is-invalid");
    isValid = false;
  } else password.classList.add("is-valid");

  // Stop submit if invalid
  if (!isValid) {
    // Focus first invalid input
    const firstInvalid = document.querySelector(".is-invalid");
    if (firstInvalid) firstInvalid.focus();
    return false;
  }

  // Allow submission
  return true;
}

// Optional: add Bootstrap native validation style for all forms with .needs-validation
(function () {
  "use strict";
  const forms = document.querySelectorAll(".needs-validation");
  Array.prototype.slice.call(forms).forEach(function (form) {
    form.addEventListener(
      "submit",
      function (event) {
        if (!form.checkValidity()) {
          event.preventDefault();
          event.stopPropagation();
        }
        form.classList.add("was-validated");
      },
      false
    );
  });
})();
