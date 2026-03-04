/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.create_vehicle_booking = publicWidget.Widget.extend({
    selector: '.modal_create_new_booking',
    events: {
            'change .booking_date': '_onchangeBookingDate',
        },

    _onchangeBookingDate: async function(ev) {
            var self = this;
            var bookingDate = $(ev.currentTarget).val();
            if (bookingDate) {
                var dayOfWeek = new Date(bookingDate).toLocaleString('en-US', { weekday: 'long' });
                console.log("hello")
                console.log("dayOfWeek",dayOfWeek)

                await rpc("/advance_vehicle_repair/get_vehicle_appointments", {
                    'dayOfWeek': dayOfWeek
                }).then(async function(appointments) {
                    if (appointments.length > 0) {
                        var appointmentId = appointments[0].id;
                        await rpc("/advance_vehicle_repair/get_appointments_slot", {
                            'appointmentId': appointmentId
                        }).then(function(slots) {
                            var availableSlotField = self.$('.available_slot');
                            availableSlotField.empty();
                            slots.forEach(function(slot) {
                                availableSlotField.append($('<option>', {
                                    value: slot.id,
                                    text: slot.time_slot
                                }));
                            });

                        });
                    } else {
                        self.$('.available_slot').empty();
                    }
                });
            } else {
                self.$('.available_slot').empty();
            }
    },
});

