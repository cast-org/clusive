/* global notify */

// Super simple notification
(function($) {
    'use strict';

    var SELECTOR_CONTAINER = '#notifyContainer';

    var CLASS_FADE = 'fade';
    var CLASS_IN = 'in';

    var notifyModule = function() {
        // placeholder
    };

    notifyModule.prototype = {
        show : function(msg) {
            var $item = $('<div class="notify" aria-live="assertive" aria-atomic="true"></div>');
            $item.html(msg);
            $(SELECTOR_CONTAINER).append($item);

            var complete = function() {
                setTimeout(function() {
                    notify.hide($item);
                }, 3000);
            };

            $item.addClass(CLASS_FADE);
            $.CFW_reflow($item); // Reflow for transition
            $item.addClass(CLASS_IN);
            $item.CFW_transition(null, complete);
        },

        hide : function($item) {
            var complete = function() {
                $item.remove();
            };

            $item.removeClass(CLASS_IN);
            $item.CFW_transition(null, complete);
        }
    };

    window.notify = notifyModule.prototype;
}(jQuery));
