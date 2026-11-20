// Service Worker for Flipkart-style push notifications
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

// Helper to display rich OS lock-screen notification
function triggerConsignmentNotification(data) {
  const title = data.title || '🚨 New Consignment Requirement Available!';
  const options = {
    body: data.body || 'Shree Mahalaxmi Marbel and Granite posted a new tender.',
    icon: data.icon || 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png',
    badge: 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png',
    vibrate: [200, 100, 200, 100, 200],
    tag: 'negotiagent-rfq-' + Date.now(),
    renotify: true,
    data: { url: data.url || '/supplier_dashboard.html' },
    actions: [
      { action: 'bid', title: '⚡ Submit Quote Now' },
      { action: 'close', title: 'Dismiss' }
    ]
  };

  return self.registration.showNotification(title, options);
}

// 1. Listen for real-time RFQ alerts posted from supplier_dashboard.html
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'NEW_RFQ_ALERT') {
    event.waitUntil(triggerConsignmentNotification(event.data));
  }
});

// 2. Listen for incoming push payloads from server
self.addEventListener('push', (event) => {
  let data = {
    title: '🚨 New Consignment Requirement Available!',
    body: 'Shree Mahalaxmi Marbel and Granite posted a new tender.',
    icon: '/css/favicon.ico',
    url: '/supplier_dashboard.html'
  };

  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }

  event.waitUntil(triggerConsignmentNotification(data));
});

// 3. Click listener: opens or focuses the supplier bidding terminal when tapped
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'close') return;

  const targetUrl = (event.notification.data && event.notification.data.url)
    ? event.notification.data.url
    : '/supplier_dashboard.html';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if ((client.url.includes('supplier_dashboard.html') || client.url.includes('login.html')) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});