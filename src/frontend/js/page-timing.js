/**
 * page-timing.js
 *
 * Tracks three pieces of timing information about pages to be reported to the server:
 *   How long the page takes to load
 *   How long the page remains loaded before the user leaves the page or its window is closed.
 *   How much of that time the window was not actually focused, or had a timeout warning modal showing.
 *
 * Requires that a global variable "PAGE_EVENT_ID" has been set by the template.
 * This is an arbitrary string that will be sent back to the server to let it know which page view the timing
 * information is for.
 *
 */

/* global PAGE_EVENT_ID, clusiveEvents */

var PageTiming = {};

PageTiming.pageloadTime = null;
PageTiming.startInactiveTime = null;
PageTiming.totalInactiveTime = 0;
PageTiming.pageBlocked = false;
PageTiming.lastSeenAwakeTime = null;
PageTiming.awakeCheckInterval = 5000;  // Check for awakeness every 5 seconds
PageTiming.awakeCheckTimer = null;
PageTiming.performanceObserver = null;

/**
 * Call to initiate time tracking of this page.
 * @param {string} eventId the ID that we use to identify this page view event to the server.
 * @returns {null} nothing
 */
PageTiming.trackPage = function(eventId) {
    'use strict';

    PageTiming.eventId = eventId;

    console.debug('PageTiming: Started tracking page ', eventId);

    // First choice:  Use PerformanceObserver and PerformanceNavigationTiming
    // APIs if available -- check is made in usePerformanceObserver() and
    // observer is returned if check succeeds.
    PageTiming.performanceObserver = PageTiming.usePerformanceObserver();
    if (!PageTiming.performanceObserver) {
        // Second choice: if deprecated Performance.timing is available, use
        // it to acquire the page load time.
        if ('performance' in window && 'timing' in window.performance) {
            PageTiming.pageloadTime = window.performance.timing.responseEnd - window.performance.timing.navigationStart;
            console.log(`PageTiming: load time via Performance.timing for ${eventId}: ${PageTiming.pageloadTime}`);
        }
    }
    var currentTime = Date.now();

    // Tracking for visible/invisible time
    if (document.hasFocus !== 'undefined') {
        PageTiming.handleFocusChange();
        $(window).on('focusin focusout', PageTiming.handleFocusChange);
    } else {
        console.warn('PageTiming: Browser doesn\'t support focus checking; hidden time won\'t be reported.');
    }

    // Interval timer to monitor laptop going to sleep.
    PageTiming.awakeCheckTimer = setInterval(PageTiming.checkAwakeness, PageTiming.awakeCheckInterval);

    // Set up so that end time will be recorded
    $(window).on('pagehide', function() { PageTiming.reportEndTime(); });

    // Save current time - end time will be calculated as an offset to this.
    PageTiming.pageStartTime = currentTime;
};

PageTiming.checkAwakeness = function() {
    'use strict';

    var curTime = Date.now();
    var lastAwake = PageTiming.lastSeenAwakeTime;
    PageTiming.lastSeenAwakeTime = curTime;
    if (lastAwake === null || curTime - lastAwake < PageTiming.awakeCheckInterval * 2) {
        // Looks like we're getting regular pings, no action needed
        // console.debug('Browser is awake at ', PageTiming.fmt(curTime),
        //     ' blocked? ', PageTiming.pageBlocked, '; blurred? ', !document.hasFocus());
    } else {
        // Last awake time was too long ago, record preceding interval as having been asleep.
        console.debug('PageTiming: Computer woke up from sleep that started around ' + PageTiming.fmt(lastAwake));
        if (PageTiming.startInactiveTime === null) {
            //   do we need this?:  || PageTiming.startInactiveTime > lastAwake
            PageTiming.startInactiveTime = lastAwake; // might want to add a fraction of interval
            console.debug('PageTiming: Set startInactiveTime to ', PageTiming.fmt(lastAwake));
        } else {
            console.debug('PageTiming: startInactiveTime is already set to ', PageTiming.fmt(PageTiming.startInactiveTime),
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
    } else if (PageTiming.startInactiveTime === null) {
        // Page is either blocked or blurred.  Record start of inactive time if this is new.
        PageTiming.startInactiveTime = Date.now();
        console.debug('PageTiming: Window went inactive at ', PageTiming.fmt(PageTiming.startInactiveTime),
            ' with cumulative ', PageTiming.totalInactiveTime / 1000, 's');
    }
};

PageTiming.fmt = function(unixtime) {
    'use strict';

    if (unixtime) {
        return new Date(unixtime).toLocaleTimeString();
    }
    return 'null';
};

PageTiming.recordInactiveTime = function() {
    'use strict';

    if (PageTiming.startInactiveTime !== null) {
        var now = Date.now();
        PageTiming.totalInactiveTime += now - PageTiming.startInactiveTime;
        console.debug('PageTiming: Window reactivated. Was inactive from ', PageTiming.fmt(PageTiming.startInactiveTime),
            ' to ', PageTiming.fmt(now),
            '; Cumulative inactive time = ', PageTiming.totalInactiveTime / 1000, 's');
        PageTiming.startInactiveTime = null;
    }
};

// Called in page's "pagehide" event
PageTiming.reportEndTime = function() {
    'use strict';
    console.debug(`PageTiming: reportEndTime() for ${PageTiming.eventId}, load time is ${PageTiming.pageloadTime}`);
    if (!localStorage['pageEndTime.' + PageTiming.eventId]) {
        PageTiming.recordInactiveTime();
        var duration = Date.now() - PageTiming.pageStartTime;
        var activeTime = duration - PageTiming.totalInactiveTime;
        if (activeTime < 0) {
            activeTime = 0;
            console.debug(`PageTiming: detected negative active duration, duration is ${duration}, inactive time is ${PageTiming.totalInactiveTime}`);
        }
        var data = {
            type: 'PT',
            eventId: PageTiming.eventId,
            loadTime: PageTiming.pageloadTime,
            duration: duration,
            activeDuration: activeTime,
        };
        console.debug('PageTiming: Reporting page data: ', data);
        clusiveEvents.messageQueue.add(data);
    } else {
        console.warn('PageTiming: Pagehide event received, but end time was already recorded');
    }
    // Done with the observer, if any.
    if (PageTiming.performanceObserver) {
        PageTiming.performanceObserver.disconnect();
        PageTiming.performanceObserver = null;
    }
};

// If browser supports both of the PerformanceObserver and the
// PerformanceNavigationTiming APIs, set up a PerformanceObserver to observe the
// navigation events to get the page's load time.
// https://developer.mozilla.org/en-US/docs/Web/API/PerformanceObserver
// https://developer.mozilla.org/en-US/docs/Web/API/PerformanceNavigationTiming
PageTiming.usePerformanceObserver = function () {
    var observer = null;
    if (window.PerformanceObserver && window.PerformanceNavigationTiming) {
        observer = new PerformanceObserver(function (perfEntries) {
            PageTiming.processNavEntries(perfEntries);
        });
        observer.observe({ type: "navigation", buffered: true });
    };
    return observer;
};

// Called from the PerformanceObserver callback to get the page load time.
// See PageTiming.usePerformanceObserver(), above.
PageTiming.processNavEntries = function (perfEntries) {
    'use strict';

    var navEntries = perfEntries.getEntries();
    navEntries.some(function (entry) {
        // Only interested in navigation entries for this page.
        if (entry.name === document.URL) {
            PageTiming.pageloadTime = entry.responseEnd - entry.startTime;
            console.log(`PageTiming: load time via PerformanceNavigationTiming for ${PageTiming.eventId}: ${PageTiming.pageloadTime}`);
            return true;
        } else {
            return false;
        }
    });
};

$(document).ready(function() {
    'use strict';

    PageTiming.trackPage(PAGE_EVENT_ID);
});
