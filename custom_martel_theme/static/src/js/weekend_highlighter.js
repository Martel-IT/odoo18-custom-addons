/** @odoo-module **/
/**
 * Martel Innovate – Weekend Highlighter for Timesheet Grid
 *
 * Adds the CSS class `o_weekend` to all <th> and <td> elements
 * whose column represents a Saturday (day 6) or Sunday (day 0).
 *
 * Works with both:
 *  - The standalone Grid View  (.o_grid_renderer table)
 *  - The inline timesheet sheet inside a Form View
 *
 * Uses a MutationObserver so it re-applies after OWL re-renders.
 */

import { onWillStart, onMounted, onPatched } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

// ── Utility: parse a date string "Mon, Sep 1" or "Sat, Sep 6" → day index ──
function dayIndexFromHeader(text) {
    if (!text) return -1;
    const t = text.trim().toLowerCase();
    if (t.startsWith("sat")) return 6;
    if (t.startsWith("sun")) return 0;
    return -1;
}

// ── Core function: mark weekend columns in a grid table ─────────────────────
function markWeekendColumns(root) {
    if (!root) return;

    const tables = root.querySelectorAll(
        ".o_grid_renderer table, .o_timesheet_container table"
    );

    tables.forEach((table) => {
        // Build a map: columnIndex → isWeekend (from header row)
        const weekendCols = new Set();

        const headerRow = table.querySelector("thead tr");
        if (!headerRow) return;

        const headers = headerRow.querySelectorAll("th");
        headers.forEach((th, idx) => {
            const txt = th.innerText || th.textContent || "";
            if (dayIndexFromHeader(txt) !== -1) {
                weekendCols.add(idx);
            }
        });

        if (weekendCols.size === 0) return;

        // Apply / remove class on ALL rows
        const rows = table.querySelectorAll("tr");
        rows.forEach((row) => {
            const cells = row.querySelectorAll("th, td");
            cells.forEach((cell, idx) => {
                if (weekendCols.has(idx)) {
                    cell.classList.add("o_weekend");
                } else {
                    cell.classList.remove("o_weekend");
                }
            });
        });
    });
}

// ── MutationObserver: watch the whole .o_web_client for grid re-renders ─────
function initWeekendObserver() {
    const target = document.querySelector(".o_web_client") || document.body;

    const observer = new MutationObserver((mutations) => {
        let relevant = false;
        for (const m of mutations) {
            if (m.type === "childList" && m.addedNodes.length) {
                for (const node of m.addedNodes) {
                    if (
                        node.nodeType === 1 &&
                        (node.matches(".o_grid_renderer, .o_timesheet_container") ||
                            node.querySelector(
                                ".o_grid_renderer, .o_timesheet_container"
                            ))
                    ) {
                        relevant = true;
                        break;
                    }
                }
            }
            if (relevant) break;
        }
        if (relevant) {
            requestAnimationFrame(() => markWeekendColumns(document));
        }
    });

    observer.observe(target, { childList: true, subtree: true });

    // Initial run
    requestAnimationFrame(() => markWeekendColumns(document));
}

// ── Bootstrap: run after app is mounted ─────────────────────────────────────
// We hook into the WebClient service lifecycle by registering a simple service.

import { registry } from "@web/core/registry";

const martelWeekendService = {
    dependencies: [],
    start(env) {
        // Wait for the first paint before attaching observer
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                initWeekendObserver();
            });
        });
        return {};
    },
};

registry.category("services").add("martel_weekend_highlighter", martelWeekendService);
