const assert = require('node:assert/strict');
const { RunObservabilityClient } = require('../.tmp-observability/lib/runObservability.js');

function event(sequence, overrides = {}) {
  return {
    id: `00000000-0000-4000-8000-${String(sequence).padStart(12, '0')}`,
    sequence,
    run_id: '11111111-1111-4111-8111-111111111111',
    project_id: '22222222-2222-4222-8222-222222222222',
    event_key: `event-${sequence}`,
    event_type: 'STAGE_RESULT',
    stage: sequence < 3 ? 'BUILD' : 'TEST',
    outcome: 'SUCCEEDED',
    subsystem: 'EXECUTION',
    attempt_id: null,
    worker_execution_id: null,
    source_lineage_ref: null,
    parent_source_lineage_ref: null,
    operation_ref: null,
    artifact_ref: null,
    evidence_ref: null,
    failure_code: null,
    summary: `event ${sequence}`,
    metadata: {},
    occurred_at: '2026-08-24T12:00:00Z',
    created_at: '2026-08-24T12:00:00Z',
    ...overrides,
  };
}

function sseResponse(events) {
  const body = events.map((item) => `id: ${item.sequence}\nevent: run-event\ndata: ${JSON.stringify(item)}\n\n`).join('');
  const stream = new ReadableStream({ start(controller) { controller.enqueue(new TextEncoder().encode(body)); controller.close(); } });
  return new Response(stream, { status: 200, headers: { 'content-type': 'text/event-stream' } });
}

(async () => {
  const runId = '11111111-1111-4111-8111-111111111111';
  const requests = [];
  let streamCount = 0;
  const request = async (path, init = {}) => {
    requests.push({ path, init });
    if (path.includes('/events?')) {
      return new Response(JSON.stringify({ events: [event(1), event(2)], next_after_sequence: 2, has_more: false }), { status: 200, headers: { 'content-type': 'application/json' } });
    }
    if (path.endsWith('/events/stream')) {
      streamCount += 1;
      return streamCount === 1 ? sseResponse([event(2), event(3)]) : sseResponse([event(3), event(4)]);
    }
    throw new Error(`unexpected request ${path}`);
  };

  const client = new RunObservabilityClient(request);
  const replay = await client.replay(runId);
  assert.deepEqual(replay.map((item) => item.sequence), [1, 2]);
  assert.equal(client.cursor.last(runId), 2);

  const first = [];
  const firstStates = [];
  await client.stream(runId, (item) => first.push(item.sequence), (state) => firstStates.push(state));
  assert.deepEqual(first, [3], 'duplicate SSE sequence must not be rendered');
  assert.equal(client.cursor.last(runId), 3);
  assert.deepEqual(firstStates, ['RECONNECTING', 'LIVE', 'CLOSED']);

  const second = [];
  await client.stream(runId, (item) => second.push(item.sequence));
  assert.deepEqual(second, [4], 'reconnect must ignore the replayed last event');
  assert.equal(client.cursor.last(runId), 4);

  const streamRequests = requests.filter((entry) => entry.path.endsWith('/events/stream'));
  assert.equal(streamRequests[0].init.headers['Last-Event-ID'], '2');
  assert.equal(streamRequests[1].init.headers['Last-Event-ID'], '3');

  client.cursor.reset(runId);
  assert.equal(client.cursor.last(runId), 0, 'run switch/reset must discard observer cursor state');

  console.log('run observability reconnect tests passed');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
