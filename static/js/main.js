/* Sturdy Broccoli — main.js */

// ── Page-load fade-in ─────────────────────────────────────────────────────
document.body.classList.add('is-loading');

document.addEventListener('DOMContentLoaded', function () {
    // Remove is-loading after a short delay so content fades in smoothly
    setTimeout(function () {
        document.body.classList.remove('is-loading');
    }, 300);

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

    // ── Animated number counters ──────────────────────────────────────────
    // When a .kpi-value or .stat-number scrolls into view, count up from 0
    // to the target number with an easing animation.
    var counterObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (!entry.isIntersecting) { return; }
            counterObserver.unobserve(entry.target);
            var el = entry.target;
            var rawText = el.textContent.trim();
            var numMatch = rawText.match(/[\d,.]+/);
            if (!numMatch) { return; }
            var numStr = numMatch[0].replace(/,/g, '');
            var target = parseFloat(numStr);
            if (isNaN(target)) { return; }
            var suffix = rawText.slice(numMatch.index + numMatch[0].length);
            var prefix = rawText.slice(0, numMatch.index);
            var duration = 1200;
            var startTime = null;
            function easeOutQuad(t) { return t * (2 - t); }
            function step(timestamp) {
                if (!startTime) { startTime = timestamp; }
                var progress = Math.min((timestamp - startTime) / duration, 1);
                var current = Math.floor(easeOutQuad(progress) * target);
                el.textContent = prefix + current.toLocaleString() + suffix;
                if (progress < 1) {
                    requestAnimationFrame(step);
                } else {
                    el.textContent = prefix + target.toLocaleString() + suffix;
                }
            }
            requestAnimationFrame(step);
        });
    }, { threshold: 0.2 });

    document.querySelectorAll('.kpi-value, .stat-number').forEach(function (el) {
        counterObserver.observe(el);
    });

    // ── Sidebar active-link pulse animation ───────────────────────────────
    // The CSS @keyframes activePulse is defined in style.css; the class
    // .sidebar .nav-link.active already picks it up automatically on load.
    // Nothing extra needed in JS — the CSS rule handles it.

    // ── Table row click-to-highlight ─────────────────────────────────────
    document.querySelectorAll('.table-interactive tbody tr').forEach(function (row) {
        row.addEventListener('click', function () {
            row.classList.toggle('row-selected');
        });
        row.style.cursor = 'pointer';
    });

    // ── Copy-to-clipboard button ──────────────────────────────────────────
    document.querySelectorAll('pre.copyable, code.copyable').forEach(function (block) {
        var wrapper = document.createElement('div');
        wrapper.className = 'copy-wrapper';
        block.parentNode.insertBefore(wrapper, block);
        wrapper.appendChild(block);

        var btn = document.createElement('button');
        btn.className = 'copy-btn';
        btn.textContent = 'Copy';
        wrapper.appendChild(btn);

        btn.addEventListener('click', function () {
            var text = block.textContent;
            navigator.clipboard.writeText(text).then(function () {
                btn.textContent = 'Copied ✓';
                setTimeout(function () { btn.textContent = 'Copy'; }, 2000);
            }).catch(function () {
                btn.textContent = 'Copy';
            });
        });
    });

    // ── Smooth-scroll for anchor links ────────────────────────────────────
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            var targetId = anchor.getAttribute('href').slice(1);
            if (!targetId) { return; }
            var target = document.getElementById(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // ── Form submit loading state ─────────────────────────────────────────
    var spinnerSVG = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="animation:spin .75s linear infinite;margin-right:.4rem"><circle cx="12" cy="12" r="10" stroke-opacity=".25"/><path d="M12 2a10 10 0 0 1 10 10" /></svg>';
    // Inject keyframe for spinner if not already present
    if (!document.getElementById('sb-spinner-style')) {
        var spinStyle = document.createElement('style');
        spinStyle.id = 'sb-spinner-style';
        spinStyle.textContent = '@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}';
        document.head.appendChild(spinStyle);
    }
    document.querySelectorAll('form:not([data-confirm])').forEach(function (form) {
        form.addEventListener('submit', function () {
            var btn = form.querySelector('[type="submit"]');
            if (btn && !btn.disabled) {
                btn.disabled = true;
                btn.innerHTML = spinnerSVG + 'Processing…';
            }
        });
    });

    // ── Bootstrap 5 tooltip initialisation ───────────────────────────────
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
        new bootstrap.Tooltip(el);
    });
});
