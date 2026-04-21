/** @odoo-module **/
/**
 * When the Odoo session expires, the default dialog reloads the current page.
 * That lands the user on a stale deep-link instead of a clean login. Here we
 * redirect to the configured `web.base.url` after clearing browser storage,
 * so the next navigation starts from a clean slate regardless of origin URL.
 */

import { patch } from "@web/core/utils/patch";
import { SessionExpiredDialog } from "@web/core/errors/error_dialogs";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";

patch(SessionExpiredDialog.prototype, {
    onClick() {
        try {
            browser.sessionStorage.clear();
            browser.localStorage.clear();
        } catch (_) {
            // storage access can throw in private mode — ignore
        }
        const target = session.web_base_url || browser.location.origin;
        browser.location.assign(target);
    },
});
