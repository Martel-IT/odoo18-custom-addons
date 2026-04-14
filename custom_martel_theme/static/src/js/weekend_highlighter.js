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
//
// The Flexitime Analysis tab renders its table inside an <iframe> (a complete
// HTML document). CSS classes from the main document don't reach it, so we
// apply INLINE styles directly on each cell.
//
// Handles two table structures:
//   A) Standard: <thead><tr><th>…</th></tr></thead>
//   B) attendanceTable (iframe): no <thead>, <th>s inside <tbody> rows
//

const DIFF_NEG_STYLE = "background-color:rgba(220,53,69,0.15);color:#b02030;font-weight:600;";
const DIFF_POS_STYLE = "background-color:rgba(25,135,84,0.13);color:#146c43;font-weight:600;";

function _applyDiffStyles(table) {
    // ── Find header row ───────────────────────────────────────────────────────
    let headerRow = table.querySelector("thead tr");
    if (!headerRow) {
        for (const row of table.querySelectorAll("tr")) {
            if (row.querySelector("th")) { headerRow = row; break; }
        }
    }
    if (!headerRow) return;

    // ── Find "Difference" column index ────────────────────────────────────────
    let diffIdx = -1;
    headerRow.querySelectorAll("th, td").forEach((cell, idx) => {
        if ((cell.textContent || "").trim().toLowerCase() === "difference") diffIdx = idx;
    });
    if (diffIdx === -1) return;

    // ── Apply inline styles to every data row ─────────────────────────────────
    table.querySelectorAll("tr").forEach((row) => {
        const cells = row.querySelectorAll("td");
        if (!cells.length) return;          // skip header-only rows
        const cell = cells[diffIdx];
        if (!cell) return;

        const raw = (cell.textContent || "").trim();

        if (!raw || raw === "00:00" || raw === "-") {
            cell.style.cssText = cell.style.cssText
                .replace(/background-color:[^;]+;?/g, "")
                .replace(/color:[^;]+;?/g, "")
                .replace(/font-weight:[^;]+;?/g, "");
        } else if (raw.startsWith("-")) {
            cell.style.cssText = DIFF_NEG_STYLE;
        } else {
            cell.style.cssText = DIFF_POS_STYLE;
        }
    });
}

function colorFlextimeDifference(root) {
    if (!root) return;
    const el = root.nodeType === Node.DOCUMENT_NODE ? root.documentElement : root;

    // ── Main document tables ──────────────────────────────────────────────────
    el.querySelectorAll(
        ".o_notebook .tab-pane table, .o_form_sheet table, table.attendanceTable"
    ).forEach(_applyDiffStyles);

    // ── Tables inside same-origin iframes ─────────────────────────────────────
    el.querySelectorAll("iframe").forEach((iframe) => {
        try {
            const iDoc = iframe.contentDocument || iframe.contentWindow?.document;
            if (!iDoc) return;

            // If the iframe is still loading, wait for it
            if (iDoc.readyState === "loading") {
                iframe.addEventListener("load", () => {
                    iDoc.querySelectorAll("table.attendanceTable, table")
                        .forEach(_applyDiffStyles);
                }, { once: true });
            } else {
                iDoc.querySelectorAll("table.attendanceTable, table")
                    .forEach(_applyDiffStyles);
            }
        } catch (_) {
            // Cross-origin iframe – skip silently
        }
    });
}

