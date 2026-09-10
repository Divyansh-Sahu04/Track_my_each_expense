// main.js — students will add JavaScript here as features are built

document.querySelectorAll("[data-photo-trigger]").forEach(function (trigger) {
    var form = trigger.closest("form");
    var fileInput = form ? form.querySelector("[data-photo-input]") : null;
    if (!fileInput) return;

    trigger.addEventListener("click", function () {
        fileInput.click();
    });

    fileInput.addEventListener("change", function () {
        if (fileInput.files.length > 0) {
            form.submit();
        }
    });
});

// Appearance (dark mode) toggle
function resolveSystemTheme() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
}

var themeToggleButtons = document.querySelectorAll("[data-theme-option]");
var themeToggleForm = document.getElementById("theme-toggle-form");
var themeToggleInput = document.getElementById("theme-toggle-input");

function markActiveThemeButton(preference) {
    themeToggleButtons.forEach(function (btn) {
        var isActive = btn.dataset.themeOption === preference;
        btn.classList.toggle("theme-toggle-btn--active", isActive);
        btn.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
}

function applyTheme(preference) {
    var effective = preference === "system" ? resolveSystemTheme() : preference;
    document.documentElement.setAttribute("data-theme", effective);
    document.documentElement.setAttribute("data-theme-preference", preference);
    markActiveThemeButton(preference);
}

markActiveThemeButton(document.documentElement.getAttribute("data-theme-preference") || "system");

themeToggleButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
        var preference = btn.dataset.themeOption;
        applyTheme(preference);

        if (themeToggleForm && themeToggleInput) {
            themeToggleInput.value = preference;
            themeToggleForm.submit();
        }
    });
});

if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
        if (document.documentElement.getAttribute("data-theme-preference") === "system") {
            applyTheme("system");
        }
    });
}
