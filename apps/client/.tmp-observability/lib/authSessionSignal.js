"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.installAuthenticationRequiredListener = installAuthenticationRequiredListener;
exports.emitAuthenticationRequired = emitAuthenticationRequired;
let authenticationRequiredListener = null;
function installAuthenticationRequiredListener(listener) {
    authenticationRequiredListener = listener;
    return () => {
        if (authenticationRequiredListener === listener)
            authenticationRequiredListener = null;
    };
}
function emitAuthenticationRequired() {
    authenticationRequiredListener?.();
}
