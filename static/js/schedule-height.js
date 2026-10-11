/* Keep the shared and personal calendars within the available viewport. */
(() => {
  const start = () => {
    const schedule = document.getElementById('schedule-view');
    if (!schedule) return;
    const fit = () => {
      const top = schedule.getBoundingClientRect().top + window.scrollY;
      const height = Math.max(260, window.innerHeight - top - 16);
      schedule.style.setProperty('--schedule-available-height', `${height}px`);
    };
    fit();
    window.addEventListener('resize', fit, { passive: true });
    const header = schedule.querySelector('.cc-header');
    if (header && window.ResizeObserver) new ResizeObserver(fit).observe(header);
    if (document.fonts) document.fonts.ready.then(fit);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
