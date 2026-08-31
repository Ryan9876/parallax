"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.RunEventCursor = void 0;
class RunEventCursor {
    lastSequenceByRun = new Map();
    last(runId) {
        return this.lastSequenceByRun.get(runId) ?? 0;
    }
    accept(runId, event) {
        if (!runId || event.run_id !== runId)
            return false;
        if (!event.id || !Number.isSafeInteger(event.sequence) || event.sequence <= 0)
            return false;
        const previous = this.last(runId);
        if (event.sequence <= previous)
            return false;
        this.lastSequenceByRun.set(runId, event.sequence);
        return true;
    }
    reset(runId) {
        this.lastSequenceByRun.delete(runId);
    }
}
exports.RunEventCursor = RunEventCursor;
