/* global clusiveContext, PAGE_EVENT_ID, fluid */

// Set up common headers for Ajax requests for Clusive's event logging
$.ajaxPrefilter(function(options, originalOptions, jqXHR) {
    'use strict';

    options.beforeSend = function(xhr) {
        if (PAGE_EVENT_ID) {
            xhr.setRequestHeader('Clusive-Page-Event-Id', PAGE_EVENT_ID);
        }
        if (typeof clusiveContext !== 'undefined') {
            if (fluid.get(clusiveContext, 'reader.info.location.href')) {
                xhr.setRequestHeader('Clusive-Reader-Document-Href', clusiveContext.reader.info.location.href);
            }
            if (fluid.get(clusiveContext, 'reader.info.location.progression')) {
                xhr.setRequestHeader('Clusive-Reader-Document-Progression', clusiveContext.reader.info.location.progression);
            }
        }
    };
});

/* global Masonry, clusiveTTS, clusivePrefs, TOOLTIP_NAME */
/* exported getBreakpointByName, libraryMasonryEnable, libraryMasonryDisable, libraryListExpand, libraryListCollapse, clearVoiceListing */

var clusiveBreakpoints = ['xs', 'sm', 'md', 'lg', 'xl'];
var libraryMasonryApi = null;

// Returns a function, that, as long as it continues to be invoked, will not
// be triggered. The function will be called after it stops being called for
// N milliseconds. If `immediate` is passed, trigger the function on the
// leading edge, instead of the trailing.
// By David Walsh (https://davidwalsh.name/javascript-debounce-function)
function clusiveDebounce(func, wait, immediate) {
    'use strict';

    var timeout;
    return function() {
        var context = this;
        var args = arguments;
        var later = function() {
            timeout = null;
            if (!immediate) {
                func.apply(context, args);
            }
        };
        var callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);

        if (callNow) {
            func.apply(context, args);
        }
    };
}


/*
  Easing functions
  https://spicyyoghurt.com/tools/easing-functions

  t = time
  b = beginning value
  c = change in value
  d = duration
*/
function easeInOutQuad(t, b, c, d) {
    'use strict';

    if ((t /= d / 2) < 1) { return c / 2 * t * t + b; }
    return -c / 2 * ((--t) * (t - 2) - 1) + b;
}

function getBreakpointByName(name) {
    'use strict';

    var bpMin =  window.getComputedStyle(document.body).getPropertyValue('--breakpoint-' + name);
    var bpIndex = clusiveBreakpoints.indexOf(name);
    var bpNext = bpIndex < clusiveBreakpoints.length ? clusiveBreakpoints[bpIndex + 1] : null;
    var bpMax = bpNext ? (parseInt(window.getComputedStyle(document.body).getPropertyValue('--breakpoint-' + bpNext), 10) - 0.02) + 'em' : null;

    return {
        min: bpMin,
        max: bpMax
    };
}

var libraryMasonryLayout = clusiveDebounce(function() {
    'use strict';

    if (libraryMasonryApi !== null) {
        libraryMasonryApi.layout();
    }
}, 150);

function libraryMasonryEnable() {
    'use strict';

    var elem = document.querySelector('.library-grid');
    elem.classList.add('has-masonry');

    libraryMasonryApi = new Masonry(elem, {
        itemSelector: '.card-library',
        columnWidth: '.card-library',
        percentPosition: true,
        transitionDuration: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? '0' : '0.4s'
    });

    document.addEventListener('update.cisl.prefs', libraryMasonryLayout, {
        passive: true
    });

    var imgs = elem.querySelectorAll('img');
    imgs.forEach(function(img) {
        $.CFW_imageLoaded($(img), null, function() {
            libraryMasonryLayout();
        });
    });
}

function libraryListExpand() {
    'use strict';

    $('.card-toggle-btn').CFW_Collapse('show');
}

function libraryListCollapse() {
    'use strict';

    $('.card-toggle-btn').CFW_Collapse('hide');
}

