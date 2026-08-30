import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { createReadStream, existsSync, readFileSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const root = new URL('../dist/', import.meta.url).pathname;
const indexHtml = readFileSync(join(root, 'index.html'), 'utf8');
const mime = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.wasm': 'application/wasm',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.css': 'text/css; charset=utf-8',
};

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function changedReleaseShell() {
  const match = indexHtml.match(/<script[^>]*\ssrc=(["'])([^"']+)\1/i);
  const source = match?.[2];
  assert(source, 'Exported index.html must contain a script asset for release detection');
  return indexHtml.replace(source, `${source}.next-release`);
}

let staleRelease = false;
const nextShell = changedReleaseShell();

function listen(server, port) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => resolve(server));
  });
}

function staticServer() {
  return createServer((request, response) => {
    const url = new URL(request.url ?? '/', 'http://localhost');
    const rawPath = url.pathname;

    if (rawPath === '/index.html') {
      const releaseCheck = url.searchParams.has('__parallax_release_check');
      response.writeHead(200, {
        'content-type': 'text/html; charset=utf-8',
        'cache-control': 'no-store',
      });
      response.end(releaseCheck && staleRelease ? nextShell : indexHtml);
      return;
    }

    const relative = rawPath === '/' ? 'index.html' : rawPath.replace(/^\/+/, '');
    const target = normalize(join(root, relative));
    if (!target.startsWith(normalize(root)) || !existsSync(target)) {
      response.writeHead(404, { 'content-type': 'text/plain' });
      response.end('not found');
      return;
    }
    response.writeHead(200, {
      'content-type': mime[extname(target)] ?? 'application/octet-stream',
      'cache-control': 'no-store',
    });
    createReadStream(target).pipe(response);
  });
}

const web = staticServer();
let browser;
try {
  await listen(web, 8773);
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.goto('http://127.0.0.1:8773', { waitUntil: 'domcontentloaded' });

  staleRelease = true;
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));

  const update = page.getByRole('status').filter({ hasText: 'Parallax was updated' });
  await update.waitFor({ timeout: 8000 });
  await update.getByText('Refresh to keep this screen on the current client version.', { exact: true }).waitFor();
  const refresh = update.getByRole('button', { name: 'Refresh Parallax to the current version' });
  const refreshBox = await refresh.boundingBox();
  assert(refreshBox && refreshBox.height >= 43.5 && refreshBox.width >= 44, 'Client update refresh control must remain at least 44pt');

  staleRelease = false;
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
    refresh.click(),
  ]);
  assert(await page.getByRole('status').filter({ hasText: 'Parallax was updated' }).count() === 0, 'Client update banner must clear after refresh');

  console.log(JSON.stringify({
    staleClientDetected: true,
    explicitRefreshAvailable: true,
    mobileTargetMinimum: true,
    refreshLoadsCurrentShell: true,
  }, null, 2));
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => web.close(resolve));
}
