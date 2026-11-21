// Navigation interactions are local mockup behavior; no account/session requests.
(() => {
  const preview = document.getElementById('preview');
  const sidebar = document.getElementById('app-sidebar');
  const toggle = document.getElementById('drawer-toggle');
  const scrim = document.getElementById('drawer-scrim');
  const content = preview.querySelector('.workspace');
  let returnFocus;
  function closeDrawer() {
    preview.classList.remove('drawer-open');
    document.body.classList.remove('shell-lock');
    toggle.setAttribute('aria-expanded', 'false');
    scrim.hidden = true;
    content.inert = false;
    document.querySelector('.review').inert = false;
    sidebar.removeAttribute('role');
    sidebar.removeAttribute('aria-modal');
    if (returnFocus?.isConnected) returnFocus.focus();
    returnFocus = null;
  }
  function openDrawer() {
    returnFocus = document.activeElement;
    preview.classList.add('drawer-open');
    document.body.classList.add('shell-lock');
    toggle.setAttribute('aria-expanded', 'true');
    scrim.hidden = false;
    content.inert = true;
    document.querySelector('.review').inert = true;
    sidebar.setAttribute('role', 'dialog');
    sidebar.setAttribute('aria-modal', 'true');
    document.getElementById('drawer-close').focus();
  }
  toggle.onclick = openDrawer;
  document.getElementById('drawer-close').onclick = closeDrawer;
  scrim.onclick = closeDrawer;
  document.addEventListener('keydown', event => {
    if (!preview.classList.contains('drawer-open')) return;
    if (event.key === 'Escape') { event.preventDefault(); closeDrawer(); }
    if (event.key === 'Tab') {
      const focusables = [...sidebar.querySelectorAll('a[href],button:not(:disabled),summary')].filter(e => e.getClientRects().length);
      const first = focusables[0], last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  const themeButton = document.getElementById('shell-theme');
  function syncTheme() {
    themeButton.setAttribute('aria-pressed', String(document.getElementById('theme').value === 'night'));
  }
  themeButton.onclick = () => {
    const theme = document.getElementById('theme');
    theme.value = theme.value === 'day' ? 'night' : 'day';
    theme.dispatchEvent(new Event('change'));
  };
  document.getElementById('theme').addEventListener('change', syncTheme);
  document.getElementById('shell-logout').onclick = () => {
    const notice = document.getElementById('shell-notice');
    notice.hidden = false;
    notice.textContent = 'Đây là mockup; thao tác đăng xuất chưa kết nối tài khoản.';
  };
  window.addEventListener('resize', () => {
    if (preview.classList.contains('drawer-open')) closeDrawer();
  });
  syncTheme();
})();
