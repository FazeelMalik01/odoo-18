/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.create_vehicle_register = publicWidget.Widget.extend({
    selector: '.modal_create_new_vehicle',
    events: {
        'change .vehicle_brand_id': '_onchangeBrand',
    },

    _onchangeBrand: async function(ev) {
        var self = this;
        var brand_id = $(ev.currentTarget).val();
        if (brand_id) {
            await rpc("/advance_vehicle_repair/get_vehicle_models", {
                'brand_id': brand_id
            }).then(function(models) {
                if (models.length > 0) {
                    var modelField = self.$('.vehicle_model_id');
                    modelField.empty();
                    models.forEach(function(model) {
                        modelField.append($('<option>', {
                            value: model.id,
                            text: model.name
                        }));
                    });
                } else {
                    self.$('.vehicle_model_id').empty();
                }
            });
        } else {
            self.$('.vehicle_model_id').empty();
        }
    },
});
