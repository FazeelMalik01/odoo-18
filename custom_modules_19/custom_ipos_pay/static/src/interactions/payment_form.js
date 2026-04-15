/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { rpc } from '@web/core/network/rpc';
import { PaymentForm } from '@payment/interactions/payment_form';

const IPOS_LOG = (label, data) => {
    const ts = new Date().toISOString().slice(11, 23);
    data !== undefined
        ? console.log(`[IPOS Pay ${ts}] ${label}`, data)
        : console.log(`[IPOS Pay ${ts}] ${label}`);
};
const IPOS_WARN = (label, data) => {
    const ts = new Date().toISOString().slice(11, 23);
    data !== undefined
        ? console.warn(`[IPOS Pay ${ts}] ⚠ ${label}`, data)
        : console.warn(`[IPOS Pay ${ts}] ⚠ ${label}`);
};
const IPOS_OK = (label, data) => {
    const ts = new Date().toISOString().slice(11, 23);
    data !== undefined
        ? console.log(`%c[IPOS Pay ${ts}] ✔ ${label}`, 'color:#22c55e;font-weight:bold', data)
        : console.log(`%c[IPOS Pay ${ts}] ✔ ${label}`, 'color:#22c55e;font-weight:bold');
};
const IPOS_ERROR = (label, data) => {
    const ts = new Date().toISOString().slice(11, 23);
    data !== undefined
        ? console.error(`[IPOS Pay ${ts}] ✖ ${label}`, data)
        : console.error(`[IPOS Pay ${ts}] ✖ ${label}`);
};

// Official FTD docs use id="ftd"; some builds look for "myScript".
const FTD_SCRIPT_ID = 'ftd';
const FTD_SCRIPT_ALIAS_ID = 'myScript';

