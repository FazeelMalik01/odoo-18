/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/chatter/web_portal/chatter";  
import { onMounted } from "@odoo/owl";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => this.makeFullChatterUI());
    },

    makeFullChatterUI() {
        const interval = setInterval(() => {
            const chatterEl = document.querySelector(".o-mail-ChatterContainer");
            if (chatterEl && !chatterEl.parentElement.classList.contains("chatter-wrapper")) {
                clearInterval(interval);
                console.log("✅ Chatter found, enabling full UI features");

                const parent = chatterEl.parentElement;

                // --- Create wrapper (flex layout) ---
                const wrapper = document.createElement("div");
                wrapper.classList.add("chatter-wrapper");
                wrapper.style.display = "flex";
                wrapper.style.width = "100%";
                wrapper.style.height = "100%";
                wrapper.style.overflow = "hidden";
                wrapper.style.position = "relative";

                // Main content container
                const contentDiv = document.createElement("div");
                contentDiv.classList.add("chatter-main");
                contentDiv.style.flex = "1";
                contentDiv.style.overflow = "auto";

                // Move siblings into contentDiv except chatter
                while (parent.firstChild) {
                    if (parent.firstChild !== chatterEl) {
                        contentDiv.appendChild(parent.firstChild);
                    } else break;
                }

                // Style chatter sidebar
                chatterEl.style.flex = "0 0 350px"; // default width
                chatterEl.style.minWidth = "250px";
                chatterEl.style.maxWidth = "600px";
                chatterEl.style.borderLeft = "1px solid #ddd";
                chatterEl.style.background = "white";
                chatterEl.style.overflow = "auto";
                chatterEl.style.position = "relative"; // default inline position

                // Resizer handle
                const resizer = document.createElement("div");
                resizer.classList.add("chatter-resizer");
                resizer.style.width = "8px";
                resizer.style.cursor = "col-resize";
                resizer.style.background = "#f5f5f5";
                resizer.style.display = "flex";
                resizer.style.alignItems = "center";
                resizer.style.justifyContent = "center";
                resizer.style.userSelect = "none";

                // Collapse/expand button
                const toggleBtn = document.createElement("div");
                toggleBtn.textContent = "»";
                toggleBtn.style.cursor = "pointer";
                toggleBtn.style.fontSize = "14px";
                toggleBtn.style.padding = "2px";
                toggleBtn.style.border = "1px solid #ccc";
                toggleBtn.style.borderRadius = "3px";
                toggleBtn.style.background = "white";
                toggleBtn.title = "Collapse/Expand Chatter";

                resizer.appendChild(toggleBtn);

                // Build layout
                wrapper.appendChild(contentDiv);
                wrapper.appendChild(resizer);
                wrapper.appendChild(chatterEl);
                parent.appendChild(wrapper);

                // --- Hide button inside chatter topbar ---
                const topbar = chatterEl.querySelector(".o-mail-Chatter-topbar");
                if (topbar && !topbar.querySelector(".chatter-hide-btn")) {
                    const hideBtn = document.createElement("button");
                    hideBtn.textContent = "Hide";
                    hideBtn.className = "btn btn-sm btn-danger chatter-hide-btn ms-2";
                    hideBtn.onclick = () => {
                        chatterEl.style.display = "none";
                        resizer.style.display = "none";
                        showBtn.style.display = "block";
                    };
                    topbar.appendChild(hideBtn);
                }

                // --- Floating "Show Chatter" button ---
                let showBtn = document.querySelector(".chatter-show-btn");
                if (!showBtn) {
                    showBtn = document.createElement("button");
                    showBtn.textContent = "Show Chatter";
                    showBtn.className = "btn btn-primary chatter-show-btn";
                    showBtn.style.position = "fixed";
                    showBtn.style.bottom = "20px";
                    showBtn.style.right = "20px";
                    showBtn.style.zIndex = "10000";
                    showBtn.style.display = "none";
                    showBtn.onclick = () => {
                        // Reset to default inline position
                        chatterEl.style.display = "block";
                        chatterEl.style.position = "relative";
                        chatterEl.style.left = "";
                        chatterEl.style.top = "";
                        chatterEl.style.width = "";
                        chatterEl.style.height = "";
                        chatterEl.style.flex = "0 0 350px";

                        resizer.style.display = "flex";
                        showBtn.style.display = "none";
                    };
                    document.body.appendChild(showBtn);
                }

                // --- Resizing logic ---
                let isResizing = false;
                resizer.addEventListener("mousedown", (e) => {
                    if (e.target !== toggleBtn) {
                        isResizing = true;
                        document.body.style.cursor = "col-resize";
                    }
                });
                document.addEventListener("mousemove", (e) => {
                    if (!isResizing) return;
                    const newWidth = parent.offsetWidth - e.clientX;
                    if (newWidth > 250 && newWidth < 600) {
                        chatterEl.style.flex = `0 0 ${newWidth}px`;
                    }
                });
                document.addEventListener("mouseup", () => {
                    isResizing = false;
                    document.body.style.cursor = "default";
                });

                // --- Collapse/expand logic ---
                let collapsed = false;
                let lastWidth = chatterEl.offsetWidth; // store last width

                toggleBtn.addEventListener("click", () => {
                    if (!collapsed) {
                        lastWidth = chatterEl.offsetWidth;
                        chatterEl.style.flex = "0 0 40px";
                        chatterEl.style.minWidth = "40px";
                        chatterEl.style.maxWidth = "40px";
                        toggleBtn.textContent = "«";
                        collapsed = true;
                    } else {
                        chatterEl.style.flex = `0 0 ${lastWidth}px`;
                        chatterEl.style.minWidth = "250px";
                        chatterEl.style.maxWidth = "600px";
                        toggleBtn.textContent = "»";
                        collapsed = false;
                    }
                });

                // --- Manual draggable mode (hold topbar + drag) ---
                let offsetX = 0, offsetY = 0, isDragging = false;
                chatterEl.addEventListener("mousedown", (e) => {
                    if (e.target.closest(".o-mail-Chatter-topbar")) {
                        isDragging = true;
                        offsetX = e.clientX - chatterEl.getBoundingClientRect().left;
                        offsetY = e.clientY - chatterEl.getBoundingClientRect().top;

                        chatterEl.style.position = "absolute";
                        chatterEl.style.zIndex = "9999";
                        chatterEl.style.width = chatterEl.offsetWidth + "px";
                        chatterEl.style.height = chatterEl.offsetHeight + "px";
                    }
                });
                document.addEventListener("mousemove", (e) => {
                    if (isDragging) {
                        chatterEl.style.left = e.clientX - offsetX + "px";
                        chatterEl.style.top = e.clientY - offsetY + "px";
                    }
                });
                document.addEventListener("mouseup", () => isDragging = false);
            }
        }, 500);
    },
});
