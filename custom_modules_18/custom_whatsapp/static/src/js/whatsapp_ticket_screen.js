/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.renderer = useService("renderer");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },


    /**
     * Generate receipt image for an order
     */
    async generateTicketImage(order, isBasicReceipt = false) {
        return await this.renderer.toJpeg(
            OrderReceipt,
            {
                data: this.pos.orderExportForPrinting(order),
                formatCurrency: this.env.utils.formatCurrency,
                basic_receipt: isBasicReceipt,
            },
            { addClass: "pos-receipt-print p-3" }
        );
    },

    /**
     * Send receipt via WhatsApp
     */
    async _sendReceiptOnWhatsapp(order) {
        console.log("custom_whatsapp: Starting WhatsApp send process for order", order.pos_reference || order.tracking_number);
        
        // Check if order is synced
        if (typeof order.id !== "number") {
            console.warn("custom_whatsapp: Order is not synced, cannot send via WhatsApp", order.pos_reference || order.tracking_number);
            this.dialog.add(ConfirmationDialog, {
                title: _t("Unsynced order"),
                body: _t(
                    "This order is not yet synced to server. Make sure it is synced then try again."
                ),
            });
            return Promise.reject();
        }

        // Check if WhatsApp is enabled
        if (!this.pos?.config?.whatsapp_enabled) {
            console.log("custom_whatsapp: WhatsApp is disabled in POS config, skipping send");
            return Promise.resolve();
        }

        // Get config - try from pos.config or order.config_id
        const config = this.pos?.config || order.config_id;
        const receiptTemplateId = config?.receipt_template_id;
        // Many2one fields in POS are loaded as [id, name] arrays
        const receiptTemplateIdValue = Array.isArray(receiptTemplateId) ? receiptTemplateId[0] : receiptTemplateId;
        
        console.log("custom_whatsapp: POS Config details:", {
            whatsappEnabled: config?.whatsapp_enabled,
            receiptTemplateId: receiptTemplateId,
            receiptTemplateIdType: typeof receiptTemplateId,
            receiptTemplateIdIsArray: Array.isArray(receiptTemplateId),
            receiptTemplateIdValue: receiptTemplateIdValue,
            configSource: this.pos?.config ? 'pos.config' : 'order.config_id',
            allConfigKeys: Object.keys(config || {}),
            templateRelatedKeys: Object.keys(config || {}).filter(k => k.includes('template') || k.includes('whatsapp')),
        });

        // Check if receipt template is configured
        // Note: If not found, we'll still try to send and let the server validate
        // The server will return a proper error if template is missing
        if (!receiptTemplateIdValue) {
            console.warn("custom_whatsapp: Receipt template ID not found in config data, but proceeding - server will validate");
            // Don't return early - let the server handle the validation
            // This way we get the actual server error message if template is missing
        }

        // Get customer phone number
        const partner = order.get_partner();
        const phone = partner?.mobile || partner?.phone || "";
        
        if (!phone) {
            console.log("custom_whatsapp: No phone number found for customer", partner?.name || "Unknown");
            this.notification.add(_t("WhatsApp: No phone number found for customer"), {
                type: "warning",
            });
            return Promise.resolve();
        }

        // Validate phone number format
        const phoneRegex = /^\+?[()\d\s-.]{8,18}$/;
        if (!phoneRegex.test(phone)) {
            console.warn("custom_whatsapp: Invalid phone number format", phone);
            this.notification.add(_t("WhatsApp: Invalid phone number format"), {
                type: "warning",
            });
            return Promise.resolve();
        }

        try {
            console.log("custom_whatsapp: Generating receipt images for order", order.pos_reference || order.tracking_number);
            // Generate receipt images
            const fullTicketImage = await this.generateTicketImage(order);
            const basicTicketImage = await this.generateTicketImage(order, true);
            console.log("custom_whatsapp: Receipt images generated successfully");

            console.log("custom_whatsapp: Sending receipt via WhatsApp to", phone, "for order", order.pos_reference || order.tracking_number);
            console.log("custom_whatsapp: RPC call parameters:", {
                model: "pos.order",
                method: "action_sent_receipt_on_whatsapp",
                orderId: order.id,
                phone: phone,
                hasFullImage: !!fullTicketImage,
                hasBasicImage: !!basicTicketImage,
                basicReceiptEnabled: this.pos.config.basic_receipt,
                receiptTemplateId: this.pos.config.receipt_template_id,
            });
            
            // Send via WhatsApp
            const rpcParams = [
                [order.id],
                phone,
                fullTicketImage,
                this.pos.config.basic_receipt ? basicTicketImage : null,
            ];
            console.log("custom_whatsapp: Calling RPC with params:", {
                orderIds: [order.id],
                phone: phone,
                fullImageLength: fullTicketImage?.length || 0,
                basicImageLength: (this.pos.config.basic_receipt ? basicTicketImage : null)?.length || 0,
            });
            
            await this.pos.data.call("pos.order", "action_sent_receipt_on_whatsapp", rpcParams);
            
            console.log("custom_whatsapp: ✅ Receipt successfully sent via WhatsApp to", phone, "for order", order.pos_reference || order.tracking_number);
            this.notification.add(_t("Receipt sent via WhatsApp successfully"), {
                type: "success",
            });
        } catch (error) {
            // Extract detailed error information
            let errorMessage = "Unknown error";
            let errorData = null;
            
            if (error && typeof error === "object") {
                errorMessage = error.message || error.name || String(error);
                // Try to get more details from the error object
                if (error.data) {
                    errorData = error.data;
                    errorMessage = error.data.message || error.data.debug || errorMessage;
                } else if (error.exception_type) {
                    errorMessage = `${error.exception_type}: ${error.message || errorMessage}`;
                }
                
                // Log full error object for debugging
                console.error("custom_whatsapp: Full error object:", error);
            } else if (error) {
                errorMessage = String(error);
            }
            
            console.error("custom_whatsapp: ❌ Failed to send receipt via WhatsApp from ticket screen");
            console.error("custom_whatsapp: Error message:", errorMessage);
            console.error("custom_whatsapp: Error details:", {
                order: order.pos_reference || order.tracking_number,
                orderId: order.id,
                phone: phone,
                whatsappEnabled: this.pos?.config?.whatsapp_enabled,
                receiptTemplateId: this.pos?.config?.receipt_template_id,
                error: errorMessage,
                errorData: errorData,
                fullError: error,
            });
            
            this.notification.add(_t("Failed to send receipt via WhatsApp: %s", errorMessage), {
                type: "danger",
            });
            // Don't throw error, just log it so printing still works
        }
    },

    /**
     * Handle WhatsApp button click
     */
    async onWhatsAppClick(order) {
        console.log("custom_whatsapp: Send WhatsApp button clicked for order", order?.pos_reference || order?.tracking_number);
        
        if (!order) {
            console.warn("custom_whatsapp: No order provided to WhatsApp button");
            this.notification.add(_t("Please select an order first"), {
                type: "warning",
            });
            return;
        }
        
        try {
            await this._sendReceiptOnWhatsapp(order);
        } catch (error) {
            // Error already handled in _sendReceiptOnWhatsapp
            console.error("custom_whatsapp: WhatsApp sending failed", error);
        }
    },
});

