"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.api = exports.ApiRequestError = exports.AuthorizationDeniedError = exports.AuthenticationRequiredError = void 0;
exports.installProjectCompatibilityResolver = installProjectCompatibilityResolver;
exports.authenticatedRequest = authenticatedRequest;
const fetch_1 = require("expo/fetch");
const react_native_1 = require("react-native");
const authSessionSignal_1 = require("./authSessionSignal");
const configuredApiBase = process.env.EXPO_PUBLIC_PARALLAX_API_URL ?? 'http://localhost:8010';
const hostedHttpsWeb = react_native_1.Platform.OS === 'web'
    && typeof globalThis.location !== 'undefined'
    && globalThis.location.protocol === 'https:';
const secureSessionTransport = hostedHttpsWeb || configuredApiBase.startsWith('https://');
const apiBase = hostedHttpsWeb
    ? '/p2-api'
    : react_native_1.Platform.OS === 'web' && configuredApiBase.startsWith('https://')
        ? '/p2-api'
        : configuredApiBase;
const sessionHeaders = { 'X-Parallax-Session': '1' };
let transientAccessToken = '';
let projectCompatibilityResolver = null;
class AuthenticationRequiredError extends Error {
    constructor(message = 'Private access required') {
        super(message);
        this.name = 'AuthenticationRequiredError';
        (0, authSessionSignal_1.emitAuthenticationRequired)();
    }
}
exports.AuthenticationRequiredError = AuthenticationRequiredError;
class AuthorizationDeniedError extends Error {
}
exports.AuthorizationDeniedError = AuthorizationDeniedError;
class ApiRequestError extends Error {
    status;
    constructor(status, message) {
        super(message);
        this.status = status;
        this.name = 'ApiRequestError';
    }
}
exports.ApiRequestError = ApiRequestError;
function installProjectCompatibilityResolver(resolver) {
    projectCompatibilityResolver = resolver;
    return () => {
        if (projectCompatibilityResolver === resolver)
            projectCompatibilityResolver = null;
    };
}
function observeConversation(conversation) {
    if (conversation)
        projectCompatibilityResolver?.observeConversation(conversation);
}
function requestCredentials() {
    return secureSessionTransport ? 'include' : 'same-origin';
}
function authenticatedHeaders() {
    return {
        ...(secureSessionTransport ? sessionHeaders : {}),
        ...(transientAccessToken ? { Authorization: `Bearer ${transientAccessToken}` } : {}),
    };
}
async function responseDetail(response) {
    let detail = `Parallax API ${response.status}`;
    try {
        const payload = await response.json();
        if (typeof payload.detail === 'string' && payload.detail.trim())
            detail = payload.detail;
    }
    catch {
        // Preserve the status fallback when the API did not return JSON.
    }
    return detail;
}
async function authenticatedRequest(path, init) {
    const response = await (0, fetch_1.fetch)(`${apiBase}${path}`, {
        ...init,
        credentials: requestCredentials(),
        headers: { ...authenticatedHeaders(), ...(init?.headers ?? {}) },
    });
    if (response.status === 401)
        throw new AuthenticationRequiredError();
    if (response.status === 403)
        throw new AuthorizationDeniedError(await responseDetail(response));
    return response;
}
async function json(path, init) {
    const response = await (0, fetch_1.fetch)(`${apiBase}${path}`, {
        ...init,
        credentials: requestCredentials(),
        headers: { 'Content-Type': 'application/json', ...authenticatedHeaders(), ...(init?.headers ?? {}) },
    });
    if (response.status === 401)
        throw new AuthenticationRequiredError();
    if (response.status === 403)
        throw new AuthorizationDeniedError(await responseDetail(response));
    if (!response.ok)
        throw new ApiRequestError(response.status, await responseDetail(response));
    return (await response.json());
}
async function establishSession(token) {
    const candidate = token.trim();
    if (!candidate)
        throw new AuthenticationRequiredError();
    const response = await (0, fetch_1.fetch)(`${apiBase}/v1/session`, {
        method: 'POST',
        credentials: requestCredentials(),
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${candidate}`,
        },
    });
    transientAccessToken = '';
    if (response.status === 401)
        throw new AuthenticationRequiredError();
    if (!response.ok)
        throw new ApiRequestError(response.status, await responseDetail(response));
    return (await response.json());
}
async function establishGoogleSession(accessToken) {
    const candidate = accessToken.trim();
    if (!candidate)
        throw new AuthenticationRequiredError('Google authentication required');
    const response = await (0, fetch_1.fetch)(`${apiBase}/v1/session/google`, {
        method: 'POST',
        credentials: requestCredentials(),
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${candidate}`,
        },
    });
    if (response.status === 401)
        throw new AuthenticationRequiredError(await responseDetail(response));
    if (response.status === 403)
        throw new AuthorizationDeniedError(await responseDetail(response));
    if (!response.ok)
        throw new ApiRequestError(response.status, await responseDetail(response));
    return (await response.json());
}
async function getSession() {
    if (!secureSessionTransport)
        return { authenticated: true };
    return json('/v1/session');
}
async function endSession() {
    transientAccessToken = '';
    if (!secureSessionTransport)
        return { authenticated: false };
    const response = await (0, fetch_1.fetch)(`${apiBase}/v1/session`, {
        method: 'DELETE',
        credentials: requestCredentials(),
        headers: { ...sessionHeaders },
    });
    if (!response.ok)
        throw new ApiRequestError(response.status, await responseDetail(response));
    return (await response.json());
}
function decodeEvent(block) {
    let eventName = 'message';
    const dataLines = [];
    for (const rawLine of block.split(/\r?\n/)) {
        if (rawLine.startsWith('event:'))
            eventName = rawLine.slice(6).trim();
        if (rawLine.startsWith('data:'))
            dataLines.push(rawLine.slice(5).trimStart());
    }
    if (!dataLines.length)
        return null;
    if (!['state', 'chunk', 'complete', 'amendment', 'error'].includes(eventName))
        return null;
    const parsed = JSON.parse(dataLines.join('\n'));
    return { event: eventName, data: parsed };
}
async function streamResponse(id, content, onEvent, materialScopeChange = false) {
    const response = await (0, fetch_1.fetch)(`${apiBase}/v1/conversations/${id}/responses`, {
        method: 'POST',
        credentials: requestCredentials(),
        headers: {
            'Content-Type': 'application/json',
            Accept: 'text/event-stream',
            ...authenticatedHeaders(),
        },
        body: JSON.stringify({ content, material_scope_change: materialScopeChange }),
    });
    if (response.status === 401)
        throw new AuthenticationRequiredError();
    if (response.status === 403)
        throw new AuthorizationDeniedError(await responseDetail(response));
    if (!response.ok)
        throw new ApiRequestError(response.status, await responseDetail(response));
    if (!response.body)
        throw new Error('Parallax response stream unavailable');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let text = '';
    let messageId = null;
    let confidence = null;
    let trace = null;
    let phase = 'COMPLETE';
    let scopeDecision = null;
    const handle = (event) => {
        onEvent?.(event);
        if (event.event === 'chunk' && typeof event.data.text === 'string') {
            text += event.data.text;
        }
        if (event.event === 'complete' || event.event === 'amendment') {
            if (typeof event.data.message_id === 'string')
                messageId = event.data.message_id;
            if (typeof event.data.confidence === 'number')
                confidence = event.data.confidence;
            if (typeof event.data.scope_decision === 'string')
                scopeDecision = event.data.scope_decision;
            if (event.data.trace && typeof event.data.trace === 'object') {
                trace = event.data.trace;
            }
            if (event.event === 'amendment') {
                phase = 'SPEC_AMENDMENT';
                if (typeof event.data.text === 'string')
                    text = event.data.text;
            }
        }
        if (event.event === 'error') {
            const message = typeof event.data.message === 'string'
                ? event.data.message
                : typeof event.data.error === 'string'
                    ? event.data.error
                    : 'Parallax response failed';
            throw new Error(message);
        }
    };
    while (true) {
        const { done, value } = await reader.read();
        if (done)
            break;
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() ?? '';
        for (const block of blocks) {
            const event = decodeEvent(block.trim());
            if (event)
                handle(event);
        }
    }
    buffer += decoder.decode();
    if (buffer.trim()) {
        const event = decodeEvent(buffer.trim());
        if (event)
            handle(event);
    }
    return { text, messageId, confidence, trace, phase, scopeDecision };
}
async function createConversation(mode) {
    let projectId = null;
    if (mode === 'code') {
        if (!projectCompatibilityResolver) {
            throw new Error('Select a Project before starting Code work.');
        }
        projectId = (await projectCompatibilityResolver.resolveCodeProject()).trim();
        if (!projectId)
            throw new Error('Select a Project before starting Code work.');
    }
    try {
        const conversation = await json('/v1/conversations', {
            method: 'POST',
            body: JSON.stringify(mode === 'code' ? { mode, project_id: projectId } : { mode }),
        });
        observeConversation(conversation);
        return conversation;
    }
    catch (error) {
        if (mode === 'code' && projectId && error instanceof ApiRequestError && [404, 422].includes(error.status)) {
            projectCompatibilityResolver?.invalidateProject(projectId, error.message);
        }
        throw error;
    }
}
async function getConversation(id) {
    const conversation = await json(`/v1/conversations/${id}`);
    observeConversation(conversation);
    return conversation;
}
async function listConversations() {
    const conversations = await json('/v1/conversations');
    observeConversation(conversations[0]);
    return conversations;
}
exports.api = {
    setAccessToken: (token) => { transientAccessToken = token.trim(); },
    establishSession,
    establishGoogleSession,
    getSession,
    endSession,
    currentAccessUser: () => json('/v1/access/me'),
    listAccessUsers: () => json('/v1/access/users'),
    addAccessUser: (email) => json('/v1/access/users', {
        method: 'POST',
        body: JSON.stringify({ email }),
    }),
    updateAccessUserStatus: (id, status) => json(`/v1/access/users/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
    }),
    listProjects: () => json('/v1/projects'),
    createProject: (request) => json('/v1/projects', {
        method: 'POST',
        body: JSON.stringify({
            name: request.name,
            ...(request.repository_ref ? { repository_ref: request.repository_ref } : {}),
        }),
    }),
    createConversation,
    getConversation,
    listConversations,
    appendMessage: (id, role, content) => json(`/v1/conversations/${id}/messages`, {
        method: 'POST',
        body: JSON.stringify({ role, content }),
    }),
    latestWorkSpecification: (conversationId) => json(`/v1/conversations/${conversationId}/work-specifications/latest`),
    latestApprovedWorkSpecification: (conversationId) => json(`/v1/conversations/${conversationId}/work-specifications/approved`),
    draftWorkSpecification: (conversationId) => json(`/v1/conversations/${conversationId}/work-specifications/draft`, {
        method: 'POST',
    }),
    approveWorkSpecification: (specificationId) => json(`/v1/work-specifications/${specificationId}/approve`, {
        method: 'POST',
    }),
    resumeApprovedScope: (conversationId) => json(`/v1/conversations/${conversationId}/work-specifications/resume-approved-scope`, {
        method: 'POST',
    }),
    streamResponse,
    latestEngineeringRun: (conversationId) => json(`/v1/engineering-runs/conversation/${conversationId}/latest`),
    activateEngineeringRun: (conversationId, workSpecificationId) => json('/v1/engineering-runs/activate', {
        method: 'POST',
        body: JSON.stringify({
            conversation_id: conversationId,
            ...(workSpecificationId ? { work_specification_id: workSpecificationId } : {}),
        }),
    }),
    pauseEngineeringRun: (run, operationKey) => json(`/v1/engineering-runs/${run.id}/pause`, {
        method: 'POST', body: JSON.stringify({ operation_key: operationKey, expected_revision: run.revision }),
    }),
    resumeEngineeringRun: (run, operationKey) => json(`/v1/engineering-runs/${run.id}/resume`, {
        method: 'POST', body: JSON.stringify({ operation_key: operationKey, expected_revision: run.revision }),
    }),
    cancelEngineeringRun: (run, operationKey) => json(`/v1/engineering-runs/${run.id}/cancel`, {
        method: 'POST', body: JSON.stringify({ operation_key: operationKey, expected_revision: run.revision }),
    }),
};
