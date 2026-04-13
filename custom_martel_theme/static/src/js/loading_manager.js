/** @odoo-module **/
/**
 * Martel Loading Manager
 *
 * Distinguishes between two types of loading:
 *
 *  1. PAGE NAVIGATION  → adds `o_martel_nav_loading` to <body>
 *     Detected via routerBus "BEFORE_ROUTE_CHANGE" + cleared when all
 *     pending RPCs settle to zero.
 *     CSS shows: full-page frosted-glass overlay with spinner.
 *
 *  2. MINOR RPC CALLS  → no body class added
 *     CSS shows: thin 3px shimmer bar at the top of the viewport.
 *     Non-blocking, does not obscure the UI.
 *
 * Both buses are internal Odoo 18 core APIs:
 *   rpcBus    – @web/core/network/rpc
 *   routerBus – @web/core/browser/router
 */

import { registry }   from "@web/core/registry";
import { rpcBus }     from "@web/core/network/rpc";
import { routerBus }  from "@web/core/browser/router";

const NAV_CLASS    = "o_martel_nav_loading";
const SAFETY_MS    = 10_000; // max time overlay stays visible (failsafe)
const ROUTE_LAG_MS = 400;    // wait after ROUTE_CHANGE before clearing if no RPCs

const martelLoadingService = {
    dependencies: [],
    start() {
        let pendingRpcs  = 0;
        let isNavigating = false;
        let safetyTimer  = null;

        // ── Helpers ────────────────────────────────────────────────────────
        const activate = () => {
            clearTimeout(safetyTimer);
            isNavigating = true;
            document.body.classList.add(NAV_CLASS);

            // Failsafe: never leave the overlay stuck forever
            safetyTimer = setTimeout(deactivate, SAFETY_MS);
        };

        const deactivate = () => {
            clearTimeout(safetyTimer);
            isNavigating = false;
            document.body.classList.remove(NAV_CLASS);
        };

        // ── RPC tracking ───────────────────────────────────────────────────
        rpcBus.addEventListener("RPC:REQUEST", ({ detail }) => {
            if (detail?.settings?.silent) return;
            pendingRpcs++;
        });

        rpcBus.addEventListener("RPC:RESPONSE", ({ detail }) => {
            if (detail?.settings?.silent) return;
            pendingRpcs = Math.max(0, pendingRpcs - 1);

            // Clear overlay as soon as all nav-related RPCs settle
            if (pendingRpcs === 0 && isNavigating) {
                deactivate();
            }
        });

        // ── Router tracking ────────────────────────────────────────────────
        routerBus.addEventListener("BEFORE_ROUTE_CHANGE", () => {
            activate();
        });

        // Fallback: route changed but no RPCs were triggered (cached view)
        routerBus.addEventListener("ROUTE_CHANGE", () => {
            if (!isNavigating) return;
            if (pendingRpcs === 0) {
                setTimeout(() => {
                    if (pendingRpcs === 0) deactivate();
                }, ROUTE_LAG_MS);
            }
        });

        return {};
    },
};

registry.category("services").add("martel_loading_manager", martelLoadingService);
