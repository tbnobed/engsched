(() => {
  function initialize() {
    document.querySelectorAll('[data-ticket-group]').forEach(group => {
      if (group.dataset.initialized) return;
      group.dataset.initialized = 'true';
      const form = group.closest('form');
      if (!form) return;
      const assignee = form.querySelector(`[name="${group.dataset.assigneeName || 'assigned_to'}"]`);
      if (!assignee) return;
      const notice = group.parentElement.querySelector('[data-group-assignee-notice]');
      function update(changed) {
        const selected = group.selectedOptions[0];
        const filter = group.dataset.filterMembers === 'true' && !!selected?.dataset.members;
        const members = new Set(JSON.parse(selected?.dataset.members || '[]').map(String));
        Array.from(assignee.options).forEach(option => {
          const allowed = !filter || !option.value || ['0', '-1'].includes(option.value) || members.has(option.value);
          // Preserve an existing assignment on initial load, but never offer it anew.
          option.hidden = !allowed && !(option.selected && !changed);
          option.disabled = !allowed && !(option.selected && !changed);
        });
        if (changed && filter && assignee.value && !['0', '-1'].includes(assignee.value) && !members.has(assignee.value)) {
          assignee.value = Array.from(assignee.options).some(o => o.value === '0') ? '0' : '';
          if (notice) {
            notice.textContent = 'The previous assignee is not a member of this group and has been cleared.';
            notice.hidden = false;
          }
        } else if (changed && notice) {
          notice.hidden = true;
        }
      }
      group.addEventListener('change', () => update(true));
      update(false);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
  else initialize();
})();
