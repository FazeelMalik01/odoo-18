import { patch } from "@web/core/utils/patch";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";

// Extend OrderWidget to accept customer prop
patch(OrderWidget, {
    props: {
        ...OrderWidget.props,
        customer: { type: Object, optional: true },
    },
});