// ── Decorate timesheet table: sticky cols + "Project"/"TOT" labels ───────────
//
// Guard: tables already decorated (data-martel-decorated="1") are skipped
// entirely, so re-runs on OWL mutations cost almost nothing.
//
function decorateTimesheetTable(root) {
    if (!root) return;
    const el = root.nodeType === Node.DOCUMENT_NODE ? root.documentElement : root;

    const tables = el.querySelectorAll(
        ".o_grid_renderer table, " +
        ".o_timesheet_container table, " +
        ".o_notebook .tab-pane table, " +
        ".o_form_sheet table"
    );

    tables.forEach((table) => {
        // ── Skip already-processed tables ────────────────────────────────────
        if (table.dataset.martelDecorated) return;

        // ── Skip non-timesheet tables (expense, sales, invoice lines, details) ──
        // timesheet_ids is the Details tab list - OWL owns that DOM and direct
        // class manipulation triggers a re-render that restores pending-deleted rows.
        if (table.closest(
            '.o_field_expense_lines_widget, ' +
            '[name="expense_line_ids"], ' +
            '[name="order_line"], ' +
            '[name="invoice_line_ids"], ' +
            '[name="timesheet_ids"]'
        )) return;

        const headerRow = table.querySelector("thead tr");
        if (!headerRow) return;

        const ths = headerRow.querySelectorAll("th");
        if (ths.length < 2) return;

        // ── Label: top-left "Project" ─────────────────────────────────────────
        const firstTh = ths[0];
        if (!firstTh.textContent.trim()) {
            firstTh.textContent = "Project";
            firstTh.classList.add("martel-label-cell");
        }

        // ── Label: top-right "TOT" ────────────────────────────────────────────
        const lastTh = ths[ths.length - 1];
        if (!lastTh.textContent.trim()) {
            lastTh.textContent = "TOT";
            lastTh.classList.add("martel-label-cell");
        }

        // ── Sticky: all first and last cells in every row ─────────────────────
        table.querySelectorAll("tr").forEach((row) => {
            const cells = row.querySelectorAll("th, td");
            if (!cells.length) return;
            cells[0].classList.add("martel-sticky-first");
            cells[cells.length - 1].classList.add("martel-sticky-last");
        });

        // ── Label: bottom-left total cell "TOT" ───────────────────────────────
        const rows = table.querySelectorAll("tbody tr, tfoot tr");
        if (rows.length) {
            const lastRow = rows[rows.length - 1];
            const firstCell = lastRow.querySelector("th, td");
            if (firstCell && !firstCell.textContent.trim()) {
                firstCell.textContent = "TOT";
                firstCell.classList.add("martel-label-cell");
            }
        }

        // Mark as done – future observer triggers will skip this table
        table.dataset.martelDecorated = "1";
    });
}

// ── Debounced RAF scheduler: coalesces rapid-fire mutations into one run ──────
//
// The MutationObserver can fire dozens of times per second during OWL renders.
// We cancel the pending frame before scheduling a new one, so the actual work
// (querySelectorAll + DOM traversal) runs at most once per paint frame.
//
let _pendingRaf = null;
function scheduleRun() {
    if (_pendingRaf) cancelAnimationFrame(_pendingRaf);
    _pendingRaf = requestAnimationFrame(() => {
        _pendingRaf = null;
        markWeekendColumns(document);
        colorFlextimeDifference(document);
        decorateTimesheetTable(document);
    });
}

// ── MutationObserver: re-run when OWL adds/removes grid/form nodes ───────────
function initWeekendObserver() {
    const target = document.querySelector(".o_web_client") || document.body;

    const observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
            if (m.type !== "childList" || !m.addedNodes.length) continue;

            for (const node of m.addedNodes) {
                if (node.nodeType !== Node.ELEMENT_NODE) continue;

                if (
                    node.matches(
                        ".o_grid_renderer, .o_timesheet_container, " +
                        ".o_notebook, .tab-pane, .o_form_sheet, " +
                        "table, table.attendanceTable, iframe"
                    ) ||
                    node.querySelector(
                        ".o_grid_renderer, .o_timesheet_container, " +
                        ".o_notebook, .o_form_sheet, " +
                        "table, table.attendanceTable, iframe"
                    )
                ) {
                    scheduleRun();
                    return; // one schedule per batch is enough
                }
            }
        }
    });

    observer.observe(target, { childList: true, subtree: true });

    // Re-run when the user switches tabs (Summary / Details / Flexitime)
    target.addEventListener("click", (e) => {
        const tab = e.target.closest(".nav-link, [data-bs-toggle='tab'], .o_notebook .nav-item");
        if (tab) {
            // Small delay so OWL renders the new tab content first
            setTimeout(scheduleRun, 80);
        }
    }, { passive: true });

    // Initial scan
    scheduleRun();
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
