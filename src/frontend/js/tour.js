(function($) {
    'use strict';

    var SELECTOR_CONTAINER = '#tourContainer';
    var SELECTOR_TOUR_VISIBLE = '.popover-tour:visible';
    var CLASS_TOUR = 'touring';

    var tourModule = function() {
        // placeholder
    };

    tourModule.prototype = {
        // Initialize tour popover item
        // `name` - name (via data attribute) trigger for the popover to initialize
        prepare : function(name) {
            var $control = $('[data-clusive-tip-id="' + name + '"]');
            if (!$control.length) { return; }

            var target = $control.attr('data-cfw-popover-target');
            if ((typeof target === 'undefined' || target === false) && $control.is('[data-clusive-tip-id]')) {
                target = '#tour_' + $control.attr('data-clusive-tip-id');
            }
            var placement = $control.attr('data-cfw-popover-placement');
            $control.CFW_Popover({
                container: SELECTOR_CONTAINER,
                viewport: 'window',
                trigger: 'manual',
                target: target,
                placement: placement ? placement : 'right auto',
                popperConfig: {
                    positionFixed: true
                }
            });
        },

        // Show a singleton from the tour
        singleton: function(name) {
            var $control = $('[data-clusive-tip-id="' + name + '"]');
            if (!$control.length) { return; }

            document.body.classList.remove(CLASS_TOUR);
            $control.one('afterShow.cfw.popover', function() {
                popoverHelpDialog = $('#tour_' + name).focus();
                if (popoverHelpDialog.is(':visible')) {
                    window.parent.clusiveEvents.addTipViewToQueue(name);
                }
            });
            setTimeout(function() {
                $control.CFW_Popover('show');
            }, 2000);
        },

        // Chain animations for tour items together
        // `selector` - the next popover in the chain
        chain: function(selector) {
            var $curr = $(document).find(SELECTOR_TOUR_VISIBLE);
            var $next = $(selector);

            // Hide tip/tour tooltip if showing
            $('#tip').CFW_Tooltip('hide');

            if ($curr.length) {
                // Wait until hide animation is complete before callling show
                $curr.CFW_Popover('hide').CFW_transition(null, function() {
                    document.body.classList.add(CLASS_TOUR);
                    $next.CFW_Popover('show');
                    $next[0].focus();
                });
            } else {
                document.body.classList.add(CLASS_TOUR);
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
                    document.body.classList.remove(CLASS_TOUR);
                    $next[0].focus();
                });
            } else {
                document.body.classList.remove(CLASS_TOUR);
                $next[0].focus();
            }

            return false;
        }
    };

    window.tour = tourModule.prototype;
}(jQuery));
