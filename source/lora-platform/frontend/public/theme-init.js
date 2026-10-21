// Apply the saved theme before React and the stylesheet render to prevent a flash.
(function () {
  var preference = 'system';
  try {
    var saved = localStorage.getItem('lora-theme');
    if (saved === 'light' || saved === 'dark' || saved === 'system') preference = saved;
  } catch (_) {}
  var theme = preference === 'system'
    ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    : preference;
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
  document.querySelector('meta[name="theme-color"]').content = theme === 'dark' ? '#171719' : '#fcfcfd';
})();
