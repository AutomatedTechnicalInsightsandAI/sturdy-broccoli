/* Sturdy Broccoli — main.js */

document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss alerts after 5 seconds
    document.querySelectorAll('.alert.alert-dismissible').forEach(function (alert) {
        setTimeout(function () {
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // Confirm before dangerous form submissions (data-confirm attribute)
    document.querySelectorAll('form[data-confirm]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!confirm(form.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    // Chart.js: initialize any canvas elements with data-chart attribute
    document.querySelectorAll('canvas[data-chart]').forEach(function (canvas) {
        try {
            var cfg = JSON.parse(canvas.dataset.chart);
            new Chart(canvas, cfg);
        } catch (err) {
            console.warn('Chart init failed:', err);
        }
    });
});
