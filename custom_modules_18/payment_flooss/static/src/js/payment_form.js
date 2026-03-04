/** @odoo-module **/

import { rpc } from '@web/core/network/rpc';
import paymentForm from '@payment/js/payment_form';

paymentForm.include({

    floossData: {},

    async _prepareInlineForm(providerId, providerCode, paymentOptionId) {
        if (providerCode !== 'flooss') {
            await this._super(...arguments);
            return;
        }

        this._hideInputs();
        this._setPaymentFlow('direct');

        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        if (radio) {
            this.inlineFormValues = JSON.parse(radio.dataset['floossInlineFormValues']);
        }

        this.selectedOptionId = paymentOptionId;

        // Get the transaction reference from the form or create one
        this.selectedTxReference = this._getTxReference();

        document.getElementById('o_flooss_button_container')?.classList.remove('d-none');
        document.getElementById('o_flooss_enabled_button')?.classList.remove('d-none');



        document.getElementById('o_flooss_enabled_button').onclick = async () => await this._floossOnClick();
    },



    async _getSelectedPhone() {
        // Ask backend for the selected order contacts
        const resp = await rpc('/payment/flooss/current_order_contact', {});

        if (resp?.error === 'no_order') {
            throw new Error("No active order found.");
        }

        // Prefer delivery phone; fall back to billing
        const phone = resp.shipping_phone || resp.billing_phone || '';
        if (!phone) {
            throw new Error("No phone number on the selected delivery/billing address.");
        }
        return phone;
    },
    _getTxReference() {
        // Try to get transaction reference from form data
        const txRefInput = document.querySelector('input[name="reference"]');
        if (txRefInput) {
            return txRefInput.value;
        }

        // Try to get from inline form values
        if (this.inlineFormValues && this.inlineFormValues.tx_reference) {
            return this.inlineFormValues.tx_reference;
        }

        // Try to get from the payment form's transaction reference
        if (this.txContext && this.txContext.reference) {
            return this.txContext.reference;
        }

        // Generate a temporary reference if none found (for testing)
        return 'FLOOSS-' + Date.now();
    },

    async _floossOnClick() {
        const { provider_id } = this.inlineFormValues;
        const phone = await this._getSelectedPhone();

        const modalEl = document.getElementById('floossOtpModal');
        if (!modalEl) return;
        const modal = new bootstrap.Modal(modalEl);
        modal.show();

        const infoBox = document.getElementById('floossOtpInfo');
        const otpInputDiv = document.querySelector('#floossOtpInput').closest('.mb-3');
        const submitBtn = document.getElementById('floossOtpSubmit');
        const tryAgainBtn = document.getElementById('floossOtpTryAgain');
        const errorBox = document.getElementById('floossOtpError');
        const proceedBtn = document.getElementById('floossProceedPayment');
        const cancelBtn = document.getElementById('floossCancelPayment');
        // Reset modal state
        infoBox.classList.add('d-none');
        otpInputDiv.classList.add('d-none');
        submitBtn.classList.add('d-none');
        tryAgainBtn.classList.add('d-none');
        errorBox.classList.add('d-none');
        proceedBtn?.classList.add('d-none');
        cancelBtn?.classList.add('d-none');

        document.getElementById('o_flooss_loading')?.classList.remove('d-none');

        const USER_EXIST = "User exists on FLOOSS. OTP has been sent to the entered mobile.";

        try {
            // Request OTP
            const otpResp = await rpc('/payment/flooss/request_otp', { provider_id, phone });

            infoBox.textContent = otpResp;
            infoBox.classList.remove('d-none');
            if (otpResp.includes(USER_EXIST)) {
                otpInputDiv.classList.remove('d-none');
                submitBtn.classList.remove('d-none');
            } else {
                otpInputDiv.classList.add('d-none');
                submitBtn.classList.add('d-none');
            }

        } catch (err) {
            this._showFloossError(err.message);
            return;
        } finally {
            document.getElementById('o_flooss_loading')?.classList.add('d-none');
        }

        // Set timeout to show "Try Again" button after 1 minute
        this.otpTimeout = setTimeout(() => {
            const tryAgainBtn = document.getElementById('floossOtpTryAgain');
            const submitBtn = document.getElementById('floossOtpSubmit');
            const infoBox = document.getElementById('floossOtpInfo');

            if (tryAgainBtn && submitBtn) {
                tryAgainBtn.classList.remove('d-none');
                submitBtn.classList.add('d-none');

                if (infoBox) {
                    infoBox.textContent = "OTP expired after 1 minute. Please request a new one.";
                    infoBox.classList.remove('d-none');
                }
            }
        }, 60000);

        // Handle Verify Pay click
        submitBtn.onclick = async () => {
            const otpValue = document.getElementById('floossOtpInput').value.trim();
            if (!otpValue) {
                this._showFloossError("Please enter the OTP");
                return;
            }
            try {
                const verifyResp = await rpc('/payment/flooss/verify_otp', {
                    provider_id,
                    phone,
                    otp: otpValue,
                    tx_reference: this.selectedTxReference,
                });

                if (verifyResp.error) throw new Error(verifyResp.error);

                // const message = verifyResp.verify?.message || "";
               const message = 'The OTP user entered has been verified.';
                if (message.includes("The OTP user entered has been verified.")) {
                    // hide verify button
                    submitBtn.classList.add('d-none');
                    // show Proceed + Cancel
                    proceedBtn.classList.remove('d-none');
                    cancelBtn.classList.remove('d-none');

                    // Proceed handler - UPDATED WITH NEW FUNCTIONALITY
                    proceedBtn.onclick = async () => {
                        try {
                            // Show loading state
                            proceedBtn.disabled = true;
                            proceedBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Processing...';

                            const payResp = await rpc('/payment/flooss/proceed_payment', {
                                provider_id,
                                phone,
                                tx_reference: this.selectedTxReference,
                            });

                            if (payResp.error) throw new Error(payResp.error);

                            this.floossData[this.selectedOptionId] = {
                                floossOrderId: payResp.payment_request?.order_id,
                                floossTxRef: payResp.payment_request?.reference,
                            };

                            this._showFloossSuccess("Payment processed successfully! Redirecting...");



                            // REDIRECT TO THE THANK YOU PAGE
                            setTimeout(() => {
                                if (payResp.redirect_url) {
                                    window.location.href = payResp.redirect_url;
                                } else {
                                    // Fallback redirect
                                    window.location.href = '/payment/thank-you';
                                }
                            }, 1000);

                        } catch (err) {
                            console.error('Payment processing error:', err);
                            this._showFloossError(err.message);
                            // Reset button state
                            proceedBtn.disabled = false;
                            proceedBtn.innerHTML = '<i class="fa fa-check me-2"></i>Proceed with Payment';
                        }
                    };
                } else {
                    this._showFloossError(message || "OTP verification failed");
                }

            } catch (err) {
                if (err.message.includes('OTP has expired')) {
                    // Show Try Again button, hide Verify
                    tryAgainBtn.classList.remove('d-none');
                    submitBtn.classList.add('d-none');
                    this._showFloossError("OTP has expired, please resend the OTP");
                } else {
                    this._showFloossError(err.message);
                }
            }
        };

        // Handle Try Again click
        tryAgainBtn.onclick = async () => {
            // Clear the existing timeout when Try Again is clicked
            if (this.otpTimeout) {
                clearTimeout(this.otpTimeout);
                this.otpTimeout = null;
            }

            tryAgainBtn.classList.add('d-none');
            submitBtn.classList.remove('d-none');
            errorBox.classList.add('d-none');
            document.getElementById('floossOtpInput').value = '';

            // Re-run OTP request
            await this._floossOnClick();
        };

        // Cancel handler
        cancelBtn.onclick = () => {
            modal.hide();
        };
    },

    _showFloossError(msg) {
        const errBox = document.getElementById('floossOtpError');
        if (errBox) {
            errBox.textContent = msg;
            errBox.classList.remove('d-none');
        }

        document.getElementById('floossOtpSuccess')?.classList.add('d-none');
        document.getElementById('floossOtpInfo')?.classList.add('d-none');

        console.error('Flooss Error:', msg);
    },

    _showFloossSuccess(msg) {
        const successBox = document.getElementById('floossOtpSuccess');
        if (successBox) {
            successBox.textContent = msg;
            successBox.classList.remove('d-none');
        }

        document.getElementById('floossOtpError')?.classList.add('d-none');
        document.getElementById('floossOtpInfo')?.classList.add('d-none');

        console.log('Flooss Success:', msg);
    }
});

