/* Transpose the existing geometry, not dates: retain timezone/segment decisions,
 * event identity, modal listeners, selection and the original inline styles. */
(() => {
    const key = 'schedule-orientation';
    const scrollPositions = { vertical: { left: 0, top: 0 }, horizontal: { left: 0, top: 0 } };
    const preference = () => {
        try { return localStorage.getItem(key) === 'horizontal' ? 'horizontal' : 'vertical'; }
        catch (_) { return 'vertical'; }
    };
    const remember = mode => {
        try { localStorage.setItem(key, mode); } catch (_) { /* Storage may be blocked. */ }
    };
    const geometry = event => ({
        start: Math.max(0, Math.min(100, (parseFloat(event.style.top) || 0) / 1440 * 100)),
        duration: Math.max(0, Math.min(1440 - (parseFloat(event.style.top) || 0),
            parseFloat(event.style.height) || 0)) / 1440 * 100,
        lane: Math.round((parseFloat(event.style.left) || 0) /
            (parseFloat(event.style.width) || 100)),
        lanes: Math.max(1, Math.round(100 / (parseFloat(event.style.width) || 100)))
    });
    function refresh() {
        const root = document.getElementById('schedule-view');
        if (!root) return;
        let rowMin = 80;
        root.querySelectorAll('.day-slots').forEach(day => {
            const events = Array.from(day.querySelectorAll('.schedule-event'));
            const allDay = events.filter(event => event.dataset.allDay === 'true');
            allDay.forEach((event, index) => event.style.setProperty('--horizontal-lane', `${index * 32 + 2}px`));
            const timed = events.filter(event => event.dataset.allDay !== 'true');
            let lanes = 1;
            // Personal schedules have no server-provided overlap lanes. Assign
            // those here only; never replace shared-calendar lane fractions.
            const needsLanes = timed.every(event => geometry(event).lanes === 1);
            const laneEnds = [];
            timed.sort((a, b) => geometry(a).start - geometry(b).start).forEach(event => {
                const value = geometry(event);
                if (needsLanes) {
                    let lane = laneEnds.findIndex(end => end <= value.start);
                    if (lane < 0) lane = laneEnds.length;
                    laneEnds[lane] = value.start + value.duration;
                    value.lane = lane;
                    value.lanes = laneEnds.length;
                }
                lanes = Math.max(lanes, value.lanes, value.lane + 1);
                event.style.setProperty('--horizontal-start', `${value.start}%`);
                event.style.setProperty('--horizontal-duration', `${value.duration}%`);
                event.style.setProperty('--horizontal-lane', `${allDay.length * 32 + value.lane * 44 + 4}px`);
            });
            rowMin = Math.max(rowMin, allDay.length * 32 + lanes * 44 + 8);
        });
        const grid = root.querySelector('.calendar-grid');
        if (grid) grid.style.setProperty('--horizontal-row-min', `${rowMin}px`);
    }
    function setMode(mode, persist = true) {
        const root = document.getElementById('schedule-view');
        if (!root) return;
        mode = mode === 'horizontal' ? 'horizontal' : 'vertical';
        const previous = root.classList.contains('schedule-horizontal') ? 'horizontal' : 'vertical';
        const grid = root.querySelector('.calendar-grid');
        if (grid && previous !== mode) {
            scrollPositions[previous] = { left: grid.scrollLeft, top: grid.scrollTop };
        }
        refresh();
        root.classList.toggle('schedule-horizontal', mode === 'horizontal');
        if (grid && previous !== mode) {
            grid.scrollLeft = scrollPositions[mode].left;
            grid.scrollTop = scrollPositions[mode].top;
        }
        root.querySelectorAll('[data-schedule-orientation]').forEach(button => {
            button.setAttribute('aria-pressed', String(button.dataset.scheduleOrientation === mode));
        });
        if (persist) remember(mode);
    }
    window.ScheduleOrientation = { refresh, setMode, geometry, preference };
    document.addEventListener('DOMContentLoaded', () => {
        const root = document.getElementById('schedule-view');
        if (!root) return;
        root.querySelectorAll('[data-schedule-orientation]').forEach(button =>
            button.addEventListener('click', () => setMode(button.dataset.scheduleOrientation)));
        setMode(preference(), false);
    });
})();
