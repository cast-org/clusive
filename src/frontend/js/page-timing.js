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

/* global PAGE_EVENT_ID, clusiveEvents, DJANGO_USERNAME, DJANGO_CSRF_TOKEN */

var PageTiming = {};

PageTiming.pageloadTime = null;
PageTiming.startInactiveTime = null;
PageTiming.totalInactiveTime = 0;
PageTiming.pageBlocked = false;
PageTiming.lastSeenAwakeTime = null;
PageTiming.awakeCheckInterval = 5000;  // Check for awakeness every 5 seconds
PageTiming.awakeCheckTimer = null;
PageTiming.localStorageKey = 'pageEndTime';

/**
 * Call to initiate time tracking of this page.
 * @param {string} eventId the ID that we use to identify this page view event to the server.
 * @returns {null} nothing
 */
PageTiming.trackPage = function(eventId) {
    'use strict';

    PageTiming.eventId = eventId;

    console.debug('PageTiming: Started tracking page ', eventId);

    var currentTime = Date.now();
    var timingSupported = PageTiming.isTimingSupported();

    // Tracking for visible/invisible time
    if (document.hasFocus !== 'undefined') {
        PageTiming.handleFocusChange();
        $(window).on('focusin focusout', PageTiming.handleFocusChange);
    } else {
        console.warn('PageTiming: Browser doesn\'t support focus checking; hidden time won\'t be reported.');
    }

    // Interval timer to monitor laptop going to sleep.
    PageTiming.awakeCheckTimer = setInterval(PageTiming.checkAwakeness, PageTiming.awakeCheckInterval);

    if (timingSupported) {
        PageTiming.pageloadTime = performance.timing.responseEnd - performance.timing.navigationStart;
    }

    // Set up so that end time will be recorded when user turns pages.
    // https://developer.mozilla.org/en-US/docs/Web/API/Window/pagehide_event
    $(window).on('pagehide', PageTiming.windowEventListener);

    // Save current time - end time will be calculated as an offset to this.
    PageTiming.pageStartTime = currentTime;
};

PageTiming.windowEventListener = function (event) {
    if (DJANGO_USERNAME) {
        console.debug("PageTiming: window pagehide detected for '" + DJANGO_USERNAME + "'");
        PageTiming.reportEndTime();
    }
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

PageTiming.createEndTimeMessage = function () {
    PageTiming.recordInactiveTime();
    var duration = Date.now() - PageTiming.pageStartTime;
    return {
        type: 'PT',
        eventId: PageTiming.eventId,
        loadTime: PageTiming.pageloadTime,
        duration: duration,
        activeDuration: duration - PageTiming.totalInactiveTime
    };
};

// Called in document's "visibilityChange" (hidden) event or window's "pageHide"
// event, and uses the browser's asynchronous `sendBeacon()` function.
// https://developer.mozilla.org/en-US/docs/Web/API/Navigator/sendBeacon
PageTiming.reportEndTime = function() {
    'use strict';

    var message = clusive.djangoMessageQueue.wrapMessage(PageTiming.createEndTimeMessage());
    console.debug('PageTiming: Reporting page data: ', JSON.stringify(message));
    var postForm = new FormData();
    postForm.append('csrfmiddlewaretoken', DJANGO_CSRF_TOKEN);
    postForm.append('timestamp', new Date().toISOString());
    postForm.append('messages', JSON.stringify([message]));
    postForm.append('username', DJANGO_USERNAME);
    var beaconResult = navigator.sendBeacon('/messagequeue/', postForm);

    // `beaconResult` is `true` or `false` depending on whether the browser
    // successfully queued the request or not.  (It will fail only if the
    // size of `postForm`, exceeds the browser's limit, which is unlikely
    // here).  However, `true` does not mean that the request was sent nor
    // successfully handled by Clusive.  And, there is no way to tell
    // if Clusive received the request.
    // https://www.w3.org/TR/beacon/#return-values
    console.debug(`PageTiming: Queued ${PageTiming.eventId} via sendBeacon(): ${beaconResult}`);
};

// For clusive-message-queue's logout handler.
PageTiming.logoutEndTime = function() {
    'use strict';

    // Stop event handling via sendBeacon()
    $(window).off('pagehide', PageTiming.windowEventListener);

    // Add the PageEnd event to the messagequeue.
    clusiveEvents.messageQueue.add(PageTiming.createEndTimeMessage());
    console.debug(`PageTiming: Queued ${PageTiming.eventId} via clusiveEvents.messageQueue.`);
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
