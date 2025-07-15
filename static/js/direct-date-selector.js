/**
 * Direct Date Selector
 * 
 * A specialized calendar date selector that avoids timezone issues
 * by directly working with the year, month, day components.
 */

// Global state
let directSelectedDates = new Set(); // Store selected dates
let directPrimaryDate = null; // Main schedule date
let directCurrentMonth = new Date().getMonth();
let directCurrentYear = new Date().getFullYear();

/**
 * Initialize the direct calendar 
 * @param {string} containerId - The ID of the container element
 * @param {string} primaryDateStr - The primary date in YYYY-MM-DD format
 */
function initDirectCalendar(containerId, primaryDateStr = null) {
    directPrimaryDate = primaryDateStr;
    console.log("Initializing direct calendar with primary date:", primaryDateStr);
    
    // Make sure the container exists
    if (!document.getElementById(containerId)) {
        console.error("Container not found:", containerId);
        return;
    }
    
    // Make sure the buttons exist
    const prevBtn = document.getElementById('direct-prev-month-btn');
    const nextBtn = document.getElementById('direct-next-month-btn');
    
    if (!prevBtn || !nextBtn) {
        console.error("Month navigation buttons not found");
        return;
    }
    
    // Clear any existing handlers to prevent duplicates
    const newPrevBtn = prevBtn.cloneNode(true);
    const newNextBtn = nextBtn.cloneNode(true);
    
    prevBtn.parentNode.replaceChild(newPrevBtn, prevBtn);
    nextBtn.parentNode.replaceChild(newNextBtn, nextBtn);
    
    // Initialize buttons with new event listeners
    newPrevBtn.addEventListener('click', function() {
        directPrevMonth();
    });
    
    newNextBtn.addEventListener('click', function() {
        directNextMonth();
    });
    
    // Generate the calendar
    directUpdateCalendarHeader();
    directGenerateCalendarDays();
}

/**
 * Move to the previous month
 */
function directPrevMonth() {
    directCurrentMonth--;
    if (directCurrentMonth < 0) {
        directCurrentMonth = 11;
        directCurrentYear--;
    }
    directUpdateCalendarHeader();
    directGenerateCalendarDays();
}

/**
 * Move to the next month
 */
function directNextMonth() {
    directCurrentMonth++;
    if (directCurrentMonth > 11) {
        directCurrentMonth = 0;
        directCurrentYear++;
    }
    directUpdateCalendarHeader();
    directGenerateCalendarDays();
}

/**
 * Update the calendar header with the current month and year
 */
function directUpdateCalendarHeader() {
    const monthNames = [
        'January', 'February', 'March', 'April', 'May', 'June', 
        'July', 'August', 'September', 'October', 'November', 'December'
    ];
    
    document.getElementById('direct-current-month-display').textContent = 
        `${monthNames[directCurrentMonth]} ${directCurrentYear}`;
}

/**
 * Get the number of days in a month
 * @param {number} year - The year
 * @param {number} month - The month (0-11)
 * @returns {number} The number of days in the month
 */
function directGetDaysInMonth(year, month) {
    return new Date(year, month + 1, 0).getDate();
}

/**
 * Format a date string in YYYY-MM-DD format
 * @param {number} year - The year
 * @param {number} month - The month (1-12)
 * @param {number} day - The day
 * @returns {string} The formatted date string
 */
function directFormatDateString(year, month, day) {
    // Format month and day with leading zeros
    const monthStr = month.toString().padStart(2, '0');
    const dayStr = day.toString().padStart(2, '0');
    return `${year}-${monthStr}-${dayStr}`;
}

/**
 * Generate the calendar days
 */
