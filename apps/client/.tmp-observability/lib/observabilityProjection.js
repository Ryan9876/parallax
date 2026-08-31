"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PIPELINE_STAGES = void 0;
exports.visibleStage = visibleStage;
exports.projectPipeline = projectPipeline;
exports.observedLineages = observedLineages;
exports.observedAttempts = observedAttempts;
exports.latestCandidateLineage = latestCandidateLineage;
exports.safeEventMetadata = safeEventMetadata;
exports.observabilitySummary = observabilitySummary;
exports.componentHealth = componentHealth;
exports.evidenceAuditFacts = evidenceAuditFacts;
exports.activeRunObservation = activeRunObservation;
exports.recentAlerts = recentAlerts;
exports.providerIdentities = providerIdentities;
exports.observerHealth = observerHealth;
exports.eventHasTerminalOutcome = eventHasTerminalOutcome;
exports.PIPELINE_STAGES = ['SPECIFY', 'PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY', 'REVIEW'];
const TERMINAL_OUTCOMES = new Set(['SUCCEEDED', 'FAILED', 'HUMAN_REQUIRED']);
const ATTENTION_OUTCOMES = new Set(['FAILED', 'DENIED', 'RECOVERING', 'HUMAN_REQUIRED']);
const SAFE_METADATA_KEYS = new Set([
    'attempt_number',
    'branch_name',
    'command_id',
    'content_digest',
    'control_status',
    'current_state',
    'current_step',
    'error_class',
    'evaluation_id',
    'exit_code',
    'file_count',
    'meaningful_progress',
    'mutation_applied',
    'next_recovery_action',
    'preview_deployment_id',
    'preview_status',
    'program_id',
    'pull_request_number',
    'retry_count',
    'run_revision',
    'score_class',
    'source_revision',
    'stop_reason',
    'target_state',
    'timed_out',
    'tool_id',
    'worker_state',
]);
function visibleStage(event) {
    if (event.event_type === 'REVIEW_REQUIRED' || event.outcome === 'HUMAN_REQUIRED' || event.subsystem === 'REVIEW')
        return 'REVIEW';
    if (event.event_type === 'RUN_CREATED')
        return 'SPECIFY';
    if (event.event_type === 'SOURCE_LINEAGE_ACCEPTED' || event.subsystem === 'IMPLEMENTATION' || event.subsystem === 'SOURCE_LINEAGE')
        return 'IMPLEMENT';
    if (event.stage === 'PLAN' || event.stage === 'BUILD' || event.stage === 'TEST' || event.stage === 'VERIFY')
        return event.stage;
    return null;
}
function statusForEvent(event) {
    if (event.outcome === 'HUMAN_REQUIRED')
        return 'HUMAN_REQUIRED';
    if (event.outcome === 'RECOVERING' || event.outcome === 'REPLAYED')
        return 'RECOVERING';
    if (event.outcome === 'FAILED' || event.outcome === 'DENIED')
        return 'FAILED';
    if (event.outcome === 'SUCCEEDED')
        return 'COMPLETE';
    return 'ACTIVE';
}
function componentStatus(event, supersedingRunControl = null) {
    if (!event)
        return { status: 'Unavailable', tone: 'neutral', detail: 'No persisted evidence for this component.', sequence: null };
    if (event.outcome === 'FAILED' || event.outcome === 'DENIED') {
        if (supersedingRunControl && supersedingRunControl.sequence > event.sequence) {
            return {
                status: 'Awaiting evidence',
                tone: 'teal',
                detail: `Run control resumed after prior component failure #${event.sequence}; awaiting fresh component evidence.`,
                sequence: supersedingRunControl.sequence,
            };
        }
        return { status: 'Attention', tone: 'rust', detail: event.summary || event.failure_code || 'Persisted failure evidence.', sequence: event.sequence };
    }
    if (event.outcome === 'RECOVERING' || event.outcome === 'REPLAYED') {
        return { status: 'Recovering', tone: 'teal', detail: event.summary || 'Persisted recovery evidence.', sequence: event.sequence };
    }
    if (event.outcome === 'HUMAN_REQUIRED') {
        return { status: 'Review required', tone: 'olive', detail: event.summary || 'A protected human boundary was reached.', sequence: event.sequence };
    }
    if (event.outcome === 'SUCCEEDED') {
        return { status: 'Observed', tone: 'olive', detail: event.summary || 'Persisted success evidence observed.', sequence: event.sequence };
    }
    return { status: 'Observed', tone: 'teal', detail: event.summary || `${event.event_type} · ${event.outcome}`, sequence: event.sequence };
}
function latestMatching(events, predicate) {
    for (let index = events.length - 1; index >= 0; index -= 1) {
        const event = events[index];
        if (event && predicate(event))
            return event;
    }
    return null;
}
function latestResumeBoundary(events) {
    return latestMatching(events, (event) => {
        if (event.event_type !== 'RUN_CONTROL')
            return false;
        const controlStatus = String(event.metadata.control_status ?? '').toUpperCase();
        return controlStatus === 'RESUMED' || event.outcome === 'PROGRESSED' || event.outcome === 'REPLAYED';
    });
}
function referencedComponentStatus(event, detail) {
    if (!event)
        return { status: 'Unavailable', tone: 'neutral', detail: 'No persisted evidence for this component.', sequence: null };
    return { status: 'Observed', tone: 'teal', detail, sequence: event.sequence };
}
function projectPipeline(run, events) {
    const latest = new Map();
    for (const event of events) {
        const stage = visibleStage(event);
        if (stage)
            latest.set(stage, event);
    }
    const failedStage = run.state === 'FAILED' && run.resume_stage && exports.PIPELINE_STAGES.includes(run.resume_stage)
        ? run.resume_stage
        : null;
    return exports.PIPELINE_STAGES.map((stage) => {
        const event = latest.get(stage);
        if (event) {
            return { stage, status: statusForEvent(event), sequence: event.sequence, summary: event.summary };
        }
        if (failedStage === stage) {
            return {
                stage,
                status: 'FAILED',
                sequence: null,
                summary: run.last_failure_code ? `${stage} failed · ${run.last_failure_code}` : `${stage} failed`,
            };
        }
        // Existing authoritative run state may identify the currently active protected stage,
        // but absence of persisted success never becomes completion.
        if (run.state === stage || (stage === 'REVIEW' && run.state === 'REVIEW')) {
            return { stage, status: stage === 'REVIEW' ? 'HUMAN_REQUIRED' : 'ACTIVE', sequence: null, summary: null };
        }
        return { stage, status: 'PENDING', sequence: null, summary: null };
    });
}
function observedLineages(events) {
    const seen = new Set();
    const result = [];
    for (const event of events) {
        for (const lineage of [event.parent_source_lineage_ref, event.source_lineage_ref]) {
            if (lineage && !seen.has(lineage)) {
                seen.add(lineage);
                result.push(lineage);
            }
        }
    }
    return result;
}
function observedAttempts(events) {
    const seen = new Set();
    const result = [];
    for (const event of events) {
        if (event.attempt_id && !seen.has(event.attempt_id)) {
            seen.add(event.attempt_id);
            result.push(event.attempt_id);
        }
    }
    return result;
}
function latestCandidateLineage(events) {
    for (let index = events.length - 1; index >= 0; index -= 1) {
        const event = events[index];
        if (!event)
            continue;
        if (event.source_lineage_ref)
            return { candidate: event.source_lineage_ref, parent: event.parent_source_lineage_ref };
    }
    return { candidate: null, parent: null };
}
function safeEventMetadata(event) {
    return Object.entries(event.metadata)
        .filter(([key]) => SAFE_METADATA_KEYS.has(key))
        .slice(0, 12)
        .map(([key, value]) => ({
        key,
        value: Array.isArray(value) ? value.map(String).join(', ') : String(value),
    }));
}
function observabilitySummary(events) {
    const latest = events.at(-1) ?? null;
    const attention = events.filter((event) => ATTENTION_OUTCOMES.has(event.outcome)).length;
    const recovery = events.filter((event) => event.outcome === 'RECOVERING' || event.outcome === 'REPLAYED').length;
    const hasEvents = events.length > 0;
    return [
        { key: 'events', label: 'Persisted events', value: String(events.length), note: 'Run-scoped event records', available: true, tone: 'neutral' },
        { key: 'sequence', label: 'Latest sequence', value: latest ? `#${latest.sequence}` : 'Unavailable', note: latest ? 'Highest observed durable sequence' : 'No persisted event observed', available: hasEvents, tone: latest ? 'teal' : 'neutral' },
        { key: 'attention', label: 'Attention states', value: hasEvents ? String(attention) : 'Not measured', note: 'Failure, recovery or human boundary', available: hasEvents, tone: attention > 0 ? 'rust' : hasEvents ? 'olive' : 'neutral' },
        { key: 'recovery', label: 'Recovery / replay', value: hasEvents ? String(recovery) : 'Not measured', note: 'Persisted recovery outcomes only', available: hasEvents, tone: recovery > 0 ? 'teal' : 'neutral' },
    ];
}
function componentHealth(events, transport, run) {
    const transportItem = transport === 'LIVE'
        ? { key: 'event-plane', label: 'Run event plane', status: 'Live', detail: 'Replay completed and resumable event observation is live.', sequence: events.at(-1)?.sequence ?? null, tone: 'olive' }
        : transport === 'CONNECTING'
            ? { key: 'event-plane', label: 'Run event plane', status: 'Connecting', detail: 'Observer transport is establishing or re-establishing the stream.', sequence: events.at(-1)?.sequence ?? null, tone: 'teal' }
            : transport === 'ERROR'
                ? { key: 'event-plane', label: 'Run event plane', status: 'Attention', detail: 'Observer transport reported an error; persisted replay remains authoritative.', sequence: events.at(-1)?.sequence ?? null, tone: 'rust' }
                : { key: 'event-plane', label: 'Run event plane', status: 'Unavailable', detail: 'Live observer transport is not currently connected.', sequence: events.at(-1)?.sequence ?? null, tone: 'neutral' };
    const authoritativeRun = run
        ? run.state === 'FAILED'
            ? {
                key: 'run',
                label: 'Engineering Run',
                status: 'Failed',
                detail: `${run.resume_stage || 'Run'} failed${run.last_failure_code ? ` · ${run.last_failure_code}` : ''}. Durable Engineering Run state remains authoritative even when optional component evidence is unavailable.`,
                sequence: null,
                tone: 'rust',
            }
            : run.state === 'REVIEW'
                ? { key: 'run', label: 'Engineering Run', status: 'Review required', detail: 'Authoritative run reached the protected operator review boundary.', sequence: null, tone: 'olive' }
                : run.state === 'COMPLETE'
                    ? { key: 'run', label: 'Engineering Run', status: 'Complete', detail: 'Authoritative run is complete.', sequence: null, tone: 'olive' }
                    : { key: 'run', label: 'Engineering Run', status: 'Active', detail: `Authoritative run state: ${run.state}.`, sequence: null, tone: 'teal' }
        : null;
    const resumeBoundary = latestResumeBoundary(events);
    const worker = latestMatching(events, (event) => event.subsystem === 'WORKER');
    const workerReference = latestMatching(events, (event) => Boolean(event.worker_execution_id));
    const lineage = latestMatching(events, (event) => event.subsystem === 'SOURCE_LINEAGE' || event.event_type === 'SOURCE_LINEAGE_ACCEPTED');
    const lineageReference = latestMatching(events, (event) => Boolean(event.source_lineage_ref));
    const github = latestMatching(events, (event) => event.subsystem === 'GITHUB');
    const vercel = latestMatching(events, (event) => event.subsystem === 'VERCEL');
    const evaluation = latestMatching(events, (event) => event.subsystem === 'EVALUATION' || event.event_type === 'EVALUATION_RESULT');
    const workerStatus = worker
        ? componentStatus(worker, resumeBoundary)
        : referencedComponentStatus(workerReference, 'Worker execution identity is present in persisted run evidence; no dedicated worker-health event is available yet.');
    const lineageStatus = lineage
        ? componentStatus(lineage, resumeBoundary)
        : referencedComponentStatus(lineageReference, 'Source lineage is referenced by persisted run evidence; no dedicated lineage-health event is available yet.');
    return [
        ...(authoritativeRun ? [authoritativeRun] : []),
        transportItem,
        { key: 'worker', label: 'Worker runtime', ...workerStatus },
        { key: 'source-lineage', label: 'Source lineage', ...lineageStatus },
        { key: 'github', label: 'GitHub provider', ...componentStatus(github) },
        { key: 'vercel', label: 'Vercel Preview', ...componentStatus(vercel) },
        { key: 'evaluation', label: 'Evaluation', ...componentStatus(evaluation) },
    ];
}
function evidenceAuditFacts(events) {
    const latest = events.at(-1) ?? null;
    const lineage = latestCandidateLineage(events);
    const latestAttempt = latestMatching(events, (event) => Boolean(event.attempt_id));
    const latestEvidence = latestMatching(events, (event) => Boolean(event.evidence_ref));
    const latestArtifact = latestMatching(events, (event) => Boolean(event.artifact_ref));
    const latestOperation = latestMatching(events, (event) => Boolean(event.operation_ref));
    const facts = [
        ['project', 'Project ID', latest?.project_id],
        ['run', 'Run ID', latest?.run_id],
        ['candidate', 'Candidate lineage', lineage.candidate],
        ['parent', 'Parent lineage', lineage.parent],
        ['attempt', 'Latest attempt', latestAttempt?.attempt_id],
        ['evidence', 'Evidence reference', latestEvidence?.evidence_ref],
        ['artifact', 'Artifact reference', latestArtifact?.artifact_ref],
        ['operation', 'Operation reference', latestOperation?.operation_ref],
    ];
    return facts.map(([key, label, value]) => ({ key, label, value: value || 'Unavailable', available: Boolean(value) }));
}
function activeRunObservation(events) {
    const latest = events.at(-1) ?? null;
    if (!latest) {
        return { projectId: 'Unavailable', runId: 'Unavailable', latestStage: 'Unavailable', latestOutcome: 'Unavailable', latestSequence: 'Unavailable' };
    }
    return {
        projectId: latest.project_id,
        runId: latest.run_id,
        latestStage: visibleStage(latest) ?? latest.stage ?? latest.subsystem,
        latestOutcome: latest.outcome,
        latestSequence: `#${latest.sequence}`,
    };
}
function recentAlerts(events, limit = 5) {
    return events
        .filter((event) => ATTENTION_OUTCOMES.has(event.outcome))
        .slice(-limit)
        .reverse()
        .map((event) => ({
        key: `${event.id}:${event.sequence}`,
        sequence: event.sequence,
        tone: event.outcome === 'RECOVERING' ? 'teal' : event.outcome === 'HUMAN_REQUIRED' ? 'olive' : 'rust',
        title: event.outcome === 'HUMAN_REQUIRED' ? 'Human review required' : event.outcome === 'RECOVERING' ? 'Recovery in progress' : 'Execution attention required',
        detail: event.summary || event.failure_code || `${event.subsystem} · ${event.outcome}`,
    }));
}
function providerIdentities(events) {
    const identities = [];
    for (const event of events) {
        if (event.subsystem === 'GITHUB') {
            const value = event.metadata.pull_request_number;
            identities.push({ provider: 'GitHub', sequence: event.sequence, status: event.outcome, identifier: typeof value === 'number' || typeof value === 'string' ? `PR #${value}` : null });
        }
        else if (event.subsystem === 'VERCEL') {
            const deployment = event.metadata.preview_deployment_id;
            const status = event.metadata.preview_status;
            identities.push({ provider: 'Vercel', sequence: event.sequence, status: typeof status === 'string' ? status : event.outcome, identifier: typeof deployment === 'string' ? deployment : null });
        }
    }
    return identities.slice(-4).reverse();
}
function observerHealth(transport, run, events) {
    const latestAttention = [...events].reverse().find((event) => ATTENTION_OUTCOMES.has(event.outcome));
    if (run.state === 'FAILED' || latestAttention?.outcome === 'FAILED')
        return { transport, run: 'Attention', tone: 'rust' };
    if (latestAttention?.outcome === 'HUMAN_REQUIRED' || run.state === 'REVIEW')
        return { transport, run: 'Review required', tone: 'olive' };
    if (latestAttention?.outcome === 'RECOVERING')
        return { transport, run: 'Recovering', tone: 'teal' };
    if (transport === 'ERROR')
        return { transport, run: run.state, tone: 'rust' };
    if (transport === 'LIVE')
        return { transport, run: run.state, tone: 'olive' };
    return { transport, run: run.state, tone: 'neutral' };
}
function eventHasTerminalOutcome(event) {
    return TERMINAL_OUTCOMES.has(event.outcome);
}
