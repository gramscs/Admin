document.addEventListener('DOMContentLoaded', function() {
    const statusElement = document.querySelector('.track-status');
    const tooltip = document.getElementById('deliveryTracker');
    const backdrop = document.getElementById('trackerBackdrop');

    if (!tooltip || !backdrop) {
        return;
    }

    const closeBtn = tooltip.querySelector('.tracker-close');
    const tooltipOffset = 16;

    function positionTooltip() {
        if (!statusElement) {
            return;
        }

        const statusRect = statusElement.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        let left = statusRect.left;
        let top = statusRect.bottom + tooltipOffset;

        if (left + tooltipRect.width > viewportWidth - 16) {
            left = viewportWidth - tooltipRect.width - 16;
        }

        if (left < 16) {
            left = 16;
        }

        if (top + tooltipRect.height > viewportHeight - 16) {
            top = statusRect.top - tooltipRect.height - tooltipOffset;
        }

        if (top < 16) {
            top = 16;
        }

        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
    }

    if (statusElement) {
        statusElement.addEventListener('click', function(e) {
            e.stopPropagation();
            tooltip.classList.add('active');
            backdrop.classList.add('active');
            requestAnimationFrame(positionTooltip);
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            tooltip.classList.remove('active');
            backdrop.classList.remove('active');
        });
    }

    document.addEventListener('click', function(e) {
        if (
            tooltip.classList.contains('active') &&
            !e.target.closest('.track-status-wrapper') &&
            !e.target.closest('#deliveryTracker')
        ) {
            tooltip.classList.remove('active');
            backdrop.classList.remove('active');
        }
    });

    backdrop.addEventListener('click', function() {
        tooltip.classList.remove('active');
        backdrop.classList.remove('active');
    });

    window.addEventListener('resize', function() {
        if (tooltip.classList.contains('active')) {
            positionTooltip();
        }
    });

    window.addEventListener('scroll', function() {
        if (tooltip.classList.contains('active')) {
            positionTooltip();
        }
    }, true);
});
