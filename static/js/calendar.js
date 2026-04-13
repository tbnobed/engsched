document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();

    let bulkSelectActive = false;

    // Initialize Bootstrap modal with static backdrop to prevent closing on outside clicks
    const scheduleModalEl = document.getElementById('scheduleModal');
    const scheduleModal = scheduleModalEl ? bootstrap.Modal.getOrCreateInstance(scheduleModalEl, { backdrop: 'static' }) : null;

    function positionSchedules() {
        document.querySelectorAll('.schedule-event').forEach(function(el) {
            if (el.style.top && el.style.top !== '') return;
            var startStr = el.getAttribute('data-start-time');
            var endStr = el.getAttribute('data-end-time');
            if (!startStr || !endStr) return;
            var start = new Date(startStr);
            var end = new Date(endStr);
            var startHour = start.getHours() + start.getMinutes() / 60;
            var endHour = end.getHours() + end.getMinutes() / 60;
            if (endHour <= startHour) endHour = 24;
            var slotHeight = 60;
            var parent = el.closest('.day-slots');
            if (parent) {
                var firstSlot = parent.querySelector('.time-slot');
                if (firstSlot) slotHeight = firstSlot.offsetHeight || 60;
            }
            var top = startHour * slotHeight;
            var height = (endHour - startHour) * slotHeight;
            el.style.position = 'absolute';
            el.style.top = top + 'px';
            el.style.height = height + 'px';
            el.style.zIndex = '10';
            var avatar = el.querySelector('.sched-avatar');
            if (avatar) {
                avatar.style.top = Math.round(height / 2) + 'px';
            }
        });
    }

    // Handle schedule event clicks
    document.querySelectorAll('.schedule-event').forEach(event => {
        event.addEventListener('click', function(e) {
            if (bulkSelectActive) return;
            e.stopPropagation();
            const scheduleId = this.dataset.scheduleId;
            const startTime = new Date(this.dataset.startTime);
            const endTime = new Date(this.dataset.endTime);
            const descElement = this.querySelector('.schedule-desc');
            const description = descElement ? descElement.textContent : '';
            const technicianId = this.dataset.technicianId;
            const timeOff = this.dataset.timeOff === 'true';  // Add time off status
            
            // Set form values
            document.getElementById('schedule_id').value = scheduleId;
            
            // Fix for date display - adjust for timezone issues
            // Use the date from the data attribute directly without timezone conversion
            const startTimeStr = this.dataset.startTime.split(' ')[0]; // Get YYYY-MM-DD portion
            
            document.getElementById('schedule_date').value = startTimeStr;
            // Format time as HH:MM for 30-minute increment support
            const startTimeFormatted = `${startTime.getHours().toString().padStart(2, '0')}:${startTime.getMinutes().toString().padStart(2, '0')}`;
            const endTimeFormatted = `${endTime.getHours().toString().padStart(2, '0')}:${endTime.getMinutes().toString().padStart(2, '0')}`;
            document.getElementById('start_hour').value = startTimeFormatted;
            document.getElementById('end_hour').value = endTimeFormatted;
            document.getElementById('description').value = description;
            
            // Handle time off checkbox if it exists
            const timeOffCheckbox = document.getElementById('time_off');
            if (timeOffCheckbox) {
                timeOffCheckbox.checked = timeOff;
            }
            
            // Set all-day (OOO) checkbox based on data attribute
            const allDay = this.dataset.allDay === 'true';
            const allDayCheckbox = document.getElementById('all_day');
            if (allDayCheckbox) {
                allDayCheckbox.checked = allDay;
            }
            
            // Set technician if the select exists (admin only)
            const technicianSelect = document.getElementById('technician');
            if (technicianSelect) {
                technicianSelect.value = technicianId;
            }
            
            // Set location if it exists
            // We need to find the location ID from the location element
            const locationElement = this.querySelector('.schedule-location');
            if (locationElement && locationElement.textContent) {
                const locationText = locationElement.textContent.trim();
                // Find the location select and set it to the proper location if found
                const locationSelect = document.getElementById('location_id');
                if (locationSelect) {
                    console.log("Setting location from:", locationText);
                    
                    // Try to find the matching location option
                    let locationFound = false;
                    for (let i = 0; i < locationSelect.options.length; i++) {
                        if (locationSelect.options[i].text.trim() === locationText) {
                            locationSelect.selectedIndex = i;
                            locationFound = true;
                            console.log("Location matched:", locationSelect.options[i].text);
                            break;
                        }
                    }
                    
                    if (!locationFound) {
                        console.log("No matching location found in dropdown for:", locationText);
                    }
                }
            } else {
                console.log("No location element found, setting to default Plex location");
                const locationSelect = document.getElementById('location_id');
                if (locationSelect) {
                    // Find the Plex option
                    for (let i = 0; i < locationSelect.options.length; i++) {
                        if (locationSelect.options[i].text.trim() === 'Plex') {
                            locationSelect.selectedIndex = i;
                            break;
                        }
                    }
                }
            }

            // Update modal title and buttons
            document.querySelector('.modal-title').textContent = 'Edit Schedule';
            document.querySelector('button[type="submit"]').textContent = 'Update Schedule';
            document.getElementById('delete_button').style.display = 'block';
            document.getElementById('copy_button').style.display = 'block';

            // Show the modal
            scheduleModal.show();
        });
    });

    // Handle copy button click
    const copyBtn = document.getElementById('copy_button');
    if (copyBtn) copyBtn.addEventListener('click', function() {
        // Clear the schedule ID to create a new entry
        document.getElementById('schedule_id').value = '';

        // Update modal title and buttons
        document.querySelector('.modal-title').textContent = 'Copy Schedule';
        document.querySelector('button[type="submit"]').textContent = 'Add Copy';
        document.getElementById('delete_button').style.display = 'none';
        document.getElementById('copy_button').style.display = 'none';
    });

    // Handle time slot clicks
    document.querySelectorAll('.time-slot').forEach(slot => {
        slot.addEventListener('click', function() {
            const hour = this.dataset.hour;
            const date = this.closest('.day-slots').dataset.date;

            // Reset form
            document.getElementById('schedule_form').reset();
            document.getElementById('schedule_id').value = '';
            
            // Explicitly clear checkboxes
            const timeOffCheckbox = document.getElementById('time_off');
            const allDayCheckbox = document.getElementById('all_day');
            if (timeOffCheckbox) timeOffCheckbox.checked = false;
            if (allDayCheckbox) allDayCheckbox.checked = false;

            // Set the date and initial times with proper HH:MM format
            document.getElementById('schedule_date').value = date;
            document.getElementById('start_hour').value = `${hour}:00`;
            
            // Set default location to Plex
            const locationSelect = document.getElementById('location_id');
            if (locationSelect) {
                // First try to find "Plex" (ID 1)
                for (let i = 0; i < locationSelect.options.length; i++) {
                    if (locationSelect.options[i].text.trim() === 'Plex') {
                        locationSelect.selectedIndex = i;
                        console.log("Setting default location to Plex");
                        break;
                    }
                }
            }

            // Update modal title and buttons
            document.querySelector('.modal-title').textContent = 'Add New Schedule';
            document.querySelector('button[type="submit"]').textContent = 'Add Schedule';
            document.getElementById('delete_button').style.display = 'none';
            document.getElementById('copy_button').style.display = 'none';

            // Show the modal
            scheduleModal.show();
        });
    });

    // Update end time options based on start time - Remove auto-update functionality
    window.updateEndTimeOptions = function() {
        const endSelect = document.getElementById('end_hour');
        // Clear existing options
        endSelect.innerHTML = '';

        // Add options for all 24 hours
        for (let hour = 0; hour < 24; hour++) {
            const option = document.createElement('option');
            option.value = hour.toString().padStart(2, '0');
            option.text = `${hour.toString().padStart(2, '0')}:00`;
            endSelect.appendChild(option);
        }
        // Add the 00:00 option at the end for next day
        const midnightOption = document.createElement('option');
        midnightOption.value = '00';
        midnightOption.text = '00:00';
        endSelect.appendChild(midnightOption);
    };

    // Remove the onchange handler from the start hour select
    const startHourSelect = document.getElementById('start_hour');
    if (startHourSelect) {
        startHourSelect.removeAttribute('onchange');
    }

    // Mini-calendar for repeat days selection
    let currentDate = new Date();
    let selectedDates = new Set(); // Use a Set to store selected dates
    let currentMonth = currentDate.getMonth();
    let currentYear = currentDate.getFullYear();
    let primaryDate = null; // The main date selected in the schedule form
    
    window.toggleRepeatDaysSelection = function() {
        initMiniCalendar();
    };
    
    window.selectedDates = selectedDates;
    window.initMiniCalendar = initMiniCalendar;
    window.renderSelectedDates = function() { updateSelectedDatesDisplay(); updateRepeatDaysInput(); };
    window.renderCalendar = function() { generateCalendarDays(); };

    let miniCalInitialized = false;
    function initMiniCalendar() {
        const dateInput = document.getElementById('schedule_date');
        primaryDate = dateInput.value;
        updateCalendarHeader();
        generateCalendarDays();

        if (!miniCalInitialized) {
            miniCalInitialized = true;
            document.getElementById('prev-month').addEventListener('click', function() {
                navigateMonth(-1);
            });
            document.getElementById('next-month').addEventListener('click', function() {
                navigateMonth(1);
            });
            document.getElementById('clear-selection').addEventListener('click', function() {
                clearDateSelection();
            });
        }
    }
    
    // Update the calendar header (month and year)
    function updateCalendarHeader() {
        const monthNames = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];
        
        document.getElementById('calendar-month-year').textContent = 
            `${monthNames[currentMonth]} ${currentYear}`;
    }
    
    // Generate calendar days for the current month
    function generateCalendarDays() {
        const calendarDays = document.getElementById('calendar-days');
        calendarDays.innerHTML = '';
        
        // Create a date object for the first day of the current month
        const firstDay = new Date(currentYear, currentMonth, 1);
        const lastDay = new Date(currentYear, currentMonth + 1, 0);
        
        // Get the day of the week the month starts on (0 = Sunday, 6 = Saturday)
        const startingDayOfWeek = firstDay.getDay();
        
        // Get number of days in the current month
        const daysInMonth = lastDay.getDate();
        
        // Get today's date for highlighting
        const today = new Date();
        const todayFormatted = formatDate(today);
        
        // Add the days from the previous month to fill the first row
        const prevMonthLastDay = new Date(currentYear, currentMonth, 0).getDate();
        for (let i = startingDayOfWeek - 1; i >= 0; i--) {
            const day = prevMonthLastDay - i;
            const date = new Date(currentYear, currentMonth - 1, day);
            const dateFormatted = formatDate(date);
            
            addDayToCalendar(calendarDays, day, dateFormatted, 'outside-month', 
                dateFormatted === todayFormatted, 
                dateFormatted === primaryDate,
                selectedDates.has(dateFormatted));
        }
        
        // Add the days of the current month
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(currentYear, currentMonth, day);
            const dateFormatted = formatDate(date);
            
            addDayToCalendar(calendarDays, day, dateFormatted, '', 
                dateFormatted === todayFormatted, 
                dateFormatted === primaryDate,
                selectedDates.has(dateFormatted));
        }
        
        // Add days from the next month to complete the grid (always show 6 rows)
        const totalCells = 42; // 6 rows x 7 columns
        const cellsToAdd = totalCells - (startingDayOfWeek + daysInMonth);
        
        for (let day = 1; day <= cellsToAdd; day++) {
            const date = new Date(currentYear, currentMonth + 1, day);
            const dateFormatted = formatDate(date);
            
            addDayToCalendar(calendarDays, day, dateFormatted, 'outside-month', 
                dateFormatted === todayFormatted, 
                dateFormatted === primaryDate,
                selectedDates.has(dateFormatted));
        }
    }
    
    // Add a day to the calendar
    function addDayToCalendar(container, day, dateFormatted, extraClass, isToday, isPrimary, isSelected) {
        const dayItem = document.createElement('div');
        dayItem.textContent = day;
        dayItem.className = `day-item${extraClass ? ' ' + extraClass : ''}${isToday ? ' today' : ''}`;
        
        if (isPrimary) {
            dayItem.classList.add('primary-date');
            dayItem.setAttribute('title', 'Primary schedule date');
        } else if (isSelected) {
            dayItem.classList.add('selected');
        }
        
        dayItem.setAttribute('data-date', dateFormatted);
        
        // Add click event to select/deselect the date
        if (!isPrimary) { // Don't allow clicking on the primary date
            dayItem.addEventListener('click', function() {
                toggleDateSelection(dateFormatted, dayItem);
            });
        } else {
            dayItem.classList.add('disabled');
        }
        
        container.appendChild(dayItem);
    }
    
    // Toggle date selection
    function toggleDateSelection(dateStr, dayItem) {
        if (selectedDates.has(dateStr)) {
            // Deselect the date
            selectedDates.delete(dateStr);
            dayItem.classList.remove('selected');
        } else {
            // Select the date
            selectedDates.add(dateStr);
            dayItem.classList.add('selected');
        }
        
        // Update the display of selected dates
        updateSelectedDatesDisplay();
        
        // Update the hidden input
        updateRepeatDaysInput();
    }
    
    // Update the display of selected dates
    function updateSelectedDatesDisplay() {
        const container = document.getElementById('selected-dates-container');
        
        if (typeof updateSelectedCount === 'function') updateSelectedCount();
        if (selectedDates.size === 0) {
            container.innerHTML = '<span class="text-muted" id="no-dates-selected">Click dates on the calendar above</span>';
            return;
        }
        
        // Sort the dates
        const sortedDates = Array.from(selectedDates).sort();
        container.innerHTML = '';
        
        // Add date tags
        sortedDates.forEach(dateStr => {
            const dateObj = parseDate(dateStr);
            
            const dateTag = document.createElement('div');
            dateTag.className = 'date-tag';
            
            // Format the date nicely (e.g., "Mon 03/27")
            const dateLabel = document.createElement('span');
            dateLabel.textContent = new Date(dateObj).toLocaleDateString('en-US', { 
                weekday: 'short', 
                month: '2-digit',
                day: '2-digit'
            });
            
            // Add a remove button
            const closeBtn = document.createElement('span');
            closeBtn.className = 'close ms-2';
            closeBtn.innerHTML = '&times;';
            closeBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                removeDateSelection(dateStr);
            });
            
            dateTag.appendChild(dateLabel);
            dateTag.appendChild(closeBtn);
            container.appendChild(dateTag);
        });
    }
    
    // Remove a specific date from the selection
    function removeDateSelection(dateStr) {
        selectedDates.delete(dateStr);
        
        // Update the calendar if the date is currently visible
        const dayItem = document.querySelector(`.day-item[data-date="${dateStr}"]`);
        if (dayItem) {
            dayItem.classList.remove('selected');
        }
        
        // Update the display
        updateSelectedDatesDisplay();
        
        // Update the hidden input
        updateRepeatDaysInput();
    }
    
    function clearDateSelection(keepHidden = false) {
        selectedDates.clear();
        document.querySelectorAll('.day-item.selected').forEach(item => {
            item.classList.remove('selected');
        });
        updateSelectedDatesDisplay();
        if (!keepHidden) {
            updateRepeatDaysInput();
        }
        if (typeof updateSelectedCount === 'function') updateSelectedCount();
    }
    
    // Update the hidden input with selected dates
    function updateRepeatDaysInput() {
        const allDates = new Set(selectedDates);
        
        // Include the primary date
        if (primaryDate) {
            allDates.add(primaryDate);
        }
        
        // Update the hidden input
        if (allDates.size > 0) {
            document.getElementById('repeat_days_input').value = Array.from(allDates).sort().join(',');
        } else {
            document.getElementById('repeat_days_input').value = '';
        }
    }
    
    // Navigate to previous/next month
    function navigateMonth(direction) {
        currentMonth += direction;
        
        if (currentMonth < 0) {
            currentMonth = 11;
            currentYear--;
        } else if (currentMonth > 11) {
            currentMonth = 0;
            currentYear++;
        }
        
        updateCalendarHeader();
        generateCalendarDays();
    }
    
    // Format date as YYYY-MM-DD
    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    // Parse date string YYYY-MM-DD
    function parseDate(dateStr) {
        const [year, month, day] = dateStr.split('-').map(Number);
        return new Date(year, month - 1, day);
    }

    var schedFormEl = document.getElementById('schedule_form');
    if (schedFormEl && !window.location.pathname.includes('/personal_schedule')) {
        schedFormEl.addEventListener('submit', function(e) {
            e.preventDefault();

            var schedModeEl = document.querySelector('input[name="sched_mode"]:checked');
            var schedMode = schedModeEl ? schedModeEl.value : 'single';

            var date = document.getElementById('schedule_date').value;
            var startHour = document.getElementById('start_hour').value;
            var endHour = document.getElementById('end_hour').value;

            primaryDate = date;

            if (schedMode === 'single') {
                document.getElementById('start_time_input').value = date + ' ' + startHour;
                document.getElementById('end_time_input').value = date + ' ' + endHour;
                document.getElementById('repeat_days_input').value = '';
            } else if (schedMode === 'multi') {
                updateRepeatDaysInput();
                if (selectedDates.size === 0) {
                    alert('Please select at least one date on the calendar.');
                    return;
                }
                var allDates = Array.from(selectedDates).sort();
                if (!date) date = allDates[0];
                document.getElementById('schedule_date').value = date;
                document.getElementById('start_time_input').value = allDates[0] + ' ' + startHour;
                document.getElementById('end_time_input').value = allDates[0] + ' ' + endHour;
                var currentVal = document.getElementById('repeat_days_input').value;
                if (date && !currentVal.includes(date)) {
                    document.getElementById('repeat_days_input').value = currentVal ? currentVal + ',' + date : date;
                }
            } else if (schedMode === 'range') {
                var rangeVal = document.getElementById('repeat_days_input').value;
                if (!rangeVal) {
                    alert('Please select a valid date range with at least one weekday selected.');
                    return;
                }
                var rangeDates = rangeVal.split(',').filter(function(d){ return d; });
                if (rangeDates.length === 0) {
                    alert('No dates match the selected range and weekdays.');
                    return;
                }
                document.getElementById('schedule_date').value = rangeDates[0];
                document.getElementById('start_time_input').value = rangeDates[0] + ' ' + startHour;
                document.getElementById('end_time_input').value = rangeDates[0] + ' ' + endHour;
            }

            console.log('Form submission:', {
                mode: schedMode,
                date: document.getElementById('schedule_date').value,
                startHour: startHour,
                endHour: endHour,
                repeatDays: document.getElementById('repeat_days_input').value
            });

            this.submit();
        });
    }

    // Handle delete button
    const deleteBtn = document.getElementById('delete_button');
    if (deleteBtn) deleteBtn.addEventListener('click', function() {
        if (confirm('Are you sure you want to delete this schedule?')) {
            const scheduleId = document.getElementById('schedule_id').value;
            
            // Get the current week_start from the URL
            const urlParams = new URLSearchParams(window.location.search);
            const weekStart = urlParams.get('week_start');
            
            // Check if we're in personal view
            const isPersonalView = window.location.pathname.includes('/personal_schedule');
            const deletePath = isPersonalView ? '/schedule/delete/' : '/schedule/delete/';
            
            // Redirect with the week_start parameter to maintain the same view
            if (weekStart) {
                window.location.href = `${deletePath}${scheduleId}?week_start=${weekStart}${isPersonalView ? '&personal_view=true' : ''}`;
            } else {
                window.location.href = `${deletePath}${scheduleId}${isPersonalView ? '?personal_view=true' : ''}`;
            }
        }
    });

    // Initialize positions
    positionSchedules();

    // Time off functionality removed - now handled by base.html to ensure consistency

    // Update active users panel
    function updateActiveUsers() {
        const activeUsersDiv = document.getElementById('active-users');
        if (!activeUsersDiv) return;

        fetch('/api/active_users')
            .then(response => response.json())
            .then(users => {
                if (users.length === 0) {
                    activeUsersDiv.innerHTML = '<p style="color: var(--dark-text); opacity: 0.7;">No active technicians</p>';
                    return;
                }

                activeUsersDiv.innerHTML = users.map(user => `
                    <div class="active-user-entry d-flex align-items-center mb-2 p-2" 
                         style="border-left: 4px solid ${user.color}; background: var(--dark-bg); border-radius: 6px;">
                        <span class="me-2" style="width: 12px; height: 12px; border-radius: 50%; background-color: ${user.color}"></span>
                        <span class="fw-medium" style="color: var(--dark-text); font-size: 0.9rem;">${user.username}</span>
                    </div>
                `).join('');
            })
            .catch(error => {
                console.error('Error fetching active users:', error);
                activeUsersDiv.innerHTML = '<p class="text-danger">Error loading active users</p>';
            });
    }

    // Update active users every minute
    updateActiveUsers(); // Call immediately when loaded
    setInterval(updateActiveUsers, 60000);
    
    // Current time line functionality
    function updateCurrentTimeLine() {
        const timeLines = document.querySelectorAll('.current-time-line');
        if (timeLines.length === 0) return;
        
        // Get current time in user's timezone
        const now = new Date();
        const userTimezone = window.userTimezone || 'UTC';
        
        // Create time in user's timezone using Intl API
        let currentHour, currentMinute, currentSecond, timeString;
        
        try {
            // Get the current time in the user's timezone including seconds for precision
            const timeInUserTimezone = new Intl.DateTimeFormat('en-US', {
                timeZone: userTimezone,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            }).format(now);
            
            // Parse the formatted time including seconds
            const [hour, minute, second] = timeInUserTimezone.split(':').map(Number);
            currentHour = hour;
            currentMinute = minute;
            currentSecond = second;
            
            // Format time for display (12-hour format to match main clock)
            timeString = new Intl.DateTimeFormat('en-US', {
                timeZone: userTimezone,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: true
            }).format(now);
            
        } catch (error) {
            console.warn('Error getting time in user timezone, falling back to local time:', error);
            // Fallback to local time
            currentHour = now.getHours();
            currentMinute = now.getMinutes();
            const currentSecond = now.getSeconds();
            timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        }
        
        // Calculate position with second-level precision for smoother updates
        const totalMinutes = currentHour * 60 + currentMinute + (currentSecond / 60);
        const topPosition = Math.round(totalMinutes); // Round to nearest pixel
        
        timeLines.forEach(timeLine => {
            timeLine.style.top = `${topPosition}px`;
            timeLine.style.display = 'block';
            timeLine.setAttribute('data-time', timeString);
        });
        
        console.log('Calendar timeline sync check:', `${currentHour}:${currentMinute.toString().padStart(2, '0')}:${currentSecond.toString().padStart(2, '0')}`, 'position:', topPosition, 'totalMinutes:', totalMinutes.toFixed(2));
    }
    
    // Initialize current time line and update it every second to match dashboard precision
    updateCurrentTimeLine();
    setInterval(updateCurrentTimeLine, 1000);

    // Bulk select mode (bulkSelectActive declared at top of DOMContentLoaded, used by event handlers above)
    // Variable already hoisted above
    const bulkSelected = new Set();
    const bulkToggleBtn = document.getElementById('bulk-select-toggle');
    const bulkBar = document.getElementById('bulk-action-bar');
    const bulkCountEl = document.getElementById('bulk-count');
    const calendarContainer = document.querySelector('.calendar-container');

    function updateBulkCount() {
        if (!bulkCountEl) return;
        const n = bulkSelected.size;
        bulkCountEl.textContent = n + ' selected';
        if (bulkBar) {
            bulkBar.classList.toggle('visible', n > 0);
        }
    }

    function exitBulkMode() {
        bulkSelectActive = false;
        bulkSelected.clear();
        if (calendarContainer) calendarContainer.classList.remove('bulk-select-mode');
        document.querySelectorAll('.schedule-event.bulk-selected').forEach(function(el) {
            el.classList.remove('bulk-selected');
        });
        if (bulkBar) bulkBar.classList.remove('visible');
        if (bulkToggleBtn) {
            bulkToggleBtn.classList.remove('btn-warning');
            bulkToggleBtn.classList.add('btn-outline-warning');
            bulkToggleBtn.innerHTML = '<i data-feather="check-square"></i> Select';
            feather.replace();
        }
    }

    if (bulkToggleBtn) {
        bulkToggleBtn.addEventListener('click', function() {
            if (bulkSelectActive) {
                exitBulkMode();
            } else {
                bulkSelectActive = true;
                if (calendarContainer) calendarContainer.classList.add('bulk-select-mode');
                bulkToggleBtn.classList.remove('btn-outline-warning');
                bulkToggleBtn.classList.add('btn-warning');
                bulkToggleBtn.innerHTML = '<i data-feather="x"></i> Cancel Select';
                feather.replace();
            }
        });
    }

    document.querySelectorAll('.schedule-event').forEach(function(el) {
        el.addEventListener('click', function(e) {
            if (!bulkSelectActive) return;
            e.stopPropagation();
            e.preventDefault();
            const sid = this.dataset.scheduleId;
            if (!sid) return;
            if (bulkSelected.has(sid)) {
                bulkSelected.delete(sid);
                this.classList.remove('bulk-selected');
            } else {
                bulkSelected.add(sid);
                this.classList.add('bulk-selected');
            }
            updateBulkCount();
        }, true);
    });

    const bulkSelectAllBtn = document.getElementById('bulk-select-all');
    if (bulkSelectAllBtn) {
        bulkSelectAllBtn.addEventListener('click', function() {
            document.querySelectorAll('.schedule-event').forEach(function(el) {
                const sid = el.dataset.scheduleId;
                if (sid) {
                    bulkSelected.add(sid);
                    el.classList.add('bulk-selected');
                }
            });
            updateBulkCount();
        });
    }

    const bulkCancelBtn = document.getElementById('bulk-cancel');
    if (bulkCancelBtn) {
        bulkCancelBtn.addEventListener('click', function() {
            exitBulkMode();
        });
    }

    const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
    if (bulkDeleteBtn) {
        bulkDeleteBtn.addEventListener('click', function() {
            if (bulkSelected.size === 0) return;
            if (!confirm('Delete ' + bulkSelected.size + ' schedule(s)? This cannot be undone.')) return;
            const ids = Array.from(bulkSelected).map(Number);
            fetch('/schedule/bulk-delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify({ schedule_ids: ids })
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.success) {
                    window.location.reload();
                } else {
                    alert('Error deleting schedules: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(function(err) {
                alert('Error deleting schedules: ' + err.message);
            });
        });
    }
});