function directGenerateCalendarDays() {
    const calendarDays = document.getElementById('direct-calendar-days');
    calendarDays.innerHTML = '';
    
    // Get the first day of the month and days in month
    const firstDayOfMonth = new Date(directCurrentYear, directCurrentMonth, 1);
    const startingDayOfWeek = firstDayOfMonth.getDay();
    const daysInCurrentMonth = directGetDaysInMonth(directCurrentYear, directCurrentMonth);
    
    // Calculate previous and next month
    let prevMonthYear = directCurrentYear;
    let prevMonth = directCurrentMonth - 1;
    if (prevMonth < 0) {
        prevMonth = 11;
        prevMonthYear--;
    }
    
    let nextMonthYear = directCurrentYear;
    let nextMonth = directCurrentMonth + 1;
    if (nextMonth > 11) {
        nextMonth = 0;
        nextMonthYear++;
    }
    
    // Get today's date
    const today = new Date();
    const todayYear = today.getFullYear();
    const todayMonth = today.getMonth();
    const todayDay = today.getDate();
    
    // Add days from previous month to fill the first row
    const daysInPrevMonth = directGetDaysInMonth(prevMonthYear, prevMonth);
    for (let i = startingDayOfWeek - 1; i >= 0; i--) {
        const day = daysInPrevMonth - i;
        const display_month = prevMonth + 1; // For display (1-12)
        const dateStr = directFormatDateString(prevMonthYear, display_month, day);
        
        const isToday = (prevMonthYear === todayYear && prevMonth === todayMonth && day === todayDay);
        const isPrimary = (dateStr === directPrimaryDate);
        const isSelected = directSelectedDates.has(dateStr);
        
        directAddDayToCalendar(calendarDays, day, dateStr, 'outside-month', 
            isToday, isPrimary, isSelected, prevMonthYear, display_month, day);
    }
    
    // Add days of current month
    const display_current_month = directCurrentMonth + 1; // For display (1-12)
    for (let day = 1; day <= daysInCurrentMonth; day++) {
        const dateStr = directFormatDateString(directCurrentYear, display_current_month, day);
        
        const isToday = (directCurrentYear === todayYear && directCurrentMonth === todayMonth && day === todayDay);
        const isPrimary = (dateStr === directPrimaryDate);
        const isSelected = directSelectedDates.has(dateStr);
        
        directAddDayToCalendar(calendarDays, day, dateStr, '', 
            isToday, isPrimary, isSelected, directCurrentYear, display_current_month, day);
    }
    
    // Add days from next month to complete the grid
    const totalCells = 42; // 6 rows x 7 columns
    const cellsToAdd = totalCells - (startingDayOfWeek + daysInCurrentMonth);
    const display_next_month = nextMonth + 1; // For display (1-12)
    
    for (let day = 1; day <= cellsToAdd; day++) {
        const dateStr = directFormatDateString(nextMonthYear, display_next_month, day);
        
        const isToday = (nextMonthYear === todayYear && nextMonth === todayMonth && day === todayDay);
        const isPrimary = (dateStr === directPrimaryDate);
        const isSelected = directSelectedDates.has(dateStr);
        
        directAddDayToCalendar(calendarDays, day, dateStr, 'outside-month', 
            isToday, isPrimary, isSelected, nextMonthYear, display_next_month, day);
    }
}

/**
 * Add a day to the calendar
 * @param {HTMLElement} container - The container to add the day to
 * @param {number} day - The day number
 * @param {string} dateStr - The date string in YYYY-MM-DD format
 * @param {string} extraClass - Extra CSS class for styling
 * @param {boolean} isToday - Whether this day is today
 * @param {boolean} isPrimary - Whether this is the primary date
 * @param {boolean} isSelected - Whether this date is selected
 * @param {number} year - The year
 * @param {number} month - The month (1-12)
 * @param {number} dayNum - The day number
 */
function directAddDayToCalendar(container, day, dateStr, extraClass, isToday, isPrimary, isSelected, year, month, dayNum) {
    const dayItem = document.createElement('div');
    dayItem.textContent = day;
    dayItem.className = `day-item${extraClass ? ' ' + extraClass : ''}${isToday ? ' today' : ''}`;
    
    if (isPrimary) {
        dayItem.classList.add('primary-date');
        dayItem.setAttribute('title', 'Primary schedule date');
    } else if (isSelected) {
        dayItem.classList.add('selected');
    }
    
    // Store the date components as data attributes
    dayItem.setAttribute('data-date', dateStr);
    dayItem.setAttribute('data-year', year);
    dayItem.setAttribute('data-month', month);
    dayItem.setAttribute('data-day', dayNum);
    
    // Add click event to select/deselect the date
    if (!isPrimary) {
        dayItem.addEventListener('click', function() {
            // Use the data attributes to get the date string
            const clickedDateStr = this.getAttribute('data-date');
            directToggleDateSelection(clickedDateStr, this);
        });
    } else {
        dayItem.classList.add('disabled');
    }
    
    // Fix the width to make a 7-column grid
    dayItem.style.width = 'calc(100% / 7)';
    
    container.appendChild(dayItem);
}

/**
 * Toggle date selection
 * @param {string} dateStr - The date string in YYYY-MM-DD format
 * @param {HTMLElement} dayItem - The day item element
 */
function directToggleDateSelection(dateStr, dayItem) {
    console.log("Toggling date selection for:", dateStr);
    
    if (directSelectedDates.has(dateStr)) {
        console.log("Removing date:", dateStr);
        directSelectedDates.delete(dateStr);
        dayItem.classList.remove('selected');
    } else {
        console.log("Adding date:", dateStr);
        directSelectedDates.add(dateStr);
        dayItem.classList.add('selected');
    }
    
    // Update form and display
    directUpdateFormWithSelectedDates();
    directUpdateSelectedDatesDisplay();
    
    // Make sure the checkbox is checked if we have dates selected
    const repeatCheckbox = document.getElementById('enable_repeat_days');
    if (repeatCheckbox && directSelectedDates.size > 0) {
        repeatCheckbox.checked = true;
    }
}

/**
 * Update the form with selected dates
 */
