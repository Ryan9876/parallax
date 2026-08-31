"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.RunObservabilityClient = void 0;
const runEventCursor_1 = require("../state/runEventCursor");
function encode(value) {
    return encodeURIComponent(value);
}
async function requireJson(response) {
    if (!response.ok)
        throw new Error(`Parallax observability request failed (${response.status})`);
    return await response.json();
}
function decodeSseBlock(block, runId) {
    if (!block.trim() || block.trimStart().startsWith(':'))
        return null;
    let id = '';
    let eventName = 'message';
    const data = [];
    for (const line of block.split(/\r?\n/)) {
        if (line.startsWith('id:'))
            id = line.slice(3).trim();
        else if (line.startsWith('event:'))
            eventName = line.slice(6).trim();
        else if (line.startsWith('data:'))
            data.push(line.slice(5).trimStart());
    }
    if (eventName !== 'run-event' || !/^[1-9][0-9]*$/.test(id) || data.length === 0)
        return null;
    const parsed = JSON.parse(data.join('\n'));
    const sequence = Number(id);
    if (!Number.isSafeInteger(sequence) || parsed.sequence !== sequence || parsed.run_id !== runId)
        return null;
    return parsed;
}
class RunObservabilityClient {
    request;
    cursor = new runEventCursor_1.RunEventCursor();
    constructor(request) {
        this.request = request;
    }
    async replay(runId, limit = 100) {
        const after = this.cursor.last(runId);
        const response = await this.request(`/v1/engineering-runs/${encode(runId)}/events?after_sequence=${after}&limit=${limit}`, { method: 'GET' });
        const page = await requireJson(response);
        const accepted = [];
        for (const event of page.events) {
            if (this.cursor.accept(runId, event))
                accepted.push(event);
        }
        return accepted;
    }
    async stream(runId, onEvent, onState, signal) {
        const previous = this.cursor.last(runId);
        onState?.(previous > 0 ? 'RECONNECTING' : 'CONNECTING');
        try {
            const response = await this.request(`/v1/engineering-runs/${encode(runId)}/events/stream`, {
                method: 'GET',
                signal,
                headers: {
                    Accept: 'text/event-stream',
                    ...(previous > 0 ? { 'Last-Event-ID': String(previous) } : {}),
                },
            });
            if (!response.ok || !response.body) {
                throw new Error(`Parallax run-event stream unavailable (${response.status})`);
            }
            onState?.('LIVE');
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            while (true) {
                const { done, value } = await reader.read();
                if (done)
                    break;
                buffer += decoder.decode(value, { stream: true });
                const blocks = buffer.split(/\r?\n\r?\n/);
                buffer = blocks.pop() ?? '';
                for (const block of blocks) {
                    const event = decodeSseBlock(block, runId);
                    if (event && this.cursor.accept(runId, event))
                        onEvent(event);
                }
            }
            buffer += decoder.decode();
            if (buffer.trim()) {
                const event = decodeSseBlock(buffer, runId);
                if (event && this.cursor.accept(runId, event))
                    onEvent(event);
            }
            onState?.('CLOSED');
        }
        catch (error) {
            if (signal?.aborted) {
                onState?.('CLOSED');
                return;
            }
            onState?.('ERROR');
            throw error;
        }
    }
    async sourceTree(runId, lineageId, offset = 0, limit = 100) {
        return requireJson(await this.request(`/v1/engineering-runs/${encode(runId)}/source/${encode(lineageId)}/tree?offset=${offset}&limit=${limit}`, { method: 'GET' }));
    }
    async sourceFile(runId, lineageId, path) {
        return requireJson(await this.request(`/v1/engineering-runs/${encode(runId)}/source/${encode(lineageId)}/file?path=${encode(path)}`, { method: 'GET' }));
    }
    async sourceDiff(runId, fromLineage, toLineage) {
        return requireJson(await this.request(`/v1/engineering-runs/${encode(runId)}/source-diff?from_lineage=${encode(fromLineage)}&to_lineage=${encode(toLineage)}`, { method: 'GET' }));
    }
    async attemptEvidence(runId, attemptId) {
        return requireJson(await this.request(`/v1/engineering-runs/${encode(runId)}/attempts/${encode(attemptId)}/evidence`, { method: 'GET' }));
    }
}
exports.RunObservabilityClient = RunObservabilityClient;
