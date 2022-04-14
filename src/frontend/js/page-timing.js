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

/* global PAGE_EVENT_ID, clusiveEvents, DJANGO_USERNAME */

var PageTiming = {};

PageTiming.pageloadTime = null;
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

    if (timingSupported) {
        PageTiming.pageloadTime = performance.timing.responseEnd - performance.timing.navigationStart;
    }

    // Set up so that end time will be recorded when user turns pages.
    // https://developer.mozilla.org/en-US/docs/Web/API/Window/pagehide_event
    $(window).on('pagehide', function() {
        if (DJANGO_USERNAME) {
            console.debug("WINDOW PAGEHIDE DETECTED FOR '" + DJANGO_USERNAME + "'");
            PageTiming.reportEndTime();
        }
    });
    // Record end time when session ends
    // https://developer.mozilla.org/en-US/docs/Web/API/Navigator/sendBeacon
    // https://developer.mozilla.org/en-US/docs/Web/API/Document/visibilitychange_event.
    document.addEventListener('visibilityChange', function() {
        if (document.visibilityState === 'hidden' && DJANGO_USERNAME) {
            console.debug("DOCUMENT HIDDEN DETECTED FOR '" + DJANGO_USERNAME + "'");
            PageTiming.reportEndTime();
        }
    });

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
    } else if (PageTiming.startInactiveTime === null) {
        // Page is either blocked or blurred.  Record start of inactive time if this is new.
        PageTiming.startInactiveTime = Date.now();
        console.debug('Window went inactive at ', PageTiming.fmt(PageTiming.startInactiveTime),
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
        console.debug('Window reactivated. Was inactive from ', PageTiming.fmt(PageTiming.startInactiveTime),
            ' to ', PageTiming.fmt(now),
            '; Cumulative inactive time = ', PageTiming.totalInactiveTime / 1000, 's');
        PageTiming.startInactiveTime = null;
    }
};

// Called in document's "visibilityChange" (hidden) event or window's "pageHide"
// event, and usese the browser's asynchronous `sendBeacon()` function.
// https://developer.mozilla.org/en-US/docs/Web/API/Navigator/sendBeacon

PageTiming.reportEndTime = function() {
    'use strict';

    if (!localStorage['pageEndTime.' + PageTiming.eventId]) {
        PageTiming.recordInactiveTime();
        var duration = Date.now() - PageTiming.pageStartTime;
        var data = clusive.djangoMessageQueue.wrapMessage({
            type: 'PT',
            eventId: PageTiming.eventId,
            loadTime: PageTiming.pageloadTime,
            duration: duration,
            activeDuration: duration - PageTiming.totalInactiveTime
        });
        console.debug('Reporting page data: ', JSON.stringify(data));
        var postBody = {
            timestamp: new Date().toISOString(),
            messages: [data],
            username: DJANGO_USERNAME
        };
        var beaconResult = navigator.sendBeacon(
            '/messagequeue/', JSON.stringify(postBody)
        );
        console.debug('SENT VIA BEACON: (' + beaconResult + ')');
        console.debug(JSON.stringify(data));
        console.debug('--');
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

$(document).ready(function() {
    'use strict';

    PageTiming.trackPage(PAGE_EVENT_ID);
});
