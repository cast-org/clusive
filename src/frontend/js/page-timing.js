/**
 * page-timing.js
 *
 * Tracks three pieces of timing information about pages to be reported to the server:
 *   How long the page takes to load
 *   How long the page remains loaded before the user leaves the page or its window is closed.
 *   How much of that time the window was not actually focused, or had the timeout warning modal showing.
 *
 */
/* globals: PageTiming */

var PageTiming = {};

PageTiming.startInactiveTime = null;
PageTiming.totalInactiveTime = 0;
PageTiming.pageBlocked = false;
PageTiming.lastSeenAwakeTime = null;
PageTiming.awakeCheckInterval = 5000;  // Check for awakeness every 5 seconds
PageTiming.awakeCheckTimer = null;

/**
 * Call to initiate time tracking of this page.
 * @param {string} eventId the ID that we use to identify this page view event to the server.
 * @returns {null} nothing
 */
PageTiming.trackPage = function(eventId) {
    'use strict';

    PageTiming.eventId = eventId;

    console.debug('Started tracking page ', eventId);

    var currentTime = Date.now();
    var timingSupported = PageTiming.isTimingSupported();

    // Tracking for visible/invisible time
    if (document.hasFocus !== 'undefined') {
        PageTiming.handleFocusChange();
        $(window).on('focusin focusout', PageTiming.handleFocusChange);
    } else {
        console.warn('Browser doesn\'t support focus checking; hidden time won\'t be reported.');
    }

    // Interval timer to monitor laptop going to sleep.
    PageTiming.awakeCheckTimer = setInterval(PageTiming.checkAwakeness, PageTiming.awakeCheckInterval);

    var loadTime = null;

    if (timingSupported) {
        loadTime = performance.timing.responseEnd - performance.timing.navigationStart;
    }

    // Set up so that end time will be recorded
    $(window).on('pagehide', function() { PageTiming.saveEndTime(eventId); });

    // Save current time - end time will be calculated as an offset to this.
    PageTiming.pageStartTime = currentTime;
};

PageTiming.checkAwakeness = function() {
    'use strict';

    var curTime = Date.now();
    var lastAwake = PageTiming.lastSeenAwakeTime;
    PageTiming.lastSeenAwakeTime = curTime;
    console.debug('LastAwake was ', PageTiming.fmt(lastAwake), '; setting to ', PageTiming.fmt(curTime));
    if (lastAwake === null || curTime-lastAwake < PageTiming.awakeCheckInterval * 2) {
        // Looks like we're getting regular pings, no action needed
        console.debug('ping ... looks like we\'re still awake at ', PageTiming.fmt(curTime),
            ' blocked? ', PageTiming.pageBlocked, '; focused? ', document.hasFocus());
    } else {
        // Last awake time was too long ago, record preceding interval as having been asleep.
        console.debug('Computer woke up from sleep that started around ' + PageTiming.fmt(lastAwake));
        if (PageTiming.startInactiveTime === null) {
            //   do we need this?:  || PageTiming.startInactiveTime > lastAwake
            PageTiming.startInactiveTime = lastAwake; // might want to add a fraction of interval
            console.debug('Set startInactiveTime to ', PageTiming.fmt(lastAwake));
        } else {
            console.debug('startInactiveTime is already set to ', PageTiming.fmt(PageTiming.startInactiveTime),
                ' so not resetting to ', PageTiming.fmt(lastAwake));
        }
        PageTiming.handleFocusChange();
    }
};

PageTiming.blocked = function(isBlocked) {
    'use strict';

    PageTiming.pageBlocked = isBlocked;
    PageTiming.handleFocusChange();
};

PageTiming.handleFocusChange = function() {
    'use strict';

    if (!PageTiming.pageBlocked && document.hasFocus()) {
        // page is active.  If it was inactive before, record duration of inactivity.
        PageTiming.recordInactiveTime();
    } else {
        // Page is either blocked or blurred.  Record start of inactive time if this is new.
        if (PageTiming.startInactiveTime === null) {
            PageTiming.startInactiveTime = Date.now();
            console.debug('Window went inactive at ', PageTiming.fmt(PageTiming.startInactiveTime),
                ' with cumulative ', PageTiming.totalInactiveTime / 1000, 's');
        }
    }
};

PageTiming.fmt = function(unixtime) {
    'use strict';

    if (unixtime) {
        return new Date(unixtime).toLocaleTimeString();
    } else {
        return 'null';
    }
};

PageTiming.recordInactiveTime = function() {
    'use strict';

    if (PageTiming.startInactiveTime !== null) {
        var now = Date.now();
        PageTiming.totalInactiveTime += (now - PageTiming.startInactiveTime);
        console.debug('Window reactivated. Was inactive from ', PageTiming.fmt(PageTiming.startInactiveTime),
            ' to ', PageTiming.fmt(now));
        console.debug('Cumulative inactive time = ', PageTiming.totalInactiveTime / 1000, 's');
        PageTiming.startInactiveTime = null;
    }
};

// Called in page's "pagehide" event:
// saves a timestamp to local storage as the page gets unloaded
PageTiming.saveEndTime = function(eventId) {
    'use strict';

    if (!localStorage['pageEndTime.' + eventId]) {
        console.debug('Saving end time for page: ', PageTiming.fmt(Date.now()));
        // TODO localStorage['pageEndTime.' + eventId] = Date.now();
        PageTiming.recordInactiveTime();
        // TODO localStorage['pageInactiveTime.' + eventId] = PageTiming.totalInactiveTime;
    } else {
        console.warn('Pagehide event received, but end time was already recorded');
    }
};

// Test if browser supports the timing API
PageTiming.isTimingSupported = function() {
    'use strict';

    try {
        return 'performance' in window && 'timing' in window.performance;
    } catch (e) {
        return false;
    }
};
