/** @odoo-module **/
/**
 * Martel Innovate – Weekend Highlighter + Flexitime Difference Colorizer
 *
 * 1. Adds `o_weekend` CSS class to <th>/<td> cells whose column header
 *    starts with "Sat" or "Sun".
 *
 * 2. In the Flexitime Analysis table, colors the "Difference" column:
 *    - negative value (starts with "-")  → .o_diff_negative  (red bg)
 *    - positive value (> 00:00)          → .o_diff_positive  (green bg)
 *    - zero (00:00)                      → no class
 *
 * Targets:
 *  - Grid view          (.o_grid_renderer table)
 *  - Timesheet container (.o_timesheet_container table)
 *  - Any table inside the Summary / Details form tabs
 *    (.o_notebook .tab-pane table  and  .o_form_sheet table)
 *
 * Re-runs via MutationObserver (OWL re-renders) and on tab clicks.
 */

import { registry } from "@web/core/registry";

// ── Utility: is this header text a weekend day? ──────────────────────────────
function isWeekendHeader(text) {
    if (!text) return false;
    const t = text.trim().toLowerCase();
    return t.startsWith("sat") || t.startsWith("sun");
}

// ── Core: mark weekend columns in every matching table under `root` ──────────
function markWeekendColumns(root) {
    if (!root) return;

    // Cast to Element so we can call querySelectorAll
    const el = root.nodeType === Node.DOCUMENT_NODE ? root.documentElement : root;

    const tables = el.querySelectorAll(
        ".o_grid_renderer table, " +
        ".o_timesheet_container table, " +
        ".o_notebook .tab-pane table, " +
        ".o_form_sheet table"
    );

    tables.forEach((table) => {
        const headerRow = table.querySelector("thead tr");
        if (!headerRow) return;

        // Build the set of weekend column indices from <th> cells
        const weekendCols = new Set();
        headerRow.querySelectorAll("th").forEach((th, idx) => {
            if (isWeekendHeader(th.innerText || th.textContent)) {
                weekendCols.add(idx);
            }
        });

        if (weekendCols.size === 0) return;

        // Apply / remove class on every row
        table.querySelectorAll("tr").forEach((row) => {
            row.querySelectorAll("th, td").forEach((cell, idx) => {
                cell.classList.toggle("o_weekend", weekendCols.has(idx));
            });
        });
    });
}

// ── Flexitime: color the "Difference" column ─────────────────────────────────
function colorFlextimeDifference(root) {
    if (!root) return;
    const el = root.nodeType === Node.DOCUMENT_NODE ? root.documentElement : root;

    // Find every table that has a "Difference" header
    const tables = el.querySelectorAll(
        ".o_notebook .tab-pane table, .o_form_sheet table"
    );

    tables.forEach((table) => {
        const headerRow = table.querySelector("thead tr");
        if (!headerRow) return;

        // Find the column index of "Difference"
        let diffIdx = -1;
        headerRow.querySelectorAll("th").forEach((th, idx) => {
            const txt = (th.innerText || th.textContent || "").trim().toLowerCase();
            if (txt === "difference") diffIdx = idx;
        });

        if (diffIdx === -1) return;

        // Color each data row's Difference cell
        table.querySelectorAll("tbody tr").forEach((row) => {
            const cells = row.querySelectorAll("td");
            const cell = cells[diffIdx];
            if (!cell) return;

            const raw = (cell.innerText || cell.textContent || "").trim();

            cell.classList.remove("o_diff_negative", "o_diff_positive");

            if (!raw || raw === "00:00" || raw === "-") return;

            if (raw.startsWith("-")) {
                cell.classList.add("o_diff_negative");
            } else {
                cell.classList.add("o_diff_positive");
            }
        });
    });
}

// ── MutationObserver: re-run when OWL adds/removes grid/form nodes ───────────
function initWeekendObserver() {
    const target = document.querySelector(".o_web_client") || document.body;

    const observer = new MutationObserver((mutations) => {
        let relevant = false;

        for (const m of mutations) {
            if (m.type !== "childList" || !m.addedNodes.length) continue;

            for (const node of m.addedNodes) {
                if (node.nodeType !== Node.ELEMENT_NODE) continue;

                if (
                    node.matches(
                        ".o_grid_renderer, .o_timesheet_container, " +
                        ".o_notebook, .tab-pane, .o_form_sheet, table"
                    ) ||
                    node.querySelector(
                        ".o_grid_renderer, .o_timesheet_container, " +
                        ".o_notebook, .o_form_sheet, table"
                    )
                ) {
                    relevant = true;
                    break;
                }
            }
            if (relevant) break;
        }

        if (relevant) {
            requestAnimationFrame(() => {
                markWeekendColumns(document);
                colorFlextimeDifference(document);
            });
        }
    });

    observer.observe(target, { childList: true, subtree: true });

    // Also re-run when the user switches tabs (Summary / Details / Flexitime)
    target.addEventListener("click", (e) => {
        const tab = e.target.closest(".nav-link, [data-bs-toggle='tab'], .o_notebook .nav-item");
        if (tab) {
            // Small delay so OWL renders the new tab content first
            setTimeout(() => {
                markWeekendColumns(document);
                colorFlextimeDifference(document);
            }, 80);
        }
    });

    // Initial scan
    requestAnimationFrame(() => {
        markWeekendColumns(document);
        colorFlextimeDifference(document);
    });
}

// ── Service registration ─────────────────────────────────────────────────────
const martelWeekendService = {
    dependencies: [],
    start() {
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                initWeekendObserver();
            });
        });
        return {};
    },
};

registry.category("services").add("martel_weekend_highlighter", martelWeekendService);