// Global initialization for pages that don't go through _prepareInlineForm
document.addEventListener('DOMContentLoaded', function() {
    // Create a minimal instance to access the methods
    const floossHandler = {
        selectedTxReference: null,

        async _checkPaymentStatus() {
            const checkStatusBtn = document.getElementById('checkPaymentStatus');

            if (!checkStatusBtn) return;

            // Try to get transaction reference from sessionStorage or other sources
            this.selectedTxReference = sessionStorage.getItem('flooss_tx_reference') ||
                                     document.querySelector('input[name="reference"]')?.value ||
                                     'FLOOSS-' + Date.now();

            // Show loading state
            const originalContent = checkStatusBtn.innerHTML;
            checkStatusBtn.disabled = true;
            checkStatusBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i>Checking...';

            try {
                if (!this.selectedTxReference) {
                    this._showStatusAlert('Error: No transaction reference found', 'error');
                    return;
                }

                const response = await rpc('/payment/flooss/check_status', {});

                if (response.error) {
                    this._showStatusAlert(`Error: ${response.error}`, 'error');
                } else if (response.message) {
                    this._showStatusAlert(response.message, 'success');
                } else {
                    this._showStatusAlert('Unknown response from server', 'warning');
                }

            } catch (error) {
                console.error('Check status error:', error);
                this._showStatusAlert(`Error: ${error.message || 'Failed to check payment status'}`, 'error');
            } finally {
                // Reset button state
                checkStatusBtn.disabled = false;
                checkStatusBtn.innerHTML = originalContent;
            }
        },

        _showStatusAlert(message, type = 'info') {
            // Create and show a Bootstrap alert modal
            const alertModal = this._createStatusModal(message, type);
            alertModal.show();
        },

        _createStatusModal(message, type) {
            // Remove existing modal if any
            const existingModal = document.getElementById('paymentStatusModal');
            if (existingModal) {
                existingModal.remove();
            }

            // Create modal HTML
            const modalHtml = `
                <div class="modal fade" id="paymentStatusModal" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">
                                    <i class="fa ${this._getIconForType(type)} me-2"></i>
                                    Payment Status
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="alert alert-${this._getBootstrapTypeForAlert(type)} mb-0" role="alert">
                                    <i class="fa ${this._getIconForType(type)} me-2"></i>
                                    ${message}
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Add modal to DOM
            document.body.insertAdjacentHTML('beforeend', modalHtml);

            // Return Bootstrap modal instance
            return new bootstrap.Modal(document.getElementById('paymentStatusModal'));
        },

        _getIconForType(type) {
            const icons = {
                'success': 'fa-check-circle',
                'error': 'fa-exclamation-circle',
                'warning': 'fa-exclamation-triangle',
                'info': 'fa-info-circle'
            };
            return icons[type] || icons['info'];
        },

        _getBootstrapTypeForAlert(type) {
            const types = {
                'success': 'success',
                'error': 'danger',
                'warning': 'warning',
                'info': 'info'
            };
            return types[type] || types['info'];
        }
    };

    // Initialize the check status button if it exists
    const checkStatusBtn = document.getElementById('checkPaymentStatus');
    if (checkStatusBtn) {
        checkStatusBtn.onclick = async () => await floossHandler._checkPaymentStatus();
    }
});