function directUpdateFormWithSelectedDates() {
    // Update both direct_repeat_days_list and repeat_days fields for compatibility
    const datesList = Array.from(directSelectedDates).join(',');
    console.log("Selected dates to save:", datesList);

    try {
        // Always remove existing repeat_days_inputs to avoid duplicates
        const existingInputsContainer = document.getElementById('repeat_days_inputs');
        if (existingInputsContainer) {
            existingInputsContainer.innerHTML = '';
        }
        
        // Get form
        const form = document.getElementById('schedule_form') || document.querySelector('form');
        if (!form) {
            console.error("Could not find form to add repeat days fields");
            return;
        }
        
        // Update direct_repeat_days_list field
        let directRepeatDaysField = document.getElementById('direct_repeat_days_list');
        if (!directRepeatDaysField) {
            // Create the field if it doesn't exist
            directRepeatDaysField = document.createElement('input');
            directRepeatDaysField.type = 'hidden';
            directRepeatDaysField.name = 'direct_repeat_days_list';
            directRepeatDaysField.id = 'direct_repeat_days_list';
            form.appendChild(directRepeatDaysField);
            console.log("Added direct_repeat_days_list field to form");
        }
        
        // Update repeat_days field (this is the field name in ScheduleForm)
        let repeatDaysField = document.getElementById('repeat_days_input');
        if (!repeatDaysField) {
            // Create the field if it doesn't exist
            repeatDaysField = document.createElement('input');
            repeatDaysField.type = 'hidden';
            repeatDaysField.name = 'repeat_days';
            repeatDaysField.id = 'repeat_days_input';
            form.appendChild(repeatDaysField);
            console.log("Added repeat_days field to form");
        }
        
        // Set both fields to the same value
        directRepeatDaysField.value = datesList;
        repeatDaysField.value = datesList;
        
        // Also create individual checkboxes for each date (for compatibility with server-side processing)
        if (directSelectedDates.size > 0) {
            const inputsContainer = document.getElementById('repeat_days_inputs');
            if (inputsContainer) {
                directSelectedDates.forEach(dateStr => {
                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.name = 'repeat_days';
                    checkbox.value = dateStr;
                    checkbox.checked = true;
                    checkbox.style.display = 'none'; // Hide these since they're just for form submission
                    inputsContainer.appendChild(checkbox);
                });
            }
        }
        
        console.log("Updated repeat_days field with value:", repeatDaysField.value);
        console.log("Form data that will be submitted:", new FormData(form));
        
        // For debugging, list all input fields in the form
        const formInputs = form.querySelectorAll('input, select, textarea');
        console.log("Form has", formInputs.length, "input elements:");
        formInputs.forEach(input => {
            if (input.name) {
                console.log(`- ${input.name}: ${input.value} (type: ${input.type})`);
            }
        });
    } catch (error) {
        console.error("Error updating form with selected dates:", error);
    }
}

/**
 * Update the display of selected dates
 */
function directUpdateSelectedDatesDisplay() {
    const container = document.getElementById('selected-dates-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (directSelectedDates.size === 0) {
        container.innerHTML = '<span class="text-muted">None selected</span>';
        return;
    }
    
    // Sort dates chronologically
    const sortedDates = Array.from(directSelectedDates).sort();
    
    // Add date tags
    sortedDates.forEach(dateStr => {
        // Parse the date parts
        const parts = dateStr.split('-');
        const year = parseInt(parts[0]);
        const month = parseInt(parts[1]);
        const day = parseInt(parts[2]);
        
        // Create a formatted display string (e.g., "Apr 2")
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const displayText = `${monthNames[month-1]} ${day}`;
        
        const dateTag = document.createElement('div');
        dateTag.className = 'date-tag m-1 p-1';
        dateTag.innerHTML = `
            ${displayText}
            <button type="button" class="btn-close btn-close-sm ms-1" aria-label="Remove" 
                    onclick="directRemoveDate('${dateStr}')"></button>
        `;
        container.appendChild(dateTag);
    });
}

/**
 * Remove a date from selection
 * @param {string} dateStr - The date string in YYYY-MM-DD format
 */
function directRemoveDate(dateStr) {
    if (directSelectedDates.has(dateStr)) {
        directSelectedDates.delete(dateStr);
        
        // Update the calendar visual state
        const parts = dateStr.split('-');
        const year = parseInt(parts[0]);
        const month = parseInt(parts[1]);
        const day = parseInt(parts[2]);
        
        const dayItem = document.querySelector(`.day-item[data-year="${year}"][data-month="${month}"][data-day="${day}"]`);
        if (dayItem) {
            dayItem.classList.remove('selected');
        }
        
        // Update form and display
        directUpdateFormWithSelectedDates();
        directUpdateSelectedDatesDisplay();
    }
}

/**
 * Clear all selected dates
 */
function directClearDateSelection() {
    // Clear the set
    directSelectedDates.clear();
    
    // Remove 'selected' class from all day items
    document.querySelectorAll('.day-item.selected').forEach(dayItem => {
        dayItem.classList.remove('selected');
    });
    
    // Update form and display
    directUpdateFormWithSelectedDates();
    directUpdateSelectedDatesDisplay();
}

// Add a global function to get the selected dates
function getDirectSelectedDates() {
    return Array.from(directSelectedDates);
}