// Return focus to the menu toggle control in place of the now visually hidden
// menu item in a dropdown when the confirmation modal is closed.
function confirmationRefocus($trigger, $modal) {
    'use strict';

    $modal.one('afterHide.cfw.modal', function() {
        if ($trigger.is(':hidden') && $trigger.closest('.dropdown-menu').length) {
            $trigger.closest('.dropdown-menu').siblings('[data-cfw="dropdown"]').first().trigger('focus');
        }
    });
}

function confirmationPublicationDelete() {
    'use strict';

    $(document.body).on('click', '[data-clusive="confirmPubDel"]', function(e) {
        var $trigger = $(e.currentTarget);
        var $modal = $('#modalConfirm');
        var article = $trigger.data('clusive-book-id');

        if ($trigger.data('cfw') !== 'modal') {
            e.preventDefault();

            $.get('/library/remove/confirm/' + article)
                // eslint-disable-next-line no-unused-vars
                .done(function(data, status) {
                    $modal.find('.modal-content').html(data);
                });

            confirmationRefocus($trigger, $modal);
            $trigger.CFW_Modal({
                target: '#modalConfirm',
                unlink: true,
                show: true
            });
        }
    });
}

function confirmationSharing() {
    'use strict';

    $(document.body).on('click', '[data-clusive="confirmSharing"]', function(e) {
        var $trigger = $(e.currentTarget);
        var $modal = $('#modalConfirm');
        var book = $trigger.data('clusive-book-id');

        if ($trigger.data('cfw') !== 'modal') {
            e.preventDefault();

            $.get('/library/share/' + book)
                // eslint-disable-next-line no-unused-vars
                .done(function(data, status) {
                    $modal.find('.modal-content').html(data);
                });

            confirmationRefocus($trigger, $modal);
            $trigger.CFW_Modal({
                target: '#modalConfirm',
                unlink: true,
                show: true
            });
        }
    });
}

function formFileText() {
    'use strict';

    var formFileInputUpdate = function(node) {
        var input = node;
        var $input = $(node);

        var name = (typeof input === 'object')
            && (typeof input.files === 'object')
            && (typeof input.files[0] === 'object')
            && (typeof input.files.name === 'object')
            ? input.files[0].name : $input.val();

        name = name.split('\\').pop().split('/').pop();
        if (name === null) { name = ''; }
        if (name !== '') {
            $input.closest('.form-file').find('.form-file-text').first().text(name);
        }
    };

    $(document).on('change', '.form-file-input', function() {
        formFileInputUpdate(this);
    });
    $('.form-file-input').each(function() {
        formFileInputUpdate(this);
    });
}

function starsSelectedTextUpdate(node) {
    'use strict';

    var input = node.querySelector('input[type="radio"]:checked');
    var output = node.querySelector('.stars-text-result');
    var label = input.nextElementSibling;

    if (output !== null) {
        if (label.nodeName.toLowerCase() === 'label') {
            output.innerText = label.innerText;
        } else {
            output.innerHTML = '<span class="sr-only">Unrated</span>';
        }
    }
}

function starsHoverTextUpdate(node) {
    'use strict';

    var input = node.previousElementSibling;

    if (input.nodeName.toLowerCase() !== 'input' || $(input).is('.disabled, :disabled')) {
        return;
    }

    var output = node.closest('.stars').querySelector('.stars-text-result');
    var label = input.nextElementSibling;

    if (output !== null) {
        if (label.nodeName.toLowerCase() === 'label') {
            output.innerText = label.innerText;
        }
    }
}

function starsSelectedText() {
    'use strict';

    $(document.body).on('click', '.stars input', function(e) {
        if ($(e.target).not('.disabled, :disabled')) {
            starsSelectedTextUpdate(e.target.closest('.stars'));
        }
    });
    $(document.body).on('mouseenter', '.stars label', function(e) {
        starsHoverTextUpdate(e.target);
    });
    $(document.body).on('mouseleave', '.stars label', function(e) {
        starsSelectedTextUpdate(e.target.closest('.stars'));
    });
    $('.stars').each(function() {
        starsSelectedTextUpdate(this);
    });
}

