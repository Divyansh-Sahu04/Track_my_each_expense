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

// Auto-fade flash messages after 5 seconds
document.querySelectorAll("[data-flash-message]").forEach(function (el) {
    setTimeout(function () {
        el.classList.add("flash-error--fade-out");
        el.addEventListener("transitionend", function () {
            el.remove();
        });
    }, 5000);
});

// Delete expense confirmation modal
var deleteModal = document.querySelector("[data-delete-modal]");
var deleteConfirmBtn = document.querySelector("[data-delete-confirm]");
var deleteCancelBtn = document.querySelector("[data-delete-cancel]");
var pendingDeleteForm = null;

function openDeleteModal(form) {
    pendingDeleteForm = form;
    if (deleteModal) deleteModal.hidden = false;
}

function closeDeleteModal() {
    pendingDeleteForm = null;
    if (deleteModal) deleteModal.hidden = true;
}

document.querySelectorAll("[data-delete-trigger]").forEach(function (trigger) {
    trigger.addEventListener("click", function (event) {
        var form = trigger.closest("[data-delete-form]");
        if (!form) return;
        event.preventDefault();
        openDeleteModal(form);
    });
});

if (deleteConfirmBtn) {
    deleteConfirmBtn.addEventListener("click", function () {
        if (pendingDeleteForm) pendingDeleteForm.submit();
        closeDeleteModal();
    });
}

if (deleteCancelBtn) {
    deleteCancelBtn.addEventListener("click", closeDeleteModal);
}

if (deleteModal) {
    deleteModal.addEventListener("click", function (event) {
        if (event.target === deleteModal) closeDeleteModal();
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !deleteModal.hidden) closeDeleteModal();
    });
}
