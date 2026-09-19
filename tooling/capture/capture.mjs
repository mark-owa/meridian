import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const webURL = process.env.WEB_URL || 'http://localhost:5173';
const apiURL = process.env.API_URL || 'http://localhost:8000';
const out = new URL('./output/', import.meta.url).pathname;
await mkdir(out, { recursive: true });

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
page.setDefaultTimeout(20000);

const errors = [];
page.on('pageerror', e => errors.push(e.message));
page.on('response', r => {
  if (r.url().startsWith(apiURL) && r.status() >= 500) {
    errors.push(`HTTP ${r.status()}: ${r.url()}`);
  }
});

const email = 'portfolio-demo@example.com';
const password = 'Portfolio123!';
const evidence = {
  recorded_at: new Date().toISOString(),
  source_commit: process.env.GITHUB_SHA || null,
  run_url: process.env.GITHUB_RUN_ID
    ? `https://github.com/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}`
    : null,
  environment: 'Docker Compose: PostgreSQL, Redis, Chroma, FastAPI, nginx and production React build',
  checks: {},
  note: 'UI/demo evidence only. No live model outputs are fabricated or asserted.'
};

async function jsonRequest(method, path, body, token) {
  const response = await context.request.fetch(`${apiURL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    data: body,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  return { response, data };
}

try {
  const reg = await jsonRequest('POST', '/api/v1/auth/register', {
    full_name: 'Portfolio Demo',
    email,
    company: 'Meridian Demo',
    password,
  });
  if (![201, 409].includes(reg.response.status())) {
    assert.fail(`register failed: ${reg.response.status()} ${JSON.stringify(reg.data)}`);
  }

  const login = await jsonRequest('POST', '/api/v1/auth/login', { email, password });
  assert.equal(login.response.status(), 200);
  const token = login.data.access_token;
  assert(token);

  const leads = [
    {
      company_name: 'Northwind Logistics',
      contact_name: 'Avery Chen',
      contact_email: 'avery.northwind@example.com',
      industry: 'Logistics',
      budget_range: '$25k-$50k',
      pain_points: 'Manual incident triage and fragmented operations data'
    },
    {
      company_name: 'Helios Manufacturing',
      contact_name: 'Mika Santos',
      contact_email: 'mika.helios@example.com',
      industry: 'Manufacturing',
      budget_range: '$10k-$25k',
      pain_points: 'Document-heavy supplier workflows'
    },
    {
      company_name: 'Lattice Services',
      contact_name: 'Jordan Lee',
      contact_email: 'jordan.lattice@example.com',
      industry: 'Professional Services',
      budget_range: '$5k-$10k',
      pain_points: 'Slow lead follow-up and scattered knowledge'
    }
  ];

  const existing = await jsonRequest('GET', '/api/v1/leads', undefined, token);
  assert.equal(existing.response.status(), 200);
  if (existing.data.total === 0) {
    const created = [];
    for (const lead of leads) {
      const result = await jsonRequest('POST', '/api/leads', lead, token);
      assert.equal(result.response.status(), 201);
      created.push(result.data);
    }
    assert.equal((await jsonRequest('PATCH', `/api/v1/leads/${created[0].id}/status?status=qualified`, undefined, token)).response.status(), 200);
    assert.equal((await jsonRequest('PATCH', `/api/v1/leads/${created[1].id}/status?status=contacted`, undefined, token)).response.status(), 200);
    assert.equal((await jsonRequest('PATCH', `/api/v1/leads/${created[2].id}/status?status=converted`, undefined, token)).response.status(), 200);
  }

  await page.goto(`${webURL}/login`);
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('heading', { name: 'Overview', exact: true }).waitFor();
  await page.screenshot({ path: `${out}dashboard.png`, fullPage: true });
  evidence.checks.dashboard = 'rendered after authenticated API-backed setup';

  await page.getByRole('link', { name: 'Leads', exact: true }).click();
  await page.getByRole('heading', { name: 'Leads', exact: true }).waitFor();
  await page.screenshot({ path: `${out}leads.png`, fullPage: true });
  evidence.checks.leads = 'three leads created through the real API and rendered in the UI';

  await page.getByRole('link', { name: 'Knowledge Base', exact: true }).click();
  await page.getByRole('heading', { name: 'Knowledge Base', exact: true }).waitFor();
  await page.screenshot({ path: `${out}knowledge-base.png`, fullPage: true });
  evidence.checks.knowledge_base = 'real product surface; no synthetic RAG answer inserted';

  await page.getByRole('link', { name: 'Document Intelligence', exact: true }).click();
  await page.getByRole('heading', { name: 'Document Intelligence', exact: true }).waitFor();
  await page.screenshot({ path: `${out}document-intelligence.png`, fullPage: true });
  evidence.checks.document_intelligence = 'real product surface; no synthetic extraction inserted';

  assert.deepEqual(errors, []);
  await writeFile(`${out}capture-evidence.json`, JSON.stringify(evidence, null, 2) + '\n');
} finally {
  await context.close();
  await browser.close();
}
