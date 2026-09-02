"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.MAX_AUTONOMY_REQUESTS_PER_CONTINUATION = exports.AUTONOMOUS_ENGINEERING_RUN_STATES = void 0;
exports.canContinueEngineeringRunAutonomously = canContinueEngineeringRunAutonomously;
exports.isAuthoritativeAutonomyAdvance = isAuthoritativeAutonomyAdvance;
exports.automaticAutonomyOperationKey = automaticAutonomyOperationKey;
exports.autonomyContinuationDisposition = autonomyContinuationDisposition;
exports.AUTONOMOUS_ENGINEERING_RUN_STATES = ['PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY'];
exports.MAX_AUTONOMY_REQUESTS_PER_CONTINUATION = 8;
const autonomousStates = new Set(exports.AUTONOMOUS_ENGINEERING_RUN_STATES);
function canContinueEngineeringRunAutonomously(run) {
    return run.binding_status === 'APPROVED_SPEC_BOUND' && autonomousStates.has(run.state);
}
function isAuthoritativeAutonomyAdvance(requested, latest) {
    if (!latest || latest.id !== requested.id)
        return false;
    if (!Number.isInteger(requested.revision) || requested.revision < 0)
        return false;
    if (!Number.isInteger(latest.revision) || latest.revision < 0)
        return false;
    return latest.revision > requested.revision;
}
function automaticAutonomyOperationKey(run) {
    if (!run.id.trim())
        throw new Error('Engineering Run id is required for automatic autonomy.');
    if (!Number.isInteger(run.revision) || run.revision < 0)
        throw new Error('Engineering Run revision is invalid for automatic autonomy.');
    const key = `autonomous-auto-${run.id}-${run.revision}`;
    if (key.length > 160)
        throw new Error('Automatic autonomy operation identity is unbounded.');
    return key;
}
function autonomyContinuationDisposition(run, stopReason, completedRequests) {
    if (!Number.isInteger(completedRequests) || completedRequests < 1) {
        throw new Error('Autonomy continuation request count is invalid.');
    }
    if (stopReason !== 'MAX_STEPS_REACHED' || !canContinueEngineeringRunAutonomously(run)) {
        return 'STOP';
    }
    return completedRequests >= exports.MAX_AUTONOMY_REQUESTS_PER_CONTINUATION
        ? 'LIMIT_REACHED'
        : 'CONTINUE';
}
