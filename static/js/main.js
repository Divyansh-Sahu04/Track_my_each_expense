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
