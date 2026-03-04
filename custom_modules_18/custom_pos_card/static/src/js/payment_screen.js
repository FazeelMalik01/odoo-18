/** @odoo-module */

import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

// Patch PaymentScreenPaymentLines for card number input handling
patch(PaymentScreenPaymentLines.prototype, {
    /**
     * Check if the payment method is a card payment (bank type, not cash or pay_later)
     * Cash: is_cash_count = true, type = 'cash'
     * Card: is_cash_count = false, type = 'bank'
     * Customer Account: type = 'pay_later'
     */
    isCardPayment(line) {
        const paymentMethod = line.payment_method_id;
        if (!paymentMethod) {
            return false;
        }
        // Only show for bank (card) payments - not cash and not pay_later
        return !paymentMethod.is_cash_count && paymentMethod.type === 'bank';
    },

    /**
     * Get the card number for a specific payment line
     */
    getCardNo(line) {
        return line.card_no || '';
    },

    /**
     * Update the card number for a payment line
     */
    onCardNoChange(line, event) {
        const value = event.target.value;
        // Only allow digits and max 4 characters
        const sanitizedValue = value.replace(/\D/g, '').slice(0, 4);
        event.target.value = sanitizedValue;
        
        // Use update method to ensure the change is tracked for syncing
        line.update({ card_no: sanitizedValue });
    },

    /**
     * Validate that only 4 digits are entered
     */
    validateCardNo(event) {
        const key = event.key;
        // Allow: backspace, delete, tab, escape, enter, and digits
        if (
            key === 'Backspace' ||
            key === 'Delete' ||
            key === 'Tab' ||
            key === 'Escape' ||
            key === 'Enter' ||
            (key >= '0' && key <= '9')
        ) {
            // Check max length
            if (key >= '0' && key <= '9' && event.target.value.length >= 4) {
                event.preventDefault();
            }
        } else {
            event.preventDefault();
        }
    },
});

// Patch PaymentScreen for validation
patch(PaymentScreen.prototype, {
    /**
     * Check if all card payments have valid card numbers (4 digits)
     */
    _checkCardNumbersValid() {
        for (const line of this.paymentLines) {
            const paymentMethod = line.payment_method_id;
            // Check if it's a card (bank) payment
            if (paymentMethod && !paymentMethod.is_cash_count && paymentMethod.type === 'bank') {
                const cardNo = line.card_no || '';
                // Card number must be exactly 4 digits
                if (cardNo.length !== 4) {
                    return false;
                }
            }
        }
        return true;
    },

    /**
     * Override _isOrderValid to add card number validation
     */
    async _isOrderValid(isForceValidate) {
        // First check card numbers
        if (!this._checkCardNumbersValid()) {
            this.notification.add(
                _t("Please enter the last 4 digits of the card for all card payments."),
                { type: 'danger' }
            );
            return false;
        }
        
        // Then call the original validation
        return await super._isOrderValid(isForceValidate);
    },
});
