console.log('timer.js loaded');

(function() {
    'use strict';

    function initTimer() {
        const timerContainer = document.querySelector('.timer-container');
        if (!timerContainer) {
            console.log('Timer container not found');
            return;
        }

        // Get data attributes
        const taskId = timerContainer.getAttribute('data-task-id');
        const timerHours = timerContainer.getAttribute('data-timer-hours');
        const initialTimerHours = parseFloat(timerHours) || 0;
        const elapsedSeconds = parseInt(timerContainer.getAttribute('data-elapsed-seconds')) || 0;
        const timerStartTime = timerContainer.getAttribute('data-timer-start') || '';
        const timerRunning = timerContainer.getAttribute('data-timer-running');
        const isTimerRunning = timerRunning === 'true';

        // Get DOM elements
        const timerDisplay = document.getElementById('current-timer-display');
        const timerStatus = document.getElementById('timer-status');
        const totalTimerInput = document.getElementById('total-timer-hours');
        const startBtn = document.getElementById('timer-start-btn');
        const stopBtn = document.getElementById('timer-stop-btn');
        const resetBtn = document.getElementById('timer-reset-btn');
        const workOrderForm = document.getElementById('work-order-form');

        if (!taskId || !timerDisplay || !startBtn || !stopBtn || !resetBtn) {
            console.error('Timer elements not found', {
                taskId: !!taskId,
                timerDisplay: !!timerDisplay,
                startBtn: !!startBtn,
                stopBtn: !!stopBtn,
                resetBtn: !!resetBtn
            });
            return;
        }

        let intervalId = null;
        let sessionStartTime = null;
        let currentTimerHours = initialTimerHours;
        let isTimerStopped = false; // Flag to prevent interval callbacks from updating after stop
        let isSavingTimesheet = false; // Flag to prevent multiple timesheet saves

        console.log('Timer initialized:', {
            taskId: taskId,
            initialTimerHours: initialTimerHours,
            timerStartTime: timerStartTime,
            isTimerRunning: isTimerRunning
        });

        /**
         * Convert decimal hours to HH:MM:SS format
         */
        function formatTime(hours) {
            const totalSeconds = Math.floor(hours * 3600);
            const h = Math.floor(totalSeconds / 3600);
            const m = Math.floor((totalSeconds % 3600) / 60);
            const s = totalSeconds % 60;
            
            // Format with leading zeros
            const hh = String(h).padStart(2, '0');
            const mm = String(m).padStart(2, '0');
            const ss = String(s).padStart(2, '0');
            
            return hh + ':' + mm + ':' + ss;
        }

        // Initialize timer state
        console.log('Initializing timer state:', {
            isTimerRunning: isTimerRunning,
            timerStartTime: timerStartTime,
            elapsedSeconds: elapsedSeconds,
            initialTimerHours: initialTimerHours,
            formatted: formatTime(initialTimerHours),
            timerRunningAttr: timerRunning,
            timerStartTimeAttr: timerStartTime
        });
        
        // Check if timer is running - be more lenient with the check
        const timerIsRunning = isTimerRunning || (timerRunning === 'True') || (timerRunning === true);
        const hasTimerStart = timerStartTime && timerStartTime !== '' && timerStartTime !== 'False';
        
        console.log('Timer state check:', {
            timerIsRunning: timerIsRunning,
            hasTimerStart: hasTimerStart,
            timerStartTime: timerStartTime
        });
        
        if (timerIsRunning && hasTimerStart) {
            // Timer is already running on server - continue from server state
            console.log('Timer was running on server, continuing from server state...');
            
            // Use the server's computed timer_hours as the base
            // This already includes elapsed_seconds + current running session time
            // We'll use this as our starting point and continue from now
            const serverTimerHours = initialTimerHours;
            
            // Parse server timer_start correctly
            // Server sends datetime in format "YYYY-MM-DD HH:MM:SS" (UTC timezone)
            // We need to parse it as UTC to avoid timezone offset issues
            let serverStartTime = null;
            try {
                // Odoo datetime format: "YYYY-MM-DD HH:MM:SS" (UTC)
                // Parse it as UTC by appending 'Z' and converting to ISO format
                if (timerStartTime.includes('T')) {
                    // Already ISO format
                    serverStartTime = new Date(timerStartTime);
                } else {
                    // Server format: "YYYY-MM-DD HH:MM:SS" - treat as UTC
                    // Convert to ISO format: "YYYY-MM-DDTHH:MM:SSZ"
                    const isoStr = timerStartTime.replace(' ', 'T') + 'Z';
                    serverStartTime = new Date(isoStr);
                }
                
                if (isNaN(serverStartTime.getTime())) {
                    console.error('Invalid timer start time:', timerStartTime);
                    serverStartTime = new Date(); // Fallback
                }
            } catch (e) {
                console.error('Error parsing timer start time:', e);
                serverStartTime = new Date(); // Fallback
            }
            
            // Use elapsed_seconds as the base (previous sessions only)
            // This doesn't include the current running session
            const baseAllocatedHours = elapsedSeconds / 3600.0;
            currentTimerHours = baseAllocatedHours;
            
            // Set sessionStartTime to the parsed server time
            // This will be used to calculate elapsed time from current session
            sessionStartTime = serverStartTime;
            
            console.log('Timer continuation details:', {
                elapsedSeconds: elapsedSeconds,
                baseAllocatedHours: baseAllocatedHours,
                serverTimerHours: serverTimerHours,
                timerStartTime: timerStartTime,
                serverStartTime: serverStartTime,
                serverStartTimeUTC: serverStartTime.toISOString(),
                nowUTC: new Date().toISOString(),
                timeDiffMs: new Date() - serverStartTime,
                timeDiffHours: (new Date() - serverStartTime) / (1000 * 60 * 60),
                note: 'Using elapsed_seconds as base, calculating current session from serverStartTime'
            });
            
            // Update display immediately with current calculated time
            updateTimerDisplay();
            
            // Start the timer display (will calculate from base + elapsed time from sessionStartTime)
            startTimerDisplay();
            updateButtonStates(true);
            updateTimerStatus('running');
            
            // Initialize total allocated hours field - it will update in real-time
            // The updateTimerDisplay() call above will handle this, so we don't need to set it here
        } else {
            // Timer is stopped - show accumulated time (should NOT be 0 unless reset)
            // Use elapsed_seconds as the accumulated time (this is what's stored on server)
            // This ensures we preserve the time even if allocated_hours computed field is 0
            const accumulatedHours = elapsedSeconds / 3600.0;
            
            // Use elapsed_seconds as the accumulated time
            currentTimerHours = accumulatedHours;
            
            console.log('Timer is stopped, showing accumulated time:', {
                elapsedSeconds: elapsedSeconds,
                accumulatedHours: accumulatedHours,
                initialTimerHours: initialTimerHours,
                currentTimerHours: currentTimerHours,
                note: 'Preserving accumulated time from server'
            });
            
            updateTimerDisplay(currentTimerHours);
            updateButtonStates(false);
            updateTimerStatus('stopped');
            // Initialize total timer hours field with formatted time
            if (totalTimerInput) {
                totalTimerInput.value = formatTime(currentTimerHours);
            }
        }

        // Event listeners
        startBtn.addEventListener('click', function(e) {
            e.preventDefault();
            startTimer();
        });

        stopBtn.addEventListener('click', function(e) {
            e.preventDefault();
            stopTimer();
        });

        resetBtn.addEventListener('click', function(e) {
            e.preventDefault();
            resetTimer();
        });

        // Intercept form submit to save timesheet before submitting
        // Use a flag to ensure we only attach the listener once
        if (workOrderForm && !workOrderForm.hasAttribute('data-timer-handler-attached')) {
            // Mark that we've attached the handler
            workOrderForm.setAttribute('data-timer-handler-attached', 'true');
            
            // Use a named function so we can remove it if needed
            function formSubmitHandler(e) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                
                // Prevent multiple submissions
                if (isSavingTimesheet) {
                    console.log('Timesheet save already in progress, ignoring duplicate submit');
                    return false;
                }
                
                // Disable the form submit button to prevent double-clicks
                const submitButton = workOrderForm.querySelector('button[type="submit"]');
                if (submitButton) {
                    if (submitButton.disabled) {
                        console.log('Submit button already disabled, ignoring duplicate submit');
                        return false;
                    }
                    submitButton.disabled = true;
                    const originalText = submitButton.innerHTML;
                    submitButton.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i> Saving...';
                }
                
                // Disable the entire form to prevent multiple submissions
                workOrderForm.style.pointerEvents = 'none';
                
                // Save timesheet first, then submit form
                saveTimerAndSubmit(formSubmitHandler);
                
                return false;
            }
            
            workOrderForm.addEventListener('submit', formSubmitHandler, { once: false });
            console.log('Form submit handler attached');
        }

        function startTimer() {
            if (intervalId) return; // Already running

            const csrfToken = getCsrfToken();
            fetch('/my/gate_lock_assigned/timer_action', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: new URLSearchParams({
                    'csrf_token': csrfToken,
                    'task_id': taskId,
                    'action': 'start'
                })
            })
            .then(function(response) {
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return response.json();
                }
                return response.text().then(function() { return {}; });
            })
            .then(function(data) {
                // When starting, use elapsed_seconds as base (previous sessions only)
                // The server's timer_hours includes the new session, so we need to extract base
                if (data && data.elapsed_seconds !== undefined) {
                    // Use elapsed_seconds as base (without current session)
                    currentTimerHours = (data.elapsed_seconds || 0) / 3600.0;
                } else if (data && data.timer_hours !== undefined) {
                    // Fallback: use timer_hours but this includes current session
                    // We'll use it as base and sessionStartTime will add the elapsed time
                    currentTimerHours = data.timer_hours;
                }
                
                // Set session start time to now (when this session started)
                sessionStartTime = new Date();
                
                console.log('Timer started. Base timer hours (from elapsed_seconds):', currentTimerHours, 'Session started at:', sessionStartTime, 'elapsed_seconds from server:', data ? data.elapsed_seconds : 'N/A');
                
                startTimerDisplay();
                updateButtonStates(true);
                updateTimerStatus('running');
            })
            .catch(function(error) {
                console.error('Error starting timer:', error);
            });
        }

        function stopTimer() {
            console.log('=== STOP TIMER CALLED ===');
            console.log('Initial state:', {
                intervalId: intervalId,
                sessionStartTime: sessionStartTime,
                currentTimerHours: currentTimerHours,
                isTimerStopped: isTimerStopped
            });
            
            if (!intervalId && !sessionStartTime) {
                console.log('Timer not running, returning early');
                return; // Not running
            }

            // CRITICAL: Stop the display interval FIRST to prevent any further updates
            console.log('Stopping timer display...');
            stopTimerDisplay();
            console.log('After stopTimerDisplay:', {
                intervalId: intervalId,
                isTimerStopped: isTimerStopped
            });
            
            // Calculate accumulated time IMMEDIATELY after stopping display
            // currentTimerHours is the base (from previous sessions)
            // We need to add the current session time
            let calculatedAccumulatedHours = currentTimerHours;
            if (sessionStartTime) {
                const now = new Date();
                const elapsedMs = now - sessionStartTime;
                const elapsedHours = elapsedMs / (1000 * 60 * 60);
                calculatedAccumulatedHours = currentTimerHours + elapsedHours;
                
                console.log('=== STOP CALCULATION ===');
                console.log('currentTimerHours (base):', currentTimerHours, 'hours =', formatTime(currentTimerHours));
                console.log('sessionStartTime:', sessionStartTime, 'ISO:', sessionStartTime.toISOString());
                console.log('now:', now, 'ISO:', now.toISOString());
                console.log('elapsedMs:', elapsedMs, 'milliseconds');
                console.log('elapsedHours:', elapsedHours, 'hours =', formatTime(elapsedHours));
                console.log('calculatedAccumulatedHours:', calculatedAccumulatedHours, 'hours =', formatTime(calculatedAccumulatedHours));
                console.log('Calculation: currentTimerHours + elapsedHours =', currentTimerHours, '+', elapsedHours, '=', calculatedAccumulatedHours);
            } else {
                console.log('No sessionStartTime, using currentTimerHours only:', currentTimerHours);
            }
            
            // Clear sessionStartTime IMMEDIATELY to prevent any display calculations from using it
            sessionStartTime = null;
            console.log('Cleared sessionStartTime, now:', sessionStartTime);
            
            // Update currentTimerHours immediately with calculated value
            const previousCurrentTimerHours = currentTimerHours;
            currentTimerHours = calculatedAccumulatedHours;
            console.log('Updated currentTimerHours:', previousCurrentTimerHours, '->', currentTimerHours);
            
            // Update display immediately with the exact calculated time
            console.log('Updating display with calculated time:', calculatedAccumulatedHours);
            updateTimerDisplay(calculatedAccumulatedHours);
            
            console.log('=== AFTER INITIAL STOP ===');
            console.log('calculatedAccumulatedHours:', calculatedAccumulatedHours, 'Formatted:', formatTime(calculatedAccumulatedHours));
            console.log('currentTimerHours:', currentTimerHours, 'Formatted:', formatTime(currentTimerHours));
            console.log('Display should show:', formatTime(calculatedAccumulatedHours));

            const csrfToken = getCsrfToken();
            fetch('/my/gate_lock_assigned/timer_action', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: new URLSearchParams({
                    'csrf_token': csrfToken,
                    'task_id': taskId,
                    'action': 'stop'
                })
            })
            .then(function(response) {
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return response.json();
                }
                // If not JSON, use calculated value
                return response.text().then(function() { 
                    return { timer_hours: calculatedAccumulatedHours }; 
                });
            })
            .then(function(data) {
                console.log('=== SERVER RESPONSE RECEIVED ===');
                console.log('Server response data:', data);
                console.log('Client calculated value:', calculatedAccumulatedHours, 'Formatted:', formatTime(calculatedAccumulatedHours));
                
                // Timer display and sessionStartTime are already stopped/cleared above
                // Use server value as source of truth (it's always correct)
                let finalAccumulatedHours = calculatedAccumulatedHours;
                
                // ALWAYS use server value if available (server is source of truth)
                if (data && data.timer_hours !== undefined && data.timer_hours !== null) {
                    const serverHours = data.timer_hours;
                    finalAccumulatedHours = serverHours;
                    const previousCurrentTimerHours = currentTimerHours;
                    currentTimerHours = finalAccumulatedHours;
                    console.log('=== USING SERVER VALUE ===');
                    console.log('Server timer_hours:', serverHours, 'Formatted:', formatTime(serverHours));
                    console.log('Client calculated was:', calculatedAccumulatedHours, 'Formatted:', formatTime(calculatedAccumulatedHours));
                    console.log('Difference:', (serverHours - calculatedAccumulatedHours) * 3600, 'seconds');
                    console.log('Updated currentTimerHours:', previousCurrentTimerHours, '->', currentTimerHours);
                } else if (data && data.elapsed_seconds !== undefined) {
                    // Fallback: use elapsed_seconds from server
                    finalAccumulatedHours = (data.elapsed_seconds || 0) / 3600.0;
                    const previousCurrentTimerHours = currentTimerHours;
                    currentTimerHours = finalAccumulatedHours;
                    console.log('=== USING ELAPSED_SECONDS FROM SERVER ===');
                    console.log('Server elapsed_seconds:', data.elapsed_seconds);
                    console.log('Converted to hours:', finalAccumulatedHours, 'Formatted:', formatTime(finalAccumulatedHours));
                    console.log('Updated currentTimerHours:', previousCurrentTimerHours, '->', currentTimerHours);
                } else {
                    // No server data, use client calculation
                    console.warn('=== NO SERVER DATA, USING CLIENT CALCULATION ===');
                    console.warn('No server data available, using client calculation:', calculatedAccumulatedHours);
                }
                
                console.log('=== BEFORE DISPLAY UPDATE ===');
                console.log('finalAccumulatedHours:', finalAccumulatedHours, 'Formatted:', formatTime(finalAccumulatedHours));
                console.log('currentTimerHours:', currentTimerHours, 'Formatted:', formatTime(currentTimerHours));
                console.log('sessionStartTime:', sessionStartTime);
                console.log('intervalId:', intervalId);
                console.log('isTimerStopped:', isTimerStopped);
                
                // Update display with the final accumulated time (sessionStartTime is already null)
                // This ensures the display shows the correct stopped time
                updateTimerDisplay(finalAccumulatedHours);
                
                // Check what the display actually shows
                if (timerDisplay) {
                    console.log('Display element textContent after update:', timerDisplay.textContent);
                }
                
                // Update total timer hours field
                if (totalTimerInput) {
                    totalTimerInput.value = formatTime(finalAccumulatedHours);
                    console.log('Total timer input value set to:', totalTimerInput.value);
                }
                
                // Update UI state
                updateButtonStates(false);
                updateTimerStatus('stopped');
                
                console.log('=== FINAL STATE AFTER STOP ===');
                console.log('finalAccumulatedHours:', finalAccumulatedHours, 'Formatted:', formatTime(finalAccumulatedHours));
                console.log('currentTimerHours:', currentTimerHours, 'Formatted:', formatTime(currentTimerHours));
                console.log('Display shows:', timerDisplay ? timerDisplay.textContent : 'N/A');
                console.log('Total timer input shows:', totalTimerInput ? totalTimerInput.value : 'N/A');
            })
            .catch(function(error) {
                console.error('Error stopping timer:', error);
                // Still stop the display even on error
                stopTimerDisplay();
                sessionStartTime = null;
                updateButtonStates(false);
                updateTimerStatus('stopped');
            });
        }

        function resetTimer() {
            if (confirm('Are you sure you want to reset the timer? This will clear all recorded time.')) {
                const csrfToken = getCsrfToken();
                fetch('/my/gate_lock_assigned/timer_action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: new URLSearchParams({
                        'csrf_token': csrfToken,
                        'task_id': taskId,
                        'action': 'reset'
                    })
                })
                .then(function(response) {
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        return response.json();
                    }
                    return response.text().then(function() { return {}; });
                })
                .then(function(data) {
                    stopTimerDisplay();
                    updateTimerDisplay(0);
                    updateButtonStates(false);
                    updateTimerStatus('stopped');
                    currentTimerHours = 0;
                    if (totalTimerInput) {
                        totalTimerInput.value = '00:00:00';
                    }
                    setTimeout(function() {
                        window.location.reload();
                    }, 500);
                })
                .catch(function(error) {
                    console.error('Error resetting timer:', error);
                    setTimeout(function() {
                        window.location.reload();
                    }, 500);
                });
            }
        }

        function saveTimerAndSubmit(formSubmitHandler) {
            const saveId = Date.now() + '-' + Math.random().toString(36).substr(2, 9);
            console.log(`=== SAVE TIMESHEET CALLED [ID: ${saveId}] ===`);
            console.log(`Current isSavingTimesheet flag:`, isSavingTimesheet);
            console.log(`Stack trace:`, new Error().stack);
            
            // Prevent multiple simultaneous saves
            if (isSavingTimesheet) {
                console.warn(`[${saveId}] Timesheet save already in progress, skipping duplicate call`);
                // Still submit the form even if timesheet save is in progress
                // Calculate timer hours before submitting
                let timerTime = currentTimerHours;
                if (sessionStartTime) {
                    const now = new Date();
                    const elapsedMs = now - sessionStartTime;
                    const elapsedHours = elapsedMs / (1000 * 60 * 60);
                    timerTime = currentTimerHours + elapsedHours;
                }
                submitForm(formSubmitHandler, timerTime);
                return;
            }
            
            // Set flag to prevent multiple saves
            isSavingTimesheet = true;
            console.log(`[${saveId}] Flag set: isSavingTimesheet = true`);
            console.log(`[${saveId}] === SAVE TIMESHEET STARTED ===`);
            
            // Stop timer display first to get accurate final time
            stopTimerDisplay();
            
            // Calculate current timer time (including running session if any)
            // This must be done AFTER stopping the display to get the final value
            // CRITICAL: Capture this value BEFORE resetting timer - we'll use it for worksheet
            let timerTime = currentTimerHours;
            if (sessionStartTime) {
                const now = new Date();
                const elapsedMs = now - sessionStartTime;
                const elapsedHours = elapsedMs / (1000 * 60 * 60);
                timerTime = currentTimerHours + elapsedHours;
            }
            
            // Store the timer hours value BEFORE resetting - this will be used in worksheet
            const finalTimerHoursForWorksheet = timerTime;
            console.log(`[${saveId}] Captured timer hours for worksheet BEFORE reset:`, finalTimerHoursForWorksheet, 'Formatted:', formatTime(finalTimerHoursForWorksheet));

            console.log(`[${saveId}] Timer calculation:`, {
                currentTimerHours: currentTimerHours,
                sessionStartTime: sessionStartTime,
                calculatedTime: timerTime,
                formatted: formatTime(timerTime)
            });

            // Get work notes from textarea
            const workNotesTextarea = document.querySelector('textarea[name="work_notes"]');
            const description = workNotesTextarea ? (workNotesTextarea.value || 'Timer session') : 'Timer session';

            console.log(`[${saveId}] Description from work notes:`, description);

            // If there's timer time, save it first
            if (timerTime > 0) {
                const csrfToken = getCsrfToken();
                const requestBody = {
                    'csrf_token': csrfToken,
                    'task_id': taskId,
                    'hours': timerTime,
                    'description': description
                };
                
                console.log(`[${saveId}] Sending timesheet save request:`, {
                    url: '/my/gate_lock_assigned/timer_save',
                    method: 'POST',
                    body: requestBody,
                    timestamp: new Date().toISOString()
                });
                
                fetch('/my/gate_lock_assigned/timer_save', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: new URLSearchParams(requestBody)
                })
                .then(function(response) {
                    console.log(`[${saveId}] Server response received:`, {
                        status: response.status,
                        statusText: response.statusText,
                        contentType: response.headers.get('content-type'),
                        timestamp: new Date().toISOString()
                    });
                    
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        return response.json();
                    }
                    return response.text().then(function(text) { 
                        console.log(`[${saveId}] Non-JSON response:`, text);
                        return { success: true }; 
                    });
                })
                .then(function(data) {
                    console.log(`[${saveId}] Timesheet save response data:`, data);
                    console.log(`[${saveId}] Response timestamp:`, new Date().toISOString());
                    
                    // Reset timer on client side immediately
                    resetTimerClientSide();
                    // Reset timer on server side
                    return resetTimerAfterSave();
                })
                .then(function() {
                    // Clear the saving flag before submitting form
                    isSavingTimesheet = false;
                    console.log(`[${saveId}] Flag cleared: isSavingTimesheet = false`);
                    console.log(`[${saveId}] === TIMESHEET SAVE COMPLETE, SUBMITTING FORM ===`);
                    // Submit the form after timer is reset, passing the captured timer hours
                    submitForm(formSubmitHandler, finalTimerHoursForWorksheet);
                })
                .catch(function(error) {
                    console.error(`[${saveId}] Error saving timer:`, error);
                    console.error(`[${saveId}] Error stack:`, error.stack);
                    // Clear the saving flag even on error
                    isSavingTimesheet = false;
                    console.log(`[${saveId}] Flag cleared on error: isSavingTimesheet = false`);
                    // Still reset timer and submit form even if timesheet save fails
                    resetTimerClientSide();
                    resetTimerAfterSave().then(function() {
                        submitForm(formSubmitHandler, finalTimerHoursForWorksheet);
                    });
                });
            } else {
                // No timer time, just submit the form
                console.log('No timer time to save, submitting form directly');
                isSavingTimesheet = false;
                submitForm(formSubmitHandler, 0.0);
            }
        }

        function resetTimerClientSide() {
            // Reset timer on client side immediately (synchronously)
            stopTimerDisplay();
            updateTimerDisplay(0);
            updateButtonStates(false);
            updateTimerStatus('stopped');
            currentTimerHours = 0;
            sessionStartTime = null;
            if (totalTimerInput) {
                totalTimerInput.value = '00:00:00';
            }
        }

        function resetTimerAfterSave() {
            // Reset timer on server side (asynchronously)
            const csrfToken = getCsrfToken();
            return fetch('/my/gate_lock_assigned/timer_action', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: new URLSearchParams({
                    'csrf_token': csrfToken,
                    'task_id': taskId,
                    'action': 'reset'
                })
            })
            .then(function(response) {
                // Timer reset on server
                return response;
            })
            .catch(function(error) {
                console.error('Error resetting timer after save:', error);
                // Return resolved promise to continue with form submission
                return Promise.resolve();
            });
        }

        function submitForm(formSubmitHandler, timerHoursValue) {
            // Submit the form normally by removing event listener temporarily
            if (workOrderForm) {
                // Remove the submit handler to avoid infinite loop
                workOrderForm.removeEventListener('submit', formSubmitHandler);
                
                // Add timer hours as hidden input before submitting (captured before reset)
                // This ensures worksheet gets the correct timer hours value
                let timerHoursInput = workOrderForm.querySelector('input[name="saved_timer_hours"]');
                if (!timerHoursInput) {
                    timerHoursInput = document.createElement('input');
                    timerHoursInput.type = 'hidden';
                    timerHoursInput.name = 'saved_timer_hours';
                    workOrderForm.appendChild(timerHoursInput);
                }
                // Use the passed timer hours value (captured before reset)
                const finalTimerHours = timerHoursValue !== undefined ? timerHoursValue : 0.0;
                timerHoursInput.value = finalTimerHours;
                console.log('Added saved_timer_hours to form:', finalTimerHours, 'Formatted:', formatTime(finalTimerHours));
                
                // Submit the form
                // Note: Form fields will be cleared on the backend after saving to worksheet
                workOrderForm.submit();
            }
        }

        function startTimerDisplay() {
            if (intervalId) {
                console.log('Timer display already running');
                return;
            }
            
            // Clear the stopped flag when starting
            isTimerStopped = false;
            
            console.log('Starting timer display interval');
            intervalId = setInterval(function() {
                // Only update if timer is not stopped (prevents queued callbacks from updating after stop)
                if (!isTimerStopped) {
                    updateTimerDisplay();
                }
            }, 1000);
            
            // Update immediately
            updateTimerDisplay();
        }

        function stopTimerDisplay() {
            if (intervalId) {
                clearInterval(intervalId);
                intervalId = null;
            }
            // Set flag to prevent any queued interval callbacks from updating
            isTimerStopped = true;
        }

        function updateTimerDisplay(displayHours) {
            console.log('=== updateTimerDisplay CALLED ===');
            console.log('Parameters:', {
                displayHours: displayHours,
                displayHoursFormatted: displayHours !== undefined ? formatTime(displayHours) : 'undefined'
            });
            console.log('Current state:', {
                currentTimerHours: currentTimerHours,
                currentTimerHoursFormatted: formatTime(currentTimerHours),
                sessionStartTime: sessionStartTime,
                intervalId: intervalId,
                isTimerStopped: isTimerStopped
            });
            
            // If timer is stopped and no explicit displayHours provided, don't update
            // This prevents queued interval callbacks from updating after stop
            if (isTimerStopped && displayHours === undefined) {
                console.log('Timer is stopped and no displayHours provided, skipping update');
                return;
            }
            
            let totalHours = currentTimerHours;
            let calculationMethod = 'default (currentTimerHours)';

            // If timer is running (has sessionStartTime AND interval is running AND not stopped), calculate total
            if (sessionStartTime && intervalId && !isTimerStopped) {
                // Timer is running - calculate current session time
                const now = new Date();
                const elapsedMs = now - sessionStartTime;
                const elapsedHours = elapsedMs / (1000 * 60 * 60);
                totalHours = currentTimerHours + elapsedHours;
                calculationMethod = 'running (currentTimerHours + elapsedHours)';
                console.log('Timer is RUNNING - calculating:', {
                    currentTimerHours: currentTimerHours,
                    elapsedMs: elapsedMs,
                    elapsedHours: elapsedHours,
                    totalHours: totalHours
                });
            } else if (displayHours !== undefined) {
                // Timer is stopped - use the provided value explicitly (highest priority)
                totalHours = displayHours;
                const previousCurrentTimerHours = currentTimerHours;
                currentTimerHours = displayHours; // Update currentTimerHours when explicitly provided
                calculationMethod = 'explicit displayHours provided';
                console.log('Using EXPLICIT displayHours:', {
                    displayHours: displayHours,
                    previousCurrentTimerHours: previousCurrentTimerHours,
                    newCurrentTimerHours: currentTimerHours
                });
            } else if (!sessionStartTime || isTimerStopped) {
                // Timer is stopped and no displayHours provided - use currentTimerHours as-is
                totalHours = currentTimerHours;
                calculationMethod = 'stopped (currentTimerHours only)';
                console.log('Timer is STOPPED - using currentTimerHours:', totalHours);
            }

            console.log('Final calculation:', {
                calculationMethod: calculationMethod,
                totalHours: totalHours,
                totalHoursFormatted: formatTime(totalHours)
            });

            // Update current timer display in HH:MM:SS format
            if (timerDisplay) {
                const previousDisplay = timerDisplay.textContent;
                timerDisplay.textContent = formatTime(totalHours);
                console.log('Updated timer display:', previousDisplay, '->', timerDisplay.textContent);
            } else {
                console.warn('timerDisplay element not found!');
            }
            
            // Update total timer hours field
            if (totalTimerInput) {
                let inputValue;
                if (sessionStartTime && intervalId && !isTimerStopped) {
                    // Timer is running - update in real-time
                    inputValue = formatTime(totalHours);
                } else if (displayHours !== undefined) {
                    // Timer is stopped - use the provided value
                    inputValue = formatTime(displayHours);
                } else {
                    // Timer is stopped, no explicit value - use currentTimerHours
                    inputValue = formatTime(currentTimerHours);
                }
                const previousInputValue = totalTimerInput.value;
                totalTimerInput.value = inputValue;
                console.log('Updated total timer input:', previousInputValue, '->', inputValue);
            } else {
                console.warn('totalTimerInput element not found!');
            }
            
            console.log('=== END updateTimerDisplay ===');
        }

        function updateTimerStatus(status) {
            if (!timerStatus) return;

            const statusText = {
                'running': '<span class="text-success">●</span> Timer Running',
                'paused': '<span class="text-warning">●</span> Timer Paused',
                'stopped': '<span class="text-secondary">●</span> Timer Stopped'
            };

            timerStatus.innerHTML = statusText[status] || statusText['stopped'];
        }

        function updateButtonStates(isRunning) {
            if (startBtn) {
                startBtn.disabled = isRunning;
            }
            if (stopBtn) {
                stopBtn.disabled = !isRunning;
            }
        }

        function getCsrfToken() {
            const csrfInput = timerContainer.querySelector('input[name="csrf_token"]');
            return csrfInput ? csrfInput.value : '';
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTimer);
    } else {
        // DOM is already ready
        initTimer();
    }
})();
