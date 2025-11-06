/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BarcodeInput } from "@stock_barcode/components/manual_barcode";

patch(BarcodeInput.prototype, {
    setup() {
        super.setup();
        this.state.suggestions = [];
    },

    async _onKeydown(ev) {
        if (ev.key === "Enter" && this.state.barcode) {
            ev.preventDefault();
            await this._onSubmit();
        } else if (ev.key === "Escape") {
            this._hideSuggestions();
        }
    },

    async _onSubmit() {
        if (!this.state.barcode) return;

        try {
            const response = await fetch("/custom_barcode_search/search_product", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
                body: JSON.stringify({
                    jsonrpc: "2.0", method: "call",
                    params: { search_term: this.state.barcode },
                    id: Math.floor(Math.random() * 1000000)
                })
            });
            
            const result = await response.json();
            
            if (result.result?.success) {
                if (result.result.product) {
                    this.props.onSubmit(result.result.product.barcode || this.state.barcode);
                } else if (result.result.suggestions) {
                    this.state.suggestions = result.result.suggestions;
                    this._showSuggestions();
                }
            } else {
                this.props.onSubmit(this.state.barcode);
            }
        } catch (error) {
            this.props.onSubmit(this.state.barcode);
        }
    },

    _showSuggestions() {
        this._hideSuggestions();
        const inputGroup = document.querySelector('.input-group');
        if (!inputGroup) return;
        
        const dropdown = document.createElement('div');
        dropdown.id = 'barcode-dropdown';
        dropdown.style.cssText = `
            position: absolute; top: 100%; left: 0; right: 0; background: white;
            border: 1px solid #ccc; border-top: none; max-height: 200px;
            overflow-y: auto; z-index: 1000; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            margin-bottom: 10px;
        `;
        
        this.state.suggestions.forEach((product, index) => {
            const item = document.createElement('div');
            const isLast = index === this.state.suggestions.length - 1;
            item.style.cssText = `
                padding: 8px 12px; cursor: pointer; display: flex;
                border-bottom: ${isLast ? 'none' : '1px solid #eee'};
                ${isLast ? 'padding-bottom: 12px;' : ''}
            `;
            item.innerHTML = `
                <div>
                    <div style="font-weight: bold;">${product.name}</div>
                    <div style="font-size: 12px; color: #666;">${product.barcode}</div>
                </div>
            `;
            item.onmouseover = () => item.style.backgroundColor = '#f5f5f5';
            item.onmouseout = () => item.style.backgroundColor = 'white';
            item.onclick = () => this._selectProduct(product);
            dropdown.appendChild(item);
        });
        
        inputGroup.style.position = 'relative';
        inputGroup.appendChild(dropdown);
    },

    _hideSuggestions() {
        const dropdown = document.getElementById('barcode-dropdown');
        if (dropdown) dropdown.remove();
    },

    _selectProduct(product) {
        this.state.barcode = product.barcode;
        this._hideSuggestions();
        this.props.onSubmit(product.barcode);
    }
});
