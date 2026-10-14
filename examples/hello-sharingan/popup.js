chrome.storage.local.get('installedAt', ({installedAt}) => {
  document.getElementById('state').textContent = installedAt
      ? 'Service worker berjalan: ' + installedAt : 'Belum ada status service worker.';
});
