import { registry } from "@web/core/registry";

function getFormRecordId() {
    const sheet = document.querySelector(".o_form_sheet");
    if (!sheet) return null;


    const byClass = sheet.querySelector(".o_password_entry_id_source");
    const byDataName = sheet.querySelector("[data-name='id']");
    let el = byClass || byDataName;
    if (el) {
        const input = el.querySelector("input");
        if (input && input.value) return parseInt(input.value, 10);
        const text = (el.textContent || "").trim().replace(/\s+/g, " ");
        const num = parseInt(text, 10);
        if (!isNaN(num)) return num;
    }

  
    const form = sheet.closest("form") || sheet.closest(".o_form_view_container") || document.body;
    const idInput = form.querySelector('input[name="id"]');
    if (idInput && idInput.value) return parseInt(idInput.value, 10);


    const hash = (typeof location !== "undefined" && location.hash) || "";
    if (hash && hash.indexOf("=") >= 0) {
        const params = new URLSearchParams(hash.slice(1));
        const idParam = params.get("id") || params.get("resId");
        if (idParam && idParam !== "new") {
            const num = parseInt(idParam, 10);
            if (!isNaN(num)) return num;
        }
    }


    const pathname = (typeof location !== "undefined" && location.pathname) || "";
    const pathStr = pathname + " " + (hash && hash.indexOf("=") < 0 ? hash.slice(1) : "");
    const pathMatch = pathStr.match(/(?:password\.entry|m-password\.entry)\/(\d+)/);
    if (pathMatch) {
        const num = parseInt(pathMatch[1], 10);
        if (!isNaN(num)) return num;
    }

    return null;
}

document.addEventListener("click", async (ev) => {
    const btn = ev.target.closest("[data-action]");
    if (!btn || !btn.dataset.action) return;

    const action = btn.dataset.action;
    const input = document.getElementById("password_field");
    if (!input) return;

    const recordId = getFormRecordId();
    const orm = registry.category("services").get("orm");
    const notification = registry.category("services").get("notification");
    if (!recordId) {
        notification.add("Cannot get record id. Save the entry first, then use Reveal or Copy.", { type: "warning" });
        return;
    }

    if (action === "reveal") {
        const isRevealed = input.type === "text";
        if (isRevealed) {
            input.type = "password";
            input.value = "";
            const icon = btn.querySelector(".o_reveal_icon");
            if (icon) icon.textContent = "👁";
            btn.title = "Show / Hide password";
            return;
        }
        try {
            const password = await orm.call(
                "password.entry",
                "action_reveal_password",
                [[recordId]]
            );
            input.value = password || "";
            input.type = "text";
            const icon = btn.querySelector(".o_reveal_icon");
            if (icon) icon.textContent = "🙈";
            btn.title = "Hide password";
        } catch (e) {
            notification.add(e?.message || "Could not reveal password", { type: "danger" });
        }
        return;
    }

    if (action === "copy") {
        try {
            const password = await orm.call(
                "password.entry",
                "action_copy_password",
                [[recordId]]
            );
            if (password) {
                await navigator.clipboard.writeText(password);
                notification.add("Password copied to clipboard", { type: "success" });
            } else {
                notification.add("No password set", { type: "warning" });
            }
        } catch (e) {
            notification.add(e?.message || "Could not copy password", { type: "danger" });
        }
    }
});
