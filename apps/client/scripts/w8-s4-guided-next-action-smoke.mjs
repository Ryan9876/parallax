import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { createReadStream, existsSync, mkdirSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const root = new URL('../dist/', import.meta.url).pathname;
const evidenceDir = new URL('../visual-evidence/', import.meta.url).pathname;
mkdirSync(evidenceDir, { recursive: true });
const mime = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json',
  '.wasm': 'application/wasm',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

function assert(condition, message) { if (!condition) throw new Error(message); }
function listen(server, port) { return new Promise((resolve, reject) => { server.once('error', reject); server.listen(port, '127.0.0.1', () => resolve(server)); }); }

function staticServer() {
  return createServer((request, response) => {
    const rawPath = new URL(request.url ?? '/', 'http://localhost').pathname;
    const relative = rawPath === '/' ? 'index.html' : rawPath.replace(/^\/+/, '');
    const target = normalize(join(root, relative));
    if (!target.startsWith(normalize(root)) || !existsSync(target)) {
      response.writeHead(404, { 'content-type': 'text/plain' });
      response.end('not found');
      return;
    }
    response.writeHead(200, { 'content-type': mime[extname(target)] ?? 'application/octet-stream', 'cache-control': 'no-store' });
    createReadStream(target).pipe(response);
  });
}

const conversation = {
  id: '47474747-4747-4747-8747-474747474747',
  title: 'Guided next action',
  mode: 'code',
  status: 'ACTIVE',
  spec_id: 'P2-V0.22.0',
  project_id: '58585858-5858-4858-8858-585858585858',
  project_binding_status: 'PROJECT_BOUND',
  created_at: '2026-08-29T01:00:00Z',
  updated_at: '2026-08-29T01:00:00Z',
  messages: [
    { id: 'guidance-user', role: 'user', content: 'Add a clear project overview page.', status: 'complete', created_at: '2026-08-29T01:00:00Z' },
    { id: 'guidance-assistant', role: 'assistant', content: 'Your request is captured. The next step is to turn it into a build plan.', status: 'complete', created_at: '2026-08-29T01:00:05Z' },
  ],
};

const project = {
  id: conversation.project_id,
  slug: 'guided-next-action',
  name: 'Guided Next Action Project',
  description: null,
  repository_ref: 'github:owner/guided-next-action',
  workspace_ref: `project:${conversation.project_id}`,
  status: 'active',
  created_at: '2026-08-29T01:00:00Z',
  updated_at: '2026-08-29T01:00:00Z',
};

let specification = null;
function draftSpecification() {
  specification = {
    id: '69696969-6969-4969-8969-696969696969',
    conversation_id: conversation.id,
    revision: 1,
    status: 'DRAFT',
    title: 'Guided next action plan',
    objective: 'Add a clear project overview page.',
    constraints: ['Preserve existing application behavior.'],
    acceptance_criteria: ['The project overview is understandable and accessible.'],
    risks: [],
    open_questions: [],
    confidence: 0.95,
    program_version: 'w8-s4-browser-acceptance',
    model_id: 'technical-provider-name-must-not-render',
    created_at: '2026-08-29T01:00:10Z',
    updated_at: '2026-08-29T01:00:10Z',
    approved_at: null,
  };
  return specification;
}

function apiServer() {
  function cors(response, origin) {
    response.setHeader('access-control-allow-origin', origin ?? '*');
    response.setHeader('access-control-allow-headers', 'Content-Type,Accept,Authorization');
    response.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS');
  }
  function json(response, status, body, origin) {
    cors(response, origin);
    const encoded = Buffer.from(JSON.stringify(body));
    response.writeHead(status, { 'content-type': 'application/json', 'content-length': encoded.length });
    response.end(encoded);
  }
  return createServer((request, response) => {
    const origin = request.headers.origin;
    if (request.method === 'OPTIONS') { cors(response, origin); response.writeHead(204); response.end(); return; }
    const pathname = new URL(request.url ?? '/', 'http://localhost').pathname;
    if (pathname === '/v1/session' && request.method === 'GET') return json(response, 200, { authenticated: true }, origin);
    if (pathname === '/v1/projects' && request.method === 'GET') return json(response, 200, [project], origin);
    if (pathname === '/v1/conversations' && request.method === 'GET') return json(response, 200, [conversation], origin);
    if (pathname === `/v1/conversations/${conversation.id}` && request.method === 'GET') return json(response, 200, conversation, origin);
    if (pathname === `/v1/conversations/${conversation.id}/work-specifications/latest` && request.method === 'GET') return json(response, 200, specification, origin);
    if (pathname === `/v1/conversations/${conversation.id}/work-specifications/approved` && request.method === 'GET') return json(response, 200, null, origin);
    if (pathname === `/v1/conversations/${conversation.id}/work-specifications/draft` && request.method === 'POST') return json(response, 200, draftSpecification(), origin);
    if (pathname === `/v1/engineering-runs/conversation/${conversation.id}/latest` && request.method === 'GET') return json(response, 200, null, origin);
    return json(response, 404, { detail: 'not found' }, origin);
  });
}

async function pageErrors(page) {
  const errors = [];
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console: ${message.text()}`); });
  return errors;
}

const site = staticServer();
const api = apiServer();
let browser;
try {
  await Promise.all([listen(site, 8774), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });
  const desktop = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const desktopErrors = await pageErrors(desktop);
  const mobileErrors = await pageErrors(mobile);

  await Promise.all([
    desktop.goto('http://127.0.0.1:8774', { waitUntil: 'networkidle' }),
    mobile.goto('http://127.0.0.1:8774', { waitUntil: 'networkidle' }),
  ]);

  const desktopCard = desktop.getByTestId('guided-workflow-card');
  const mobileCard = mobile.getByTestId('mobile-context-card');
  await Promise.all([desktopCard.waitFor({ timeout: 10000 }), mobileCard.waitFor({ timeout: 10000 })]);
  await Promise.all([
    desktopCard.getByText('Create your build plan', { exact: true }).waitFor(),
    mobileCard.getByText('Create your build plan', { exact: true }).waitFor(),
  ]);

  const desktopText = await desktopCard.innerText();
  const mobileText = await mobileCard.innerText();
  assert(desktopText.includes('NEXT STEP') && mobileText.includes('NEXT STEP'), 'W8-S4: desktop/mobile did not share next-step category');
  assert(desktopText.includes('Create your build plan') && mobileText.includes('Create your build plan'), 'W8-S4: same canonical fixture did not produce equivalent guidance title');
  for (const forbidden of [conversation.id, project.id, 'P2-V0.22.0', 'technical-provider-name-must-not-render', 'PLAN', 'IMPLEMENT', 'VERIFY']) {
    assert(!desktopText.includes(forbidden), `W8-S4 desktop guidance leaked technical value: ${forbidden}`);
    assert(!mobileText.includes(forbidden), `W8-S4 mobile guidance leaked technical value: ${forbidden}`);
  }

  const desktopButton = desktopCard.getByRole('button', { name: 'Create build plan' });
  const mobileButton = mobileCard.getByRole('button', { name: 'Create build plan' });
  const [desktopButtonBox, mobileButtonBox, desktopCardBox, mobileCardBox] = await Promise.all([
    desktopButton.boundingBox(),
    mobileButton.boundingBox(),
    desktopCard.boundingBox(),
    mobileCard.boundingBox(),
  ]);
  assert(desktopButtonBox && desktopButtonBox.height >= 44, `W8-S4 desktop CTA below 44px (${desktopButtonBox?.height})`);
  assert(mobileButtonBox && mobileButtonBox.height >= 44, `W8-S4 mobile CTA below 44px (${mobileButtonBox?.height})`);
  assert(desktopCardBox && desktopCardBox.x >= 0 && desktopCardBox.x + desktopCardBox.width <= 1441, 'W8-S4 desktop guidance overflows viewport');
  assert(mobileCardBox && mobileCardBox.x >= 0 && mobileCardBox.x + mobileCardBox.width <= 391, 'W8-S4 mobile guidance overflows viewport');

  await desktop.screenshot({ path: `${evidenceDir}/w8-s4-desktop-create-plan.png` });
  await mobile.screenshot({ path: `${evidenceDir}/w8-s4-mobile-create-plan.png` });

  await Promise.all([desktopButton.click(), mobileButton.click()]);
  await Promise.all([
    desktopCard.getByText('Review your build plan', { exact: true }).waitFor({ timeout: 5000 }),
    mobileCard.getByText('Review your build plan', { exact: true }).waitFor({ timeout: 5000 }),
  ]);
  const desktopReviewText = await desktopCard.innerText();
  const mobileReviewText = await mobileCard.innerText();
  assert(desktopReviewText.includes('Review your build plan'), 'W8-S4 desktop did not advance presentation after the existing draft callback');
  assert(mobileReviewText.includes('Review your build plan'), 'W8-S4 mobile did not advance presentation after the existing draft callback');

  const planSurface = desktop.getByLabel('Build plan', { exact: true });
  const planBox = await planSurface.boundingBox();
  const finalDesktopCardBox = await desktopCard.boundingBox();
  assert(finalDesktopCardBox && planBox && finalDesktopCardBox.y < planBox.y, 'W8-S4 desktop primary guidance is not before the detailed Build plan surface');

  await desktop.screenshot({ path: `${evidenceDir}/w8-s4-desktop-review-plan.png` });
  await mobile.screenshot({ path: `${evidenceDir}/w8-s4-mobile-review-plan.png` });

  assert(desktopErrors.length === 0, `W8-S4 desktop browser errors: ${desktopErrors.join(' | ')}`);
  assert(mobileErrors.length === 0, `W8-S4 mobile browser errors: ${mobileErrors.join(' | ')}`);

  console.log(JSON.stringify({
    desktop: { createPlanCtaHeight: desktopButtonBox.height, guidanceBeforePlan: true },
    mobile: { createPlanCtaHeight: mobileButtonBox.height },
    parity: { createPlan: true, reviewPlan: true },
    technicalValuesHidden: true,
    browserErrors: 0,
  }, null, 2));
} finally {
  await browser?.close();
  site.close();
  api.close();
}
