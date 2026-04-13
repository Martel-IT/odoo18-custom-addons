/** @odoo-module **/
/**
 * Martel Loading Manager – two-stage loading indicator
 *
 * Stage 1 (JS, 400ms)  → floating pill bottom-right via body.o_martel_loading
 * Stage 2 (JS, 2000ms) → full frosted-glass overlay via body.o_martel_long_loading
 *
 * Both stages are driven by JS timers so they survive OWL component mount/unmount.
 */

import { registry } from "@web/core/registry";
import { rpcBus }   from "@web/core/network/rpc";

const PILL_LOAD_MS  = 400;
const LONG_LOAD_MS  = 2000;
const PILL_CLASS    = "o_martel_loading";
const LONG_CLASS    = "o_martel_long_loading";

const martelLoadingService = {
    dependencies: [],
    start() {
        let pendingRpcs   = 0;
        let pillTimer     = null;
        let longLoadTimer = null;

        const startTimers = () => {
            if (!pillTimer) {
                pillTimer = setTimeout(() => {
                    document.body.classList.add(PILL_CLASS);
                }, PILL_LOAD_MS);
            }
            if (!longLoadTimer) {
                longLoadTimer = setTimeout(() => {
                    document.body.classList.add(LONG_CLASS);
                }, LONG_LOAD_MS);
            }
        };

        const clearTimers = () => {
            clearTimeout(pillTimer);
            clearTimeout(longLoadTimer);
            pillTimer     = null;
            longLoadTimer = null;
            document.body.classList.remove(PILL_CLASS);
            document.body.classList.remove(LONG_CLASS);
        };

        rpcBus.addEventListener("RPC:REQUEST", ({ detail }) => {
            if (detail?.settings?.silent) return;
            pendingRpcs++;
            if (pendingRpcs === 1) startTimers();
        });

        rpcBus.addEventListener("RPC:RESPONSE", ({ detail }) => {
            if (detail?.settings?.silent) return;
            pendingRpcs = Math.max(0, pendingRpcs - 1);
            if (pendingRpcs === 0) clearTimers();
        });

        return {};
    },
};

registry.category("services").add("martel_loading_manager", martelLoadingService);
