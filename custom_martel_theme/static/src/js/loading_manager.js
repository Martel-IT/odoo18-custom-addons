/** @odoo-module **/
/**
 * Martel Loading Manager – two-stage loading indicator
 *
 * Stage 1 (CSS, 400ms delay)  → floating pill bottom-right
 *   Handled entirely in SCSS via animation-delay. No JS needed.
 *
 * Stage 2 (JS, 2000ms)  → full frosted-glass overlay
 *   After 2s of continuous loading, adds `o_martel_long_loading` to <body>.
 *   CSS switches to full overlay on that class.
 *   Uses only rpcBus (same bus the Odoo loading indicator uses internally).
 */

import { registry } from "@web/core/registry";
import { rpcBus }   from "@web/core/network/rpc";

const LONG_LOAD_MS  = 2000;
const LONG_CLASS    = "o_martel_long_loading";

const martelLoadingService = {
    dependencies: [],
    start() {
        let pendingRpcs  = 0;
        let longLoadTimer = null;

        const startTimer = () => {
            if (longLoadTimer) return;
            longLoadTimer = setTimeout(() => {
                document.body.classList.add(LONG_CLASS);
            }, LONG_LOAD_MS);
        };

        const clearTimer = () => {
            clearTimeout(longLoadTimer);
            longLoadTimer = null;
            document.body.classList.remove(LONG_CLASS);
        };

        rpcBus.addEventListener("RPC:REQUEST", ({ detail }) => {
            if (detail?.settings?.silent) return;
            pendingRpcs++;
            if (pendingRpcs === 1) startTimer();
        });

        rpcBus.addEventListener("RPC:RESPONSE", ({ detail }) => {
            if (detail?.settings?.silent) return;
            pendingRpcs = Math.max(0, pendingRpcs - 1);
            if (pendingRpcs === 0) clearTimer();
        });

        return {};
    },
};

registry.category("services").add("martel_loading_manager", martelLoadingService);
