/**
 * session-expire-warning.js
*/

/* global PageTiming */

var SessionExpireWarning = {

    dialog: '#modalTimeout',               // Warning dialog locator
    dialogTrigger: '#modalTimeoutTrigger', // Trigger element to show/hide the warning dialog
    logoutLink: '#logoutLink',             // Element to "click" to log out
    statusUrl: '/sessions/status',         // URL to get information about session age
    reawakenUrl: '/sessions/keepalive',    // URL on the server to re-establish awakeness.
    tickPeriod: 10000,                     // how often to wake up and check the time (in ms)
    lastStatus: 'ACTIVE',                  // status as of previous check.
    timer: null,                           // Timer for periodic checks
    ignoreDialogClose: false,              // Set temporarily to true when we're programmatically closing the dialog
    lastFocus: null,                       // Store last focused element (if any) when modal is shown

    init: function() {
        'use strict';

        // If there's no warning dialog on this page, then don't do anything.
        if (!$(SessionExpireWarning.dialogTrigger).length > 0) {
            console.debug('SEW not starting, no dialog on this page');
            return;
        }

        // We use an interval timer since one-shot timers might never fire if, say, laptop is closed for a while.
        SessionExpireWarning.timer = setInterval(SessionExpireWarning.checkSessionAge, SessionExpireWarning.tickPeriod);
        console.debug('SEW Starting Timer = ', SessionExpireWarning.timer);
        $(SessionExpireWarning.dialog).on('afterHide.cfw.modal', SessionExpireWarning.dialogClosed);

        // Restore focus to previous item after dialog is hidden
        $(SessionExpireWarning.dialog).on('afterHide.cfw.modal', function() {
            if (SessionExpireWarning.lastFocus !== null) {
                SessionExpireWarning.lastFocus.focus();
            }
            SessionExpireWarning.lastFocus = null;
        });
    },

    // Sends request to the server if necessary; returns a promise that will resolve after this check.
    // If no check is needed, resolves immediately.
    checkSessionAge: function() {
        'use strict';

        var check = window.localStorage.getItem('SEW-check-in-progress');
        if (check) {
            var lockAge = new Date().getTime() - parseInt(check, 10);
            if (lockAge > SessionExpireWarning.tickPeriod) {
                // Server round-trip should not take a full tick cycle.
                // May be a left over due to browser or network problems.
                console.warn('SEW clearing old in-progress indication');
                window.localStorage.setItem('SEW-check-in-progress', '');
            } else {
                console.debug('SEW check already in progress, skipping check.', check);
                return;
            }
        }

        var nextcheck = SessionExpireWarning.getNextCheckTime();
        var now = new Date().getTime();
        if (nextcheck !== null && now < nextcheck) {
            // console.debug('SEW Time remaining until check: ', Math.ceil((nextcheck - now) / 1000), 's');
            SessionExpireWarning.updateDisplay();
            return;
        }

        SessionExpireWarning.checkWithServer(false);
    },

    // Contacts the server's status URL.
    // If 'awaken' arg is true, will cause the session to be non-idle; otherwise just asks.
    // Returns a Promise which will resolve after the server round-trip.
    checkWithServer: function(reawaken) {
        'use strict';

        window.localStorage.setItem('SEW-check-in-progress', String(new Date().getTime()));
        console.debug(reawaken ? 'SEW sending AWAKE to server' : 'SEW Checking with server');
        var url = reawaken ? SessionExpireWarning.reawakenUrl : SessionExpireWarning.statusUrl;
        $.get(url).then(function(data) {
            console.debug('SEW Got status: ', data);
            var secondsUntilNextCheck;
            if (data.status === 'ACTIVE') {
                // No need to check again until this session might become idle.
                secondsUntilNextCheck = data.idleLimit - data.idleTime;
            } else if (data.status === 'IDLE') {
                // Don't check again until timeout time.
                secondsUntilNextCheck = data.timeoutLimit - data.idleTime;
            }
            console.debug('SEW next check scheduled for ', secondsUntilNextCheck, ' seconds from now');
            window.localStorage.setItem('SEW-status', data.status);
            window.localStorage.setItem('SEW-next-check', String(new Date().getTime() + secondsUntilNextCheck * 1000));
            window.localStorage.setItem('SEW-check-in-progress', '');
            SessionExpireWarning.updateDisplay();
        }, function(err) {
            console.error('SEW Got error: ', err);
            window.localStorage.setItem('SEW-check-in-progress', '');
        });
    },

    // Show or hide the warning modal, or logout, as appropriate if status has changed
    updateDisplay: function() {
        'use strict';

        var status = window.localStorage.getItem('SEW-status');
        if (status && status !== SessionExpireWarning.lastStatus) {
            console.debug('SEW Transitioning from ', SessionExpireWarning.lastStatus, ' to ', status);
            SessionExpireWarning.lastStatus = status;
            if (status === 'ACTIVE') {
                SessionExpireWarning.onActive();
            } else if (status === 'IDLE') {
                SessionExpireWarning.onIdle();
            } else if (status === 'TIMEOUT' || status === 'EXPIRED') {
                SessionExpireWarning.onTimeout();
            }
        }
    },

    dialogClosed: function() {
        'use strict';

        // The dialog box may be closed in two ways:
        // 1. Programmatically closed via clearWarning() method due to activity in another window.
        // 2. Closed by the user clicking on it, in which case we need to notify the server of new activity.
        if (SessionExpireWarning.ignoreDialogClose) {
            // console.debug('SEW Dialog closed programmatically, not notifying server');
            SessionExpireWarning.ignoreDialogClose = false;
        } else {
            // console.debug('SEW User closed the warning dialog, notifying server of activity');
            SessionExpireWarning.iAmHere();
        }
    },

    onActive: function() {
        'use strict';

        PageTiming.blocked(false);
        if ($(SessionExpireWarning.dialog + ':visible').length) {
            console.debug('SEW closing');
            SessionExpireWarning.ignoreDialogClose = true;
            $(SessionExpireWarning.dialogTrigger).CFW_Modal('hide');
        }
    },

    onIdle: function() {
        'use strict';

        PageTiming.blocked(true);
        SessionExpireWarning.lastFocus = document.activeElement;
        $(SessionExpireWarning.dialogTrigger).CFW_Modal('show');
    },

    onTimeout: function() {
        'use strict';

        console.info('SEW TODO session TIMEOUT');
        SessionExpireWarning.cleanup();
        // window.location = SessionExpireWarning.logoutUrl;
        $(SessionExpireWarning.logoutLink).click();
    },

    // Called when user closes the "Are you there" dialog, confirming their presence.
    iAmHere: function() {
        'use strict';

        SessionExpireWarning.checkWithServer(true);
    },

    getNextCheckTime: function() {
        'use strict';

        var val = window.localStorage.getItem('SEW-next-check');
        if (val) { return parseInt(val, 10); }
        return null;
    },

    cleanup: function() {
        'use strict';

        console.debug('SEW cleaning up');
        window.localStorage.removeItem('SEW-status');
        window.localStorage.removeItem('SEW-next-check');
        window.localStorage.removeItem('SEW-check-in-progress');
    }

};

$(function() {
    'use strict';

    SessionExpireWarning.init();
});
