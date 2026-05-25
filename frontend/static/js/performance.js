// Performance helpers: add lazy loading attributes and handle preloads
document.addEventListener('DOMContentLoaded', function () {
  try {
    // set lazy attributes on images unless explicitly opted out
    document.querySelectorAll('img').forEach(img => {
      if (img.dataset.skipLazy === "true") return;
      // keep eager for logos
      if (img.classList.contains('logo-img') || img.classList.contains('site-logo') || img.closest('nav')) {
        img.setAttribute('loading', 'eager');
        img.setAttribute('decoding', 'async');
        img.setAttribute('fetchpriority', 'high');
      } else {
        img.setAttribute('loading', 'lazy');
        img.setAttribute('decoding', 'async');
        img.setAttribute('fetchpriority', 'low');
      }
    });

    // Add preload links for images that asked for it via data-preload attribute
    document.querySelectorAll('img[data-preload="true"]').forEach(img => {
      const href = img.currentSrc || img.getAttribute('src');
      if (!href) return;
      const link = document.createElement('link');
      link.rel = 'preload';
      link.as = 'image';
      link.href = href;
      document.head.appendChild(link);
    });
  } catch (e) {
    // fail gracefully
    console.warn('performance.js error', e);
  }
});