function reactDimAnimate(element, newVal) {
    'use strict';

    var start;
    var duration = 200;
    var old = parseInt(getComputedStyle(element).getPropertyValue('--dim'), 10);
    var delta = newVal - old;
    var isAnimating = false;

    function step(timestamp) {
        isAnimating = true;
        if (typeof start === 'undefined') {
            start = timestamp;
        }
        var elapsed = timestamp - start;
        var elapsedRatio  = elapsed / duration;
        elapsedRatio = elapsedRatio > 1 ? 1 : elapsedRatio;
        var update = Math.round(easeInOutQuad(elapsedRatio, old, delta, 1));

        if (update < Math.min(old, newVal)) {
            update = Math.min(old, newVal);
        } else if (update > Math.max(old, newVal)) {
            update = Math.max(old, newVal);
        }

        element.style.setProperty('--dim', update + '%');

        if (elapsed <= duration || (update > Math.min(old, newVal) && update < Math.max(old, newVal))) {
            window.requestAnimationFrame(step);
        } else {
            isAnimating = false;
        }
    }

    if (!isAnimating) {
        window.requestAnimationFrame(step);
    }
}

function reactChartHooks() {
    'use strict';

    $(document.body).on('click', '[data-react-index]', function(e) {
        var idx = e.currentTarget.dataset.reactIndex;
        var wedge = document.querySelector('.react-wedge-' + idx);

        if (e.currentTarget.checked) {
            reactDimAnimate(wedge, 100);
        } else {
            reactDimAnimate(wedge, 0);
        }
    });
}

function formRangeFontSize(range) {
    'use strict';

    var tip = range.parentNode.querySelector('.form-range-tip');
    tip.innerText = Math.round(range.value * 16) + 'px';
}

function formRangeReadSpeed(range) {
    'use strict';

    var tip = range.parentNode.querySelector('.form-range-tip');
    tip.innerText = range.value;
}

function formRangeTipPosition(range) {
    'use strict';

    var tip = range.parentNode.querySelector('.form-range-tip');
    var val = range.value;
    var min = range.min ? range.min : 0;
    var max = range.max ? range.max : 100;
    // var percentage = Number(((val - min) * 100) / (max - min));
    var ratio = Number(((val - min)) / (max - min));
    var thumbWidth = 1.25;
    var thumbHalfWidth = thumbWidth / 2;
    var leftCalc = 'calc(' + ratio + ' * ((100% - ' + thumbHalfWidth + 'rem) - ' + thumbHalfWidth + 'rem) + ' + thumbHalfWidth + 'rem)';

    tip.style.left = leftCalc;
}

function formRangeTip(range, callback) {
    'use strict';

    var tip = document.createElement('div');
    tip.classList.add('form-range-tip');
    range.after(tip);

    var tipID = $(tip).CFW_getID('clusive_range');
    tip.setAttribute('id', tipID);
    range.setAttribute('aria-describedby', tipID);

    range.parentNode.classList.add('has-form-range-tip');

    range.addEventListener('input', function() {
        formRangeTipPosition(range);
        callback(range);
    });

    window.addEventListener('resize', function() {
        formRangeTipPosition(range);
    });

    document.addEventListener('update.cisl.prefs', function() {
        window.requestAnimationFrame(function() {
            formRangeTipPosition(range);
            callback(range);
        });
    });

    formRangeTipPosition(range);
    callback(range);
}

var updateCSSVars = clusiveDebounce(function() {
    'use strict';

    // var root = document.documentElement;
    var body = document.body;
    var lineHeight = body.style.lineHeight;

    body.style.setProperty('--CT_lineHeight', lineHeight);
}, 10);


function formUseThisLinks() {
    'use strict';

    $('body').on('click', '.usethis-link', function(e) {
        var targ = $(this).data('target');
        var text = $(this).prev('.usethis-source').text();
        $('#' + targ).val(text);
        $(this).parent('.usethis-container').slideUp();
        e.preventDefault();
        return false;
    });
    $('body').on('change', '.usethis-cover', function(e) {
        var checked = $(this).prop('checked');
        console.debug('Checkbox now ', checked);
        if (checked) {
            $('#new-cover').slideUp();
            $('#cover-label').hide();
            $('#cover-input').slideUp();
            $(this).closest('.usethis-container').removeClass('highlight-undelete');
        } else {
            $('#new-cover').slideDown();
            $('#cover-label').show();
            $('#cover-input').slideDown();
            $(this).closest('.usethis-container').addClass('highlight-undelete');
        }
        e.preventDefault();
        return false;
    });
}

function setupVoiceListing() {
    'use strict';

    var container = $('#voiceListing');
    if (container.length) {
        var html = '';
        clusiveTTS.getVoicesForLanguage('en').forEach(function(voice) {
            html += '<li><button type="button" class="dropdown-item voice-button">' + voice.name + '</button></li>';
        });
        container.html(html);
    } else {
        console.debug('No voice listing element');
    }
    container.on('click', '.voice-button', function() {
        var name = this.textContent;
        console.debug('Voice choice: ', name);
        // Show voice name as dropdown label
        $('#currentVoice').html(name);
        // Mark the dropdown item as active.
        container.find('.voice-button').removeClass('active');
        $(this).addClass('active');
        // Tell ClusiveTTS to use this voice
        clusiveTTS.setCurrentVoice(name);
        // Set on the modal's model of preferences
        clusivePrefs.prefsEditorLoader.modalSettings.applier.change('modalSettings.readVoice', name);
    });
}

function clearVoiceListing() {
    'use strict';

    $('.voice-button').removeClass('active');
    $('#currentVoice').html('Choose...');
    clusiveTTS.setCurrentVoice(null);
}

function showTooltip(name) {
    'use strict';

    if (name) {
        console.debug('setting up tip: ', name);
        $(window).ready(function() {
            var tip_control = $('[data-clusive-tip-id="' + name + '"]');
            var tip_popover = $('#tip');
            var tip_placement = tip_control.attr('data-cfw-tooltip-placement');
            tip_control.CFW_Tooltip('dispose');
            tip_control.CFW_Tooltip({
                target: '#tip',
                container: '#features',
                viewport: '#features',
                trigger: 'manual',
                placement: tip_placement ? tip_placement : 'right auto',
                popperConfig: {
                    positionFixed: true
                }
            });
            setTimeout(function() {
                tip_popover.attr({
                    'role': 'status',
                    'aria-live': 'assertive',
                    'aria-atomic': 'true'
                });
                tip_control.CFW_Tooltip('show');
                tip_popover.trigger('focus');
            }, 2000);
            tip_control.one('afterHide.cfw.tooltip', function() {
                $(this).CFW_Tooltip('dispose');
                if ($(this).hasClass('feature-novis')) {
                    $('#content').trigger('focus');
                }
            });
        });
    }
}

function filterAllUpdate() {
    'use strict';

    $(document.body).on('click', '[data-clusive="filterAllUpdate"] input', function(e) {
        var $elm = $(e.currentTarget);
        var $par = $elm.closest('[data-clusive="filterAllUpdate"]');
        var $all = $par.find('[data-clusive="filterAll"]');
        var $checked = $par.find('input:checked');

        if (!$par.length || !$all.length) { return; }

        if ($elm[0] === $all[0]) {
            $par.find('input').prop('checked', false);
            $all.prop('checked', true);
        } else if (!$checked.length) {
            $all.prop('checked', true);
        } else {
            $all.prop('checked', false);
        }
    });
}

$(window).ready(function() {
    'use strict';

    document.addEventListener('update.cisl.prefs', updateCSSVars, {
        passive: true
    });
    updateCSSVars();

    formFileText();
    starsSelectedText();
    reactChartHooks();
    confirmationPublicationDelete();
    confirmationSharing();
    formUseThisLinks();
    showTooltip(TOOLTIP_NAME);
    filterAllUpdate();

    setupVoiceListing();
    window.speechSynthesis.onvoiceschanged = setupVoiceListing;

    var settingFontSize = document.querySelector('#set-size');
    if (settingFontSize !== null) {
        formRangeTip(settingFontSize, formRangeFontSize);
    }

    var settingReadSpeed = document.querySelector('#set-read-speed');
    if (settingReadSpeed !== null) {
        formRangeTip(settingReadSpeed, formRangeReadSpeed);
    }
});
