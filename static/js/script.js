// Confirmation dialog for deleting records
function confirmDelete() {
    return confirm("Are you sure you want to delete this assignment permanently?");
}

// Auto-hide alert messages after 4 seconds
document.addEventListener("DOMContentLoaded", function () {
    const alerts = document.querySelectorAll(".alert-box");
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.opacity = "0";
            setTimeout(() => alert.remove(), 300);
        }, 4000);
    });
});