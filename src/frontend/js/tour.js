(function($) {
    'use strict';

    var SELECTOR_START_BTN = '#tourStart';
    var SELECTOR_CONTAINER = '#tourContainer';
    var SELECTOR_TOUR_VISIBLE = '.popover-tour:visible';
    var SELECTOR_NAV_PREV = '.chain-prev';
    var SELECTOR_NAV_NEXT = '.chain-next';
    var SELECTOR_NAV_STEP = '.chain-step';

    var CLASS_TOUR = 'touring';

    var BTN_PREV = '<button type="button" class="btn btn-primary" onclick="tour.chainPrev();"><span class="fa fa-chevron-left" aria-hidden="true"></span> <span aria-hidden="true">Prev</span><span class="sr-only">Previous</span></button>';
    var BTN_NEXT = '<button type="button" class="btn btn-secondary" onclick="tour.chainNext();">Next <span class="fa fa-chevron-right" aria-hidden="true"></span></button>';
    var BTN_END = '<button type="button" class="btn btn-secondary" onclick="tour.chainEnd();">End</button>';

    var tourModule = function() {
        this.inTour = false;
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
                var next = document.querySelector('#tour_' + name);
                next.focus();
                $control[0].scrollIntoView({
                    block: 'center',
                    behavior: cisl.prefs.userPrefersReducedMotion() ? 'auto' : 'smooth'
                });
                if (typeof window.parent.clusiveEvents === 'object' && typeof window.parent.clusiveEvents.addTipViewToQueue === 'function') {
                    window.parent.clusiveEvents.addTipViewToQueue(name);
                }
            });
            setTimeout(function() {
                $control.CFW_Popover('show');
            }, 2000);
        },

        // Chain animations for tour items together
        // `selector` - the next popover in the chain
        chain: function(name) {
            var that = this;
            var $curr = $(document).find(SELECTOR_TOUR_VISIBLE);
            var $next = $('#tour_' + name);

            var $trigger = $next.data('cfw.popover').$element;

            var showStart = function() {
                that.inTour = true;
                document.body.classList.add(CLASS_TOUR);
                that.chainUpdate(name);
                $trigger.one('afterShow.cfw.popover', showComplete);
                $trigger.CFW_Popover('show');
            };

            var showComplete = function() {
                $next[0].focus();
                $trigger[0].scrollIntoView({
                    block: 'center',
                    behavior: cisl.prefs.userPrefersReducedMotion() ? 'auto' : 'smooth'
                });
                if (typeof window.parent.clusiveEvents === 'object' && typeof window.parent.clusiveEvents.addTipViewToQueue === 'function') {
                    window.parent.clusiveEvents.addTipViewToQueue(name);
                }
            };

            // Hide tip/tour tooltip if showing
            $('#tip').CFW_Tooltip('hide');

            if ($curr.length) {
                // Wait until hide animation is complete before calling show
                $curr.CFW_Popover('hide').CFW_transition(null, function() {
                    showStart();
                });
            } else {
                showStart();
            }
        },

        // Close and refocus
        // `selector` - item to focus on after popover is hidden
        closeRefocus : function(selector) {
            var that = this;
            var $curr = $(document).find(SELECTOR_TOUR_VISIBLE);
            var $next = $(selector);

            var hideStart = function() {
                that.inTour = false;
                document.body.classList.remove(CLASS_TOUR);
                $next[0].focus();
            };

            if ($curr.length) {
                // Wait until hide animation is complete before focusing
                $curr.CFW_Popover('hide').CFW_transition(null, function() {
                    hideStart();
                });
            } else {
                hideStart();
            }
        },

        // Find available tour items - those with a 'visible' trigger element
        getAvailableChain : function() {
            var available = [];
            if (TOUR_LIST !== null && TOUR_LIST.length) {
                TOUR_LIST.forEach(function(name) {
                    if ($.CFW_isVisible(document.querySelector('[data-clusive-tip-id="' + name + '"]'))) {
                        available.push(name);
                    }
                });
            }
            return available;
        },

        getCurrentChain : function() {
            var $curr = $(document).find(SELECTOR_TOUR_VISIBLE);
            if ($curr.length) {
                return {
                    elm: $curr[0],
                    name: $curr[0].id.replace(/^tour_/, '')
                };
            }
            return null;
        },

        chainStart : function() {
            var available = this.getAvailableChain();
            if (available.length) {
                // Show first in chain
                this.chain(available[0]);
            } else {
                // Show tooltip message
                var msg = "There are currently no tool tips available on this page.";
                $(SELECTOR_START_BTN).CFW_Tooltip({
                    title: msg,
                    container: "body",
                    placement: "reverse",
                    dispose: true
                }).CFW_Tooltip('show');
            }
        },

        chainPrev : function() {
            var curr = this.getCurrentChain();
            var available = this.getAvailableChain();
            var step = available.indexOf(curr.name);
            this.chain(available[step - 1]);
        },

        chainNext : function() {
            var curr = this.getCurrentChain();
            var available = this.getAvailableChain();
            var step = available.indexOf(curr.name);
            this.chain(available[step + 1]);
        },

        chainEnd : function() {
            this.closeRefocus(SELECTOR_START_BTN);
        },

        chainUpdate : function(name) {
            var elm = document.querySelector('#tour_' + name);
            var available = this.getAvailableChain();
            var step = available.indexOf(name) + 1;
            var total = available.length;

            elm.querySelector(SELECTOR_NAV_STEP).innerHTML = step + '/' + total;
            elm.querySelector(SELECTOR_NAV_PREV).innerHTML = step > 1 ? BTN_PREV : '';
            elm.querySelector(SELECTOR_NAV_NEXT).innerHTML = step >= total ? BTN_END : BTN_NEXT;
        }
    };

    window.tour = tourModule.prototype;
}(jQuery));
