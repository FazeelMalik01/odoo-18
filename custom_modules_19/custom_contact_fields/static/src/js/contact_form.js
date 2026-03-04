/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

const PARTNER_MODEL = "res.partner";

patch(FormController.prototype, {
    setup() {
        super.setup();
        // Only run contact-specific logic on res.partner form (avoid company form and others)
        const resModel = this.props?.resModel;
        if (resModel !== PARTNER_MODEL) {
            return;
        }
        this._updateEmailLabelOnLoad();
        this._watchRecordChanges();
    },

    _watchRecordChanges() {
        if (this.props?.resModel !== PARTNER_MODEL) return;
        // Watch for record data changes
        if (this.props && this.props.record) {
            const record = this.props.record;
            if (record.on) {
                record.on("update", () => {
                    setTimeout(() => this._updateEmailLabel(), 100);
                });
            }
            if (record.watch) {
                record.watch((changes) => {
                    if (changes.is_company !== undefined) {
                        setTimeout(() => this._updateEmailLabel(), 100);
                    }
                });
            }
        }
    },

    _updateEmailLabelOnLoad() {
        if (this.props?.resModel !== PARTNER_MODEL) return;
        setTimeout(() => {
            this._updateEmailLabel();
            this._setupLabelWatcher();
        }, 500);
    },

    _setupLabelWatcher() {
        if (this.props?.resModel !== PARTNER_MODEL) return;
        // Scope observer to the form root only to avoid freezing other forms (e.g. company)
        const formEl = document.querySelector('.o_form_view') || document.querySelector('.o_form_editable');
        if (!formEl) return;

        const observer = new MutationObserver(() => {
            this._updateEmailLabel();
        });
        observer.observe(formEl, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['checked']
        });
        this._contactFormMutationObserver = observer;

        const boundClick = (e) => {
            if (e.target?.type === 'radio' && (e.target.name || '').includes('is_company')) {
                setTimeout(() => this._updateEmailLabel(), 100);
            }
        };
        const boundChange = (e) => {
            if (e.target?.type === 'radio' && (e.target.name || '').includes('is_company')) {
                setTimeout(() => this._updateEmailLabel(), 100);
            }
        };
        formEl.addEventListener('click', boundClick, true);
        formEl.addEventListener('change', boundChange, true);
        this._contactFormClickHandler = boundClick;
        this._contactFormChangeHandler = boundChange;
        this._contactFormEl = formEl;
    },

    _updateEmailLabel() {
        if (this.props?.resModel !== PARTNER_MODEL) return;
        const form = document.querySelector('.o_form_view') ||
                    document.querySelector('.o_form_editable');
        if (!form) return;

        const emailWidget = form.querySelector('.o_field_widget[name="email"]') ||
                           form.querySelector('.o_field_email');
        if (!emailWidget) return;

        const emailInput = emailWidget.querySelector('input[type="email"]') ||
                          emailWidget.querySelector('input[name="email"]') ||
                          emailWidget.querySelector('input');
        if (!emailInput) return;

        // In Odoo 19, the email field structure is:
        // <div class="d-flex align-items-baseline">
        //   <i class="fa fa-envelope" title="Email"/>
        //   <field name="email" placeholder="Email"/>
        // </div>
        let emailIcon = emailWidget.querySelector('i.fa-envelope') ||
                         emailWidget.parentElement?.querySelector('i.fa-envelope') ||
                         emailInput.parentElement?.querySelector('i.fa-envelope') ||
                         emailInput.closest('.d-flex')?.querySelector('i.fa-envelope');
        if (!emailIcon) {
            const parentContainer = emailInput.closest('.d-flex') ||
                                   emailInput.closest('[class*="flex"]') ||
                                   emailWidget.parentElement;
            if (parentContainer) {
                const icons = parentContainer.querySelectorAll('i');
                for (let icon of icons) {
                    if (icon.classList.contains('fa-envelope') ||
                        icon.classList.contains('fa-envelope-o') ||
                        icon.getAttribute('title')?.toLowerCase().includes('email')) {
                        emailIcon = icon;
                        break;
                    }
                }
            }
        }

        const radios = form.querySelectorAll('input[type="radio"]');
        let isCompany = false;

        // PRIORITY 1: Check radio buttons first (they reflect current UI state)
        // Look for all radio buttons and find which one is checked, then determine Person vs Company
        let checkedRadio = null;
        let checkedRadioLabel = null;
        
        // First, find all radio buttons and check their labels/text to identify Person/Company radios
        const personCompanyRadios = [];
        for (let radio of radios) {
            const name = radio.name || radio.getAttribute('name') || '';
            // Get label text to determine if it's Person or Company
            // First, try to find the label element directly associated with this radio
            const label = radio.closest('label') || 
                         (radio.id ? form.querySelector(`label[for="${radio.id}"]`) : null) ||
                         radio.parentElement?.querySelector('label');
            
            let labelText = '';
            if (label) {
                labelText = label.textContent ? label.textContent.trim().toLowerCase() : '';
            }
            
            // If no label found, check the immediate next sibling (text node or element)
            if (!labelText) {
                let sibling = radio.nextSibling;
                while (sibling && !labelText) {
                    if (sibling.nodeType === Node.TEXT_NODE) {
                        labelText = sibling.textContent.trim().toLowerCase();
                    } else if (sibling.nodeType === Node.ELEMENT_NODE && sibling.textContent) {
                        labelText = sibling.textContent.trim().toLowerCase();
                    }
                    sibling = sibling.nextSibling;
                }
            }
            
            // If still no label, check the immediate parent's text (but only the part near this radio)
            if (!labelText) {
                const parent = radio.parentElement;
                if (parent) {
                    // Get text nodes in parent, but only those after this radio
                    const walker = document.createTreeWalker(
                        parent,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    let foundRadio = false;
                    let node;
                    while (node = walker.nextNode()) {
                        if (node.previousSibling === radio || (node.parentElement === parent && parent.childNodes[parent.childNodes.indexOf(radio) + 1] === node)) {
                            foundRadio = true;
                        }
                        if (foundRadio) {
                            const text = node.textContent.trim().toLowerCase();
                            if (text.includes('person') || text.includes('company')) {
                                labelText = text;
                                break;
                            }
                        }
                    }
                }
            }
            
            // Determine if this is Person or Company based on label text
            // Priority: label text should clearly indicate one or the other
            let isPerson = false;
            let isCompanyRadio = false;
            
            if (labelText) {
                // Check if label text contains "person" (and not "company")
                if (labelText.includes('person') && !labelText.includes('company')) {
                    isPerson = true;
                    isCompanyRadio = false;
                }
                // Check if label text contains "company" (and not "person")
                else if (labelText.includes('company') && !labelText.includes('person')) {
                    isPerson = false;
                    isCompanyRadio = true;
                }
            }
            
            // Only add if we can clearly identify it as Person or Company
            if (isPerson || isCompanyRadio) {
                personCompanyRadios.push({
                    radio: radio,
                    isPerson: isPerson,
                    isCompany: isCompanyRadio,
                    label: labelText,
                    checked: radio.checked
                });
            }
        }
        for (let radioInfo of personCompanyRadios) {
            if (radioInfo.checked) {
                checkedRadio = radioInfo.radio;
                isCompany = radioInfo.isCompany;
                checkedRadioLabel = radioInfo.label;
                break;
            }
        }
        if (!checkedRadio || personCompanyRadios.length === 0) {
            if (this.props?.record?.data) {
                const recordIsCompany = this.props.record.data.is_company;
                if (recordIsCompany !== undefined && recordIsCompany !== null) {
                    isCompany = Boolean(recordIsCompany);
                }
            }
        }
        else if (checkedRadioLabel && checkedRadioLabel.includes('person') && isCompany) {
            if (this.props?.record?.data) {
                const recordIsCompany = this.props.record.data.is_company;
                if (recordIsCompany !== undefined && recordIsCompany !== null) {
                    isCompany = Boolean(recordIsCompany);
                } else {
                    isCompany = false;
                }
            }
        }
        else if (checkedRadioLabel && checkedRadioLabel.includes('company') && !isCompany) {
            if (this.props?.record?.data) {
                const recordIsCompany = this.props.record.data.is_company;
                if (recordIsCompany !== undefined && recordIsCompany !== null) {
                    isCompany = Boolean(recordIsCompany);
                } else {
                    isCompany = true;
                }
            }
        }

        const newLabel = isCompany ? 'Email' : 'Work Email';
        if (emailIcon) {
            emailIcon.setAttribute('title', newLabel);
        }
        if (emailInput.placeholder) {
            emailInput.placeholder = newLabel;
        }

        // Find and update the visible text label (the "Work Email" text next to the icon)
        // Look in the parent container for text nodes or span elements
        const parentContainer = emailInput.closest('.d-flex') || 
                               emailInput.closest('[class*="flex"]') ||
                               emailWidget.parentElement ||
                               emailIcon?.parentElement;
        
        if (parentContainer) {
            // First, try to find a span or div that contains the label text
            const labelElements = parentContainer.querySelectorAll('span, div, label');
            for (let el of labelElements) {
                const text = el.textContent ? el.textContent.trim() : '';
                if (text === 'Email' || text === 'Work Email') {
                    el.textContent = newLabel;
                }
            }
            const walker = document.createTreeWalker(
                parentContainer,
                NodeFilter.SHOW_TEXT,
                {
                    acceptNode: function(node) {
                        const text = node.textContent.trim();
                        if (text === 'Email' || text === 'Work Email') {
                            return NodeFilter.FILTER_ACCEPT;
                        }
                        return NodeFilter.FILTER_REJECT;
                    }
                },
                false
            );
            let node;
            while (node = walker.nextNode()) {
                node.textContent = newLabel;
            }
        }
        if (emailIcon) {
            let sibling = emailIcon.nextSibling;
            while (sibling) {
                if (sibling.nodeType === Node.TEXT_NODE) {
                    const text = sibling.textContent.trim();
                    if (text === 'Email' || text === 'Work Email') {
                        sibling.textContent = ' ' + newLabel + ' ';
                        break;
                    }
                } else if (sibling.nodeType === Node.ELEMENT_NODE) {
                    const text = sibling.textContent ? sibling.textContent.trim() : '';
                    if (text === 'Email' || text === 'Work Email') {
                        sibling.textContent = newLabel;
                        break;
                    }
                }
                sibling = sibling.nextSibling;
            }
        }
    },
});
