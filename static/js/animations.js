// Shared IntersectionObserver-based reveal utility
(function(){
  function onReady(fn){
    if(document.readyState !== 'loading') return fn();
    document.addEventListener('DOMContentLoaded', fn);
  }

  onReady(function(){
    const revealEls = document.querySelectorAll('.reveal');
    if(!revealEls.length) return;

    const io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if(entry.isIntersecting){
          entry.target.classList.add('in-view');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.2, rootMargin: '0px 0px -10% 0px' });

    revealEls.forEach(el => {
      // Respect existing inline transition delays or utility classes
      io.observe(el);
    });
  });
})();