patch(PaymentForm.prototype, {

    async _prepareInlineForm(providerId, providerCode, _paymentOptionId, _paymentMethodCode, _flow) {
        IPOS_LOG('_prepareInlineForm called', { providerId, providerCode, flow: _flow });

        if (providerCode === 'ipos_pay') {
            this._setPaymentFlow('direct');
            try {
                const config = await rpc('/payment/ipos_pay/get_config', { provider_id: providerId });
                IPOS_LOG('Config received', {
                    has_auth_token: !!(config?.data_token),
                    token_length: config?.data_token?.length ?? 0,
                    data_src: config?.data_src,
                    ftd_src: config?.ftd_src,
                });
                if (config?.data_token) {
                    await this._iposEnsureFtdLoaded(config.data_token, config.data_src, config.ftd_src);
                } else {
                    IPOS_WARN('No auth token in config — FTD will not be pre-loaded');
                }
            } catch (e) {
                IPOS_WARN('Pre-load failed (non-fatal, will retry on Pay click)', e.message || e);
            }
        }

        return super._prepareInlineForm(...arguments);
    },

    async _iposEnsureFtdLoaded(authToken, dataSrc, ftdSrc) {
        if (!authToken) throw new Error('IPOS Pay: Missing auth token.');
        if (!dataSrc)   throw new Error('IPOS Pay: Missing data-src.');

        const ftdScriptSrc = ftdSrc || `${dataSrc}/ftd/v1/freedomtodesign.js`;

        IPOS_LOG('_iposEnsureFtdLoaded called', {
            token_length: authToken.length,
            data_src: dataSrc,
            ftd_src: ftdScriptSrc,
            postData_ready: typeof window.postData === 'function',
            load_in_progress: !!window._iposFtdLoading,
        });

        // Re-stamp existing element if present.
        let existingScript = document.getElementById(FTD_SCRIPT_ID)
            || document.getElementById(FTD_SCRIPT_ALIAS_ID);
        if (existingScript) {
            existingScript.setAttribute('security_key', authToken);
            existingScript.setAttribute('data-src', dataSrc);
            if (typeof window.postData === 'function') {
                IPOS_OK('FTD already loaded — attributes re-stamped');
                return;
            }
        }

        if (window._iposFtdLoading) {
            IPOS_WARN('FTD load in progress — awaiting');
            await window._iposFtdLoading;
            if (typeof window.postData !== 'function') {
                throw new Error('IPOS Pay: FTD loaded but postData() not defined.');
            }
            return;
        }

        IPOS_LOG('Creating FTD script element — setting all attrs before append');

        const script = document.createElement('script');
        // Primary id follows official docs.
        script.id = FTD_SCRIPT_ID;
        script.setAttribute('security_key', authToken);
        script.setAttribute('data-src', dataSrc);
        script.async = false;               // ensures document.currentScript is set
        script.src = ftdScriptSrc;          // set src BEFORE appendChild (canonical)

        IPOS_LOG('Script element ready (before append)', {
            id: script.id,
            security_key: script.getAttribute('security_key') ? '(set)' : '(MISSING)',
            'data-src': script.getAttribute('data-src'),
            src: script.src,
            async: script.async,
        });

        window._iposFtdLoading = new Promise((resolve, reject) => {
            script.addEventListener('load', () => {
                IPOS_OK('freedomtodesign.js loaded', {
                    postData: typeof window.postData === 'function' ? '✔' : '✖ MISSING',
                    currentScript_at_load: 'N/A (checked after load event)',
                });
                window._iposFtdLoading = null;
                resolve();
            }, { once: true });
            script.addEventListener('error', () => {
                IPOS_ERROR('freedomtodesign.js failed to load');
                window._iposFtdLoading = null;
                reject(new Error('IPOS Pay: Failed to load freedomtodesign.js.'));
            }, { once: true });
        });

        document.head.appendChild(script);  // triggers fetch (src already set)
        IPOS_LOG('Script appended to <head>', { in_dom: document.head.contains(script) });

        // Keep alias marker in sync for builds that query `myScript`.
        let aliasScript = document.getElementById(FTD_SCRIPT_ALIAS_ID);
        if (!aliasScript) {
            aliasScript = document.createElement('script');
            aliasScript.id = FTD_SCRIPT_ALIAS_ID;
            aliasScript.type = 'text/plain';
            document.head.appendChild(aliasScript);
        }
        aliasScript.setAttribute('security_key', authToken);
        aliasScript.setAttribute('data-src', dataSrc);
        aliasScript.setAttribute('src', ftdScriptSrc);

        await window._iposFtdLoading;

        if (typeof window.postData !== 'function') {
            throw new Error('IPOS Pay: freedomtodesign.js loaded but postData() not defined.');
        }
        IPOS_OK('FTD fully ready');
    },

    async _processDirectFlow(providerCode, _paymentOptionId, _paymentMethodCode, processingValues) {
        IPOS_LOG('_processDirectFlow called', {
            providerCode,
            reference: processingValues?.reference,
            has_security_key: !!(processingValues?.ipos_security_key),
        });

        if (providerCode !== 'ipos_pay') {
            return super._processDirectFlow(...arguments);
        }

        try {
            // Ensure FTD loaded and security_key is fresh.
            let script = document.getElementById(FTD_SCRIPT_ID)
                || document.getElementById(FTD_SCRIPT_ALIAS_ID);
            if (!script || !script.getAttribute('security_key')) {
                IPOS_WARN('ftd/myScript missing or key absent — fetching config');
                const config = await rpc('/payment/ipos_pay/get_config', {
                    provider_id: this.paymentContext.providerId,
                });
                await this._iposEnsureFtdLoaded(config.data_token, config.data_src, config.ftd_src);
                script = document.getElementById(FTD_SCRIPT_ID)
                    || document.getElementById(FTD_SCRIPT_ALIAS_ID);
            } else {
                script.setAttribute('security_key', processingValues.ipos_security_key);
                const aliasScript = document.getElementById(FTD_SCRIPT_ALIAS_ID);
                if (aliasScript) {
                    aliasScript.setAttribute('security_key', processingValues.ipos_security_key);
                }
            }

            IPOS_LOG('DOM state before postData()', {
                marker_exists: !!script,
                security_key: script?.getAttribute('security_key') ? '(set)' : '(MISSING!)',
                'data-src': script?.getAttribute('data-src') || '(MISSING!)',
                src: script?.getAttribute('src') || '(none)',
                postData: typeof window.postData,
            });

            // ── getElementById interceptor ─────────────────────────────────
            // Intercept FTD's getElementById call to see exactly what it finds.
            const _origGetById = Document.prototype.getElementById;
            Document.prototype.getElementById = function(id) {
                const result = _origGetById.call(this, id);
                IPOS_LOG(`[INTERCEPT] getElementById('${id}') from FTD`, {
                    result: result ? `<${result.tagName} id="${result.id}" security_key="${result.getAttribute('security_key') || '(none)'}">` : 'NULL',
                    document_url: this.URL,
                });
                return result;
            };

            IPOS_LOG('Calling window.postData() ...');

            const tokenData = await new Promise((resolve, reject) => {
                try {
                    const ret = window.postData((data) => {
                        IPOS_LOG('postData callback fired', { keys: data ? Object.keys(data) : [] });
                        resolve(data);
                    });
                    if (ret && typeof ret.then === 'function') {
                        IPOS_LOG('postData returned a Promise — racing it');
                        ret.then(resolve, reject);
                    }
                } catch (e) {
                    reject(e);
                }
            }).finally(() => {
                // Restore getElementById
                Document.prototype.getElementById = _origGetById;
                IPOS_LOG('getElementById interceptor removed');
            });

            IPOS_LOG('tokenData received', { keys: tokenData ? Object.keys(tokenData) : [] });

            const paymentToken = (
                tokenData?.payment_token_id
                || tokenData?.paymentTokenId
                || tokenData?.cardToken
                || tokenData?.payment_token
                || tokenData?.token
            );

            if (!paymentToken) {
                IPOS_ERROR('No token in tokenData', tokenData);
                throw new Error('IPOS Pay: Card token was not returned by FTD.');
            }

            IPOS_OK('Token extracted', { length: paymentToken.length });

            const result = await rpc(processingValues.ipos_charge_route, {
                reference: processingValues.reference,
                payment_token_id: paymentToken,
                access_token: this.paymentContext['accessToken'],
            });

            IPOS_LOG('Charge result', { state: result?.state, message: result?.message });

            if (result?.state === 'done') {
                IPOS_OK('Payment done — redirecting');
                window.location = result.landing_route || '/shop/payment/validate';
                return;
            }

            IPOS_ERROR('Charge returned non-done state', result);
            this._displayErrorDialog('Payment processing failed', result?.message || 'IPOS transaction failed.');
            this._enableButton();

        } catch (error) {
            IPOS_ERROR('_processDirectFlow error', { message: error?.message, stack: error?.stack });
            this._displayErrorDialog('Payment processing failed', error?.message || 'IPOS direct flow failed.');
            this._enableButton();
        }
    },
});
