/**
 * KEIBA AI PRO - サービスワーカー
 * Google Apps Script (GAS) 通信完全バイパス対応版
 */

const CACHE_NAME = 'keiba-ai-v2.1';
const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './css/style.css',
  './js/app.js'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn('キャッシュ初期化スキップ:', err);
      });
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = event.request.url;

  // Google Apps Script または Google内部サーバーへの通信は絶対にキャッシュせず、ネットワークへ直通させる
  if (
    url.includes('script.google.com') ||
    url.includes('script.googleusercontent.com') ||
    url.includes('google.com/macros')
  ) {
    // 割り込まずにそのままネットワーク通信を実行
    return;
  }

  // 静的ファイル（HTML, CSS, アイコンなど）のキャッシュ制御
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request).catch(() => {
        return caches.match('./index.html');
      });
    })
  );
});