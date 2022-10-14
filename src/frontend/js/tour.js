(function($) {
    'use strict';

    var SELECTOR_CONTAINER = '#tourContainer';
    var SELECTOR_TOUR_VISIBLE = '.popover-tour:visible';

    var tourModule = function() {
        // placeholder
    };

    tourModule.prototype = {
        // Initialize tour popover item
        // `selector` - the trigger for the popover to initialize
        prepare : function(selector) {
            if (selector) {
                var control = $(selector);
                var target = control.attr('data-cfw-popover-target');
                if ((typeof target === 'undefined' || target === false) && control.is('[data-clusive-tip-id]')) {
                    target = '#tour_' + control.attr('data-clusive-tip-id');
                }
                var placement = control.attr('data-cfw-popover-placement');
                control.CFW_Popover({
                    container: SELECTOR_CONTAINER,
                    viewport: 'window',
                    trigger: 'manual',
                    target: target,
                    placement: placement ? placement : 'right auto',
                    popperConfig: {
                        positionFixed: true
                    }
                });
            }
        },

        // Chain animations for tour items together
        // `selector` - the next popover in the chain
        chain: function(selector) {
            var $curr = $(document).find(SELECTOR_TOUR_VISIBLE);
            var $next = $(selector);

            if ($curr.length) {
                // Wait until hide animation is complete before callling show
                $curr.CFW_Popover('hide').CFW_transition(null, function() {
                    $next.CFW_Popover('show');
                    $next[0].focus();
                });
            } else {
                $next.CFW_Popover('show');
                $next[0].focus();
            }

            return false;
        },

        // Close and refocus
        // `selector` - item to focus on after popover is hidden
        closeRefocus : function(selector) {
            var $curr = $(document).find(SELECTOR_TOUR_VISIBLE);
            var $next = $(selector);

            if ($curr.length) {
                // Wait until hide animation is complete before focusing
                $curr.CFW_Popover('hide').CFW_transition(null, function() {
                    $next[0].focus();
                });
            } else {
                $next[0].focus();
            }

            return false;
        }
    };

    window.tour = tourModule.prototype;
}(jQuery));
