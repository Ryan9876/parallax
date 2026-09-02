"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.WORK_SPEC_RATE_LIMIT_MESSAGE = void 0;
exports.workSpecificationDraftFailureMessage = workSpecificationDraftFailureMessage;
exports.WORK_SPEC_RATE_LIMIT_MESSAGE = 'Model capacity is temporarily unavailable. Retry Capture Spec later; your objective is preserved.';
function workSpecificationDraftFailureMessage(status, detail) {
    if (status === 429)
        return exports.WORK_SPEC_RATE_LIMIT_MESSAGE;
    const clean = detail?.trim();
    return clean || 'Specification drafting failed. Your objective is preserved; retry Capture Spec.';
}
