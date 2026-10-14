if (!document.getElementById('sharingan-extension-test')) {
  const badge = document.createElement('div');
  badge.id = 'sharingan-extension-test';
  badge.textContent = 'Sharingan extension aktif';
  badge.style.cssText = 'position:fixed;bottom:20px;left:20px;z-index:2147483647;' +
      'background:#bb1832;color:white;padding:14px;border-radius:12px;font:16px sans-serif';
  document.body.appendChild(badge);
}
