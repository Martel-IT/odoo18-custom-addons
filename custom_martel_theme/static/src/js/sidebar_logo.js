/** @odoo-module **/
/**
 * Martel Innovate – Sidebar Company Logo
 *
 * Injects the current company's logo at the bottom of the app sidebar
 * (.o_burger_menu / .o_app_menu_sidebar) whenever it is opened.
 *
 * The logo is fetched from /web/image/res.company/{id}/logo
 * and updates automatically if the user switches company.
 */

import { registry } from "@web/core/registry";
import { session } from "@web/session";

// ── Inject logo into a sidebar element ──────────────────────────────────────
function injectLogo(sidebar) {
    if (!sidebar) return;
    if (sidebar.querySelector(".martel_sidebar_logo")) return; // already injected

    const companyId = session.user_companies?.current_company;
    if (!companyId) return;

    const wrapper = document.createElement("div");
    wrapper.className = "martel_sidebar_logo";

    const img = document.createElement("img");
    img.src = `/web/image/res.company/${companyId}/logo`;
    img.alt = session.user_companies?.allowed_companies?.[companyId]?.name || "Company";
    img.setAttribute("loading", "lazy");

    wrapper.appendChild(img);
    sidebar.appendChild(wrapper);
}

// ── Watch for the sidebar to appear / re-render ───────────────────────────
function initSidebarLogoObserver() {
    const target = document.querySelector(".o_web_client") || document.body;

    // Inject into any sidebar already present
    document.querySelectorAll(".o_burger_menu, .o_app_menu_sidebar").forEach(injectLogo);

    const observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
            if (m.type !== "childList") continue;
            for (const node of m.addedNodes) {
                if (node.nodeType !== Node.ELEMENT_NODE) continue;

                if (node.matches(".o_burger_menu, .o_app_menu_sidebar")) {
                    injectLogo(node);
                } else {
                    node.querySelectorAll(".o_burger_menu, .o_app_menu_sidebar")
                        .forEach(injectLogo);
                }
            }
        }
    });

    observer.observe(target, { childList: true, subtree: true });
}

// ── Service ──────────────────────────────────────────────────────────────────
const martelSidebarLogoService = {
    dependencies: [],
    start() {
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                initSidebarLogoObserver();
            });
        });
        return {};
    },
};

registry.category("services").add("martel_sidebar_logo", martelSidebarLogoService);
