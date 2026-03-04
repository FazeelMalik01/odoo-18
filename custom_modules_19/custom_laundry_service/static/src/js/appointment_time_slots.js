// Handle dynamic time slot loading based on selected date
(function () {
    'use strict';

    function initTimeSlotSelector() {
        const dateInput = document.getElementById('appointment_date');
        const slotSelect = document.getElementById('time_slot_id');
        const loadingText = document.getElementById('slot_loading_text');

        if (!dateInput || !slotSelect) {
            return; // Not on the booking form page
        }

        // Handle date change
        dateInput.addEventListener('change', function () {
            const selectedDate = this.value;

            if (!selectedDate) {
                // No date selected, disable slot selector
                slotSelect.disabled = true;
                slotSelect.innerHTML = '<option value="">Select a date first...</option>';
                return;
            }

            // Show loading state
            slotSelect.disabled = true;
            slotSelect.innerHTML = '<option value="">Loading...</option>';
            if (loadingText) {
                loadingText.style.display = 'block';
            }

            // Get appointment_id from hidden input if editing
            const appointmentIdInput = document.querySelector('input[name="id"]');
            let appointmentId = null;
            if (appointmentIdInput && appointmentIdInput.value) {
                const parsedId = parseInt(appointmentIdInput.value);
                if (!isNaN(parsedId)) {
                    appointmentId = parsedId;
                }
            }
            
            // Get zip_code from the form (it might be readonly/disabled, so check hidden input or select)
            let zipCode = null;
            const zipCodeSelect = document.getElementById('zip_code');
            const zipCodeHidden = document.querySelector('input[name="zip_code"][type="hidden"]');
            if (zipCodeSelect && !zipCodeSelect.disabled && zipCodeSelect.value) {
                zipCode = zipCodeSelect.value;
            } else if (zipCodeHidden && zipCodeHidden.value) {
                zipCode = zipCodeHidden.value;
            }
            
            // Prepare JSON-RPC request params
            const params = {
                date: selectedDate
            };
            if (appointmentId) {
                params.appointment_id = appointmentId;
            }
            if (zipCode) {
                params.zip_code = zipCode;
            }
            
            const jsonRpcRequest = {
                jsonrpc: '2.0',
                method: 'call',
                params: params,
                id: Math.floor(Math.random() * 1000000000)
            };

            // Fetch available slots
            fetch('/my/appointments/get_available_slots', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(jsonRpcRequest)
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok: ' + response.status);
                    }
                    return response.json();
                })
                .then(data => {
                    // Hide loading state
                    if (loadingText) {
                        loadingText.style.display = 'none';
                    }

                    // Handle JSON-RPC response format
                    if (data.error) {
                        console.error('Error loading slots:', data.error);
                        slotSelect.innerHTML = '<option value="">Error loading slots. Please try again.</option>';
                        return;
                    }

                    const result = data.result || {};
                    const slots = result.slots || [];

                    // Clear and populate slot selector
                    slotSelect.innerHTML = '';

                    if (slots.length === 0) {
                        slotSelect.innerHTML = '<option value="">No available slots for this date</option>';
                        slotSelect.disabled = true;
                    } else {
                        // Add placeholder option
                        const placeholderOption = document.createElement('option');
                        placeholderOption.value = '';
                        placeholderOption.textContent = 'Select a time slot...';
                        slotSelect.appendChild(placeholderOption);

                        // Add slot options
                        slots.forEach(slot => {
                            const option = document.createElement('option');
                            option.value = slot.id;
                            option.textContent = slot.time_range;
                            slotSelect.appendChild(option);
                        });

                        slotSelect.disabled = false;
                    }
                })
                .catch(error => {
                    console.error('Error loading time slots:', error);
                    if (loadingText) {
                        loadingText.style.display = 'none';
                    }
                    slotSelect.innerHTML = '<option value="">Error loading slots. Please try again.</option>';
                    slotSelect.disabled = true;
                });
        });

        // If editing an appointment with a pre-selected date, trigger slot loading
        if (dateInput.value) {
            // Store the selected slot ID before triggering change
            const selectedSlotId = slotSelect.getAttribute('data-selected-slot-id') ||
                slotSelect.value ||
                slotSelect.dataset.initialValue;

            // Trigger change to load slots
            const changeEvent = new Event('change');
            dateInput.dispatchEvent(changeEvent);

            // After slots are loaded, restore the selected value
            if (selectedSlotId) {
                // Wait a bit for the async load to complete
                setTimeout(() => {
                    const optionToSelect = slotSelect.querySelector(`option[value="${selectedSlotId}"]`);
                    if (optionToSelect) {
                        slotSelect.value = selectedSlotId;
                    }
                }, 500);
            }
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTimeSlotSelector);
    } else {
        initTimeSlotSelector();
    }
})();
