// static/js/sw.js

const CACHE_NAME = 'nextmedia-v1.0.1';  // Updated version
const STATIC_CACHE = 'nextmedia-static-v1.0.1';
const DYNAMIC_CACHE = 'nextmedia-dynamic-v1.0.1';

const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/img/icon-192x192.png',
    '/static/img/icon-512x512.png',
    '/static/img/logo.jpg',
    '/manifest.json',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
];

// Install Service Worker
self.addEventListener('install', function(event) {
    console.log('Service Worker installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(function(cache) {
                console.log('Caching static assets...');
                return cache.addAll(STATIC_ASSETS.map(url => new Request(url, {
                    credentials: 'same-origin'
                })));
            })
            .then(function() {
                console.log('Static assets cached successfully');
                return self.skipWaiting(); // Force activation
            })
            .catch(function(error) {
                console.error('Cache installation failed:', error);
            })
    );
});

// Activate Service Worker
self.addEventListener('activate', function(event) {
    console.log('Service Worker activating...');
    
    event.waitUntil(
        caches.keys()
            .then(function(cacheNames) {
                return Promise.all(
                    cacheNames.map(function(cacheName) {
                        // Delete old caches
                        if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
                            console.log('Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(function() {
                console.log('Service Worker activated');
                return self.clients.claim(); // Take control immediately
            })
    );
});

// Enhanced fetch handler with different strategies
self.addEventListener('fetch', function(event) {
    const requestUrl = new URL(event.request.url);
    
    // Handle different types of requests
    if (isStaticAsset(event.request)) {
        event.respondWith(cacheFirst(event.request));
    } else if (isAPIRequest(event.request)) {
        event.respondWith(networkFirst(event.request));
    } else if (isHTMLRequest(event.request)) {
        event.respondWith(staleWhileRevalidate(event.request));
    } else {
        event.respondWith(fetch(event.request));
    }
});

// Check if request is for static assets
function isStaticAsset(request) {
    return request.url.includes('/static/') || 
           request.url.includes('cdnjs.cloudflare.com') ||
           request.url.includes('fonts.googleapis.com') ||
           request.url.includes('.css') ||
           request.url.includes('.js') ||
           request.url.includes('.png') ||
           request.url.includes('.jpg') ||
           request.url.includes('.jpeg') ||
           request.url.includes('.svg');
}

// Check if request is for API endpoints
function isAPIRequest(request) {
    return request.url.includes('/api/') || 
           request.url.includes('/admin/') ||
           request.url.includes('/download/');
}

// Check if request is for HTML pages
function isHTMLRequest(request) {
    return request.headers.get('Accept') && 
           request.headers.get('Accept').includes('text/html');
}

// Cache first strategy (for static assets)
async function cacheFirst(request) {
    try {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.error('Cache first strategy failed:', error);
        // Return cached version if available
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        throw error;
    }
}

// Network first strategy (for API requests)
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok && request.method === 'GET') {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.log('Network failed, trying cache...');
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline page for navigation requests
        if (request.mode === 'navigate') {
            return createOfflinePage();
        }
        throw error;
    }
}

// Stale while revalidate strategy (for HTML pages)
async function staleWhileRevalidate(request) {
    const cachedResponse = await caches.match(request);
    
    // Start network request in background
    const networkResponsePromise = fetch(request)
        .then(response => {
            if (response.ok) {
                const cache = caches.open(DYNAMIC_CACHE);
                cache.then(c => c.put(request, response.clone()));
            }
            return response;
        })
        .catch(error => {
            console.log('Network request failed:', error);
            return null;
        });

    // Return cached response immediately, or wait for network
    return cachedResponse || networkResponsePromise || createOfflinePage();
}

// Background sync for offline actions
self.addEventListener('sync', function(event) {
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

// Push notification handler
self.addEventListener('push', function(event) {
    let notificationData = {
        title: 'NextMedia',
        body: 'New news available!',
        icon: '/static/img/icon-192x192.png',
        badge: '/static/img/icon-192x192.png',
        data: { url: '/' }
    };

    // Parse push data if available
    if (event.data) {
        try {
            const pushData = event.data.json();
            notificationData = { ...notificationData, ...pushData };
        } catch (e) {
            notificationData.body = event.data.text();
        }
    }

    const options = {
        body: notificationData.body,
        icon: notificationData.icon,
        badge: notificationData.badge,
        vibrate: [200, 100, 200],
        data: notificationData.data,
        actions: [
            {
                action: 'open',
                title: 'Read Now',
                icon: '/static/img/icon-192x192.png'
            },
            {
                action: 'close',
                title: 'Close'
            }
        ],
        requireInteraction: false,
        silent: false
    };

    event.waitUntil(
        self.registration.showNotification(notificationData.title, options)
    );
});

// Notification click handler
self.addEventListener('notificationclick', function(event) {
    event.notification.close();

    if (event.action === 'open' || !event.action) {
        const urlToOpen = event.notification.data?.url || '/';
        
        event.waitUntil(
            clients.matchAll({ type: 'window', includeUncontrolled: true })
                .then(function(clientList) {
                    // Check if NextMedia is already open
                    for (let client of clientList) {
                        if (client.url.includes(self.location.origin) && 'focus' in client) {
                            client.navigate(urlToOpen);
                            return client.focus();
                        }
                    }
                    
                    // Open new window if not already open
                    if (clients.openWindow) {
                        return clients.openWindow(urlToOpen);
                    }
                })
        );
    }
});

// Create enhanced offline page
function createOfflinePage() {
    const offlineHTML = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Offline - NextMedia</title>
            <meta name="theme-color" content="#1a1a2e">
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    color: white;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    text-align: center;
                    padding: 20px;
                }
                
                .offline-container {
                    max-width: 500px;
                    padding: 2rem;
                    animation: fadeIn 0.6s ease-out;
                }
                
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                
                .offline-icon {
                    font-size: 4rem;
                    color: #ff6b35;
                    margin-bottom: 1.5rem;
                    animation: pulse 2s infinite;
                }
                
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.7; }
                }
                
                h1 {
                    font-size: 2.2rem;
                    margin-bottom: 1rem;
                    color: #fff;
                    font-weight: 600;
                }
                
                p {
                    font-size: 1.1rem;
                    margin-bottom: 2rem;
                    opacity: 0.8;
                    line-height: 1.6;
                }
                
                .button-group {
                    display: flex;
                    gap: 1rem;
                    justify-content: center;
                    flex-wrap: wrap;
                }
                
                .retry-btn, .home-btn {
                    background: #ff6b35;
                    color: white;
                    border: none;
                    padding: 1rem 2rem;
                    border-radius: 25px;
                    font-size: 1rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    text-decoration: none;
                    display: inline-flex;
                    align-items: center;
                    gap: 0.5rem;
                }
                
                .home-btn {
                    background: transparent;
                    border: 2px solid #ff6b35;
                }
                
                .retry-btn:hover, .home-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 8px 20px rgba(255, 107, 53, 0.3);
                }
                
                .home-btn:hover {
                    background: #ff6b35;
                }
                
                .brand {
                    margin-top: 2rem;
                    font-size: 1.2rem;
                    font-weight: 600;
                    opacity: 0.6;
                }
                
                .brand span {
                    color: #ff6b35;
                }
            </style>
        </head>
        <body>
            <div class="offline-container">
                <div class="offline-icon">📡</div>
                <h1>You're Offline</h1>
                <p>It looks like you're not connected to the internet. Check your connection and try again, or browse cached content.</p>
                
                <div class="button-group">
                    <button class="retry-btn" onclick="window.location.reload()">
                        🔄 Try Again
                    </button>
                    <a href="/" class="home-btn">
                        🏠 Go Home
                    </a>
                </div>
                
                <div class="brand">
                    Next<span>Media</span>
                </div>
            </div>
            
            <script>
                // Auto-retry when online
                window.addEventListener('online', function() {
                    window.location.reload();
                });
                
                // Show connection status
                if (!navigator.onLine) {
                    console.log('Currently offline');
                }
            </script>
        </body>
        </html>
    `;

    return new Response(offlineHTML, {
        headers: { 
            'Content-Type': 'text/html',
            'Cache-Control': 'no-cache'
        }
    });
}

// Background sync function
async function doBackgroundSync() {
    try {
        // Sync any pending data when back online
        console.log('Performing background sync...');
        
        // You can add specific sync logic here
        // For example, syncing offline form submissions
        
        return Promise.resolve();
    } catch (error) {
        console.error('Background sync failed:', error);
        throw error;
    }
}

// Message handler for cache management
self.addEventListener('message', function(event) {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'CLEANUP_CACHES') {
        event.waitUntil(cleanupOldCaches());
    }
    
    if (event.data && event.data.type === 'GET_VERSION') {
        event.ports[0].postMessage({ version: CACHE_NAME });
    }
});

// Cleanup old caches
async function cleanupOldCaches() {
    const cacheNames = await caches.keys();
    const currentCaches = [STATIC_CACHE, DYNAMIC_CACHE];
    
    return Promise.all(
        cacheNames
            .filter(name => !currentCaches.includes(name))
            .map(name => {
                console.log('Cleaning up old cache:', name);
                return caches.delete(name);
            })
    );
}

// Error handling for fetch events
self.addEventListener('error', function(event) {
    console.error('Service Worker error:', event.error);
});

self.addEventListener('unhandledrejection', function(event) {
    console.error('Service Worker unhandled rejection:', event.reason);
});

// Periodic cache cleanup (called when SW receives cleanup message)
async function performCacheCleanup() {
    try {
        const cache = await caches.open(DYNAMIC_CACHE);
        const requests = await cache.keys();
        
        // Remove old cached responses (older than 7 days)
        const oneWeekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
        
        const deletePromises = requests
            .filter(request => {
                // Simple heuristic: if it's been cached for a while, remove it
                return request.url.includes('timestamp') || 
                       request.url.includes('cache_bust');
            })
            .map(request => cache.delete(request));
            
        await Promise.all(deletePromises);
        console.log('Cache cleanup completed');
    } catch (error) {
        console.error('Cache cleanup failed:', error);
    }
}