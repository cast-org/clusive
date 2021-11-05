/* global Masonry, clusiveContext, PAGE_EVENT_ID, fluid, TOOLTIP_NAME, load_translation */
/* exported updateLibraryData, getBreakpointByName, libraryMasonryEnable, libraryMasonryDisable, libraryListExpand, libraryListCollapse, clearVoiceListing, contextLookup, contextTranslate */

// Set up common headers for Ajax requests for Clusive's event logging
$.ajaxPrefilter(function(options) {
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
    return -c / 2 * (--t * (t - 2) - 1) + b;
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

    if (elem === null) { return; }

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

function getLoadingMsg() {
    'use strict';

    return '' +
    '<div class="text-center py-0_5">' +
    '    <strong>Loading...</strong>' +
    '    <div class="loader-circle" role="status" aria-hidden="true"></div>' +
    '</div>';
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

        // Replace modal body and footer after hide
        $modal.on('afterHide.cfw.modal', function() {
            $modal.find('.modal-body').replaceWith(getLoadingMsg());
            $modal.find('.modal-footer').remove();
        });

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

        // Replace form after hide
        $modal.on('afterHide.cfw.modal', function() {
            $modal.find('form').replaceWith(getLoadingMsg());
        });

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
    var $button = $(node).closest('form').find('button[type="submit"]');

    if (output !== null) {
        if (label.nodeName.toLowerCase() === 'label') {
            output.innerText = label.innerText;
            $button.prop('disabled', false);
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
    $('#star_rating_panel form').on('submit', function(e) {
        e.preventDefault();
        var data = $(this).serialize();
        $.ajax({
            type: 'POST',
            url: '/set_star_rating',
            data: data
        }).done(function(html) {
            $('#star_rating_panel').replaceWith(html);
            starsSelectedTextUpdate($('#star_rating_panel .stars')[0]);
        }).fail(function(err) {
            console.error('Failed sending star rating results: ', err);
        });
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

function showTooltip(name) {
    'use strict';

    if (name) {
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
                if (tip_control.is(':visible')) {
                    tip_popover.attr({
                        'role': 'status',
                        'aria-live': 'assertive',
                        'aria-atomic': 'true'
                    });
                    tip_control.CFW_Tooltip('show');
                    tip_popover.trigger('focus');
                    window.parent.clusiveEvents.addTipViewToQueue(name);
                }
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

// Determine if page has bricks layout
function hasBricksLayout() {
    'use strict';

    var regex = new RegExp('/bricks/');
    return regex.test(window.location.pathname);
}

// Determine if this page has any filtering active. It does if there is an unchecked "All" checkbox.
function hasActiveFilters() {
    'use strict';

    return $('[data-clusive="filterAll"]').not(':checked').length > 0;
}

// Look at the filter checkboxes and update the given URI with appropriate arguments to reflect them.
function addFilterArgs(uri) {
    'use strict';

    var params = uri.searchParams;
    $('[data-clusive="filterAllUpdate"]').each(function() {
        var $par = $(this);
        var $all = $par.find('[data-clusive="filterAll"]');
        var name = $all.attr('name');
        if ($all.is(':checked')) {
            params.delete(name);
        } else {
            var values = [];
            $par.find('input:checked').each(function() {
                values.push($(this).val());
            });
            params.set(name, values.join(','));
        }
    });
    return uri;
}

// AJAX update the library cards based on the current collection, view, query, and filters.
// If a page is specified it will go to that page.
function updateLibraryData(page) {
    'use strict';

    // eslint-disable-next-line compat/compat
    var uri = new URL(window.location); // not good for Opera Mini, IE
    uri.pathname = uri.pathname
        .replace('/library/', '/library/data/');
    var params = uri.searchParams;
    if (page) {
        params.set('page', page);
    } else {
        params.delete('page'); // Force first page of results when filters are changed.
    }
    uri = addFilterArgs(uri);

    return $.get(uri).done(function(data) {
        var $libraryData = $('#libraryData');
        $libraryData.html(data);
        if (hasBricksLayout()) {
            libraryMasonryEnable();
        }
        $libraryData.CFW_Init();
    });
}

// Handle filter checkbox dynamic behavior
function filterAllUpdate() {
    'use strict';

    // set up initial state based on page markup
    $('[data-clusive="filterAllUpdate"]').each(function() {
        var $par = $(this);
        var $all = $par.find('[data-clusive="filterAll"]');
        var $checked = $par.find('input:checked');
        if (!$par.length || !$all.length) { return; }
        if (!$checked.length) {
            $all.prop('checked', true);
        } else {
            $all.prop('checked', false);
        }
    });
    $('#clearFilters').toggle(hasActiveFilters());

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
        $('#clearFilters').toggle(hasActiveFilters());
        updateLibraryData();
        if (hasBricksLayout()) {
            libraryMasonryEnable();
        }
    });
}

// Set up pagination links to AJAX update the library page content.
function libraryPageLinkSetup() {
    'use strict';

    $(document.body).on('click', 'a.page-link', function(e) {
        e.preventDefault();
        var $elm = $(e.currentTarget);
        updateLibraryData($elm.attr('href'))
            .then(function() {
                $('#libraryData')[0].scrollIntoView();
            });
    });
}

// Set up style and sort links on the library page to dynamically add page number & filter settings to the URL linked.
function libraryStyleSortLinkSetup() {
    'use strict';

    // Style links add filters and page numbers
    $(document.body).on('click', 'a.style-link', function(e) {
        e.preventDefault();
        // eslint-disable-next-line compat/compat
        var url = new URL($(e.currentTarget).attr('href'), window.location);
        url = addFilterArgs(url);
        if (window.current_page_number) {
            url.searchParams.set('page', window.current_page_number);
        }
        window.location = url;
    });

    // Sort links add filters, but page number is reset to 1.
    $(document.body).on('click', 'a.sort-link', function(e) {
        e.preventDefault();
        // eslint-disable-next-line compat/compat
        var url = new URL($(e.currentTarget).attr('href'), window.location);
        url = addFilterArgs(url);
        window.location = url;
    });
}

function dashboardSetup() {
    'use strict';

    var $body = $('body');
    // Clicking one of the bars in the dashboard activity panel highlights other bars for the same book.
    $body.on('focus', '.readtime-bar', function() {
        var id = $(this).data('clusive-book-id');
        if (id) {
            $('.readtime-bar.active').removeClass('active');
            $('[data-clusive-book-id="' + id + '"]').addClass('active');
        }
    });
    $body.on('blur', '.readtime-bar', function() {
        $('.readtime-bar.active').removeClass('active');
    });

    // Timescale links in the dashboard activity panel
    $body.on('click', 'a.activity-panel-days', function(e) {
        e.preventDefault();
        var $studentActivityPanel = $('#StudentActivityPanel');
        $studentActivityPanel.find('table tr.loading').show();
        $studentActivityPanel.find('table tr.real-data').hide();
        $.get('/dashboard-activity-panel/' + $(this).data('days'))
            .done(function(result) {
                $studentActivityPanel.replaceWith(result);
                $studentActivityPanel.CFW_Init();
            })
            .fail(function(err) {
                console.error('Failed fetching replacement dashboard panel: ', err);
            });
    });

    // Sort links in the dashboard activity panel
    $body.on('click', 'a.activity-panel-sort', function(e) {
        e.preventDefault();
        var $studentActivityPanel = $('#StudentActivityPanel');
        $studentActivityPanel.find('table tr.loading').show();
        $studentActivityPanel.find('table tr.real-data').hide();
        $.get('/dashboard-activity-panel-sort/' + $(this).data('sort'))
            .done(function(result) {
                $studentActivityPanel.replaceWith(result);
                $studentActivityPanel.CFW_Init();
            })
            .fail(function(err) {
                console.error('Failed fetching replacement dashboard panel: ', err);
            });
    });
}

// Starred button functionality
function starredButtons() {
    'use strict';

    var txtDefault = 'Not Starred';
    var txtActive = 'Starred';

    $(document).on('click', '.btn-starred', function(e) {
        var $trigger = $(e.currentTarget);
        $trigger.toggleClass('active');
        var isActive = $trigger.hasClass('active');
        var textMsg = isActive ? txtActive : txtDefault;

        $(document).one('afterUnlink.cfw.tooltip', $trigger, function() {
                $trigger
                    .attr('aria-label', textMsg)
                    .removeAttr('data-cfw-tooltip-title')
                    .CFW_Tooltip({
                        title: textMsg
                    })
                    .CFW_Tooltip('show');
        });

        $trigger.CFW_Tooltip('dispose');

        // TODO: Callback to event logging?
    });
}

// Context (selection) menu methods

function contextLookup(selection) {
    'use strict';

    var match = selection.match('\\w+');
    var word = '';
    if (match) {
        word = match[0];
    } else {
        console.info('Did not find any word in selection: %s', selection);
    }
    console.debug('looking up: ', word);
    window.parent.load_definition(0, word);
    window.parent.$('#glossaryLocator').CFW_Popover('show');
    window.parent.glossaryPop_focus($('#lookupIcon'));
}

function contextTranslate(selection) {
    'use strict';

    console.info('translate: ' + selection);
    load_translation(selection);
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
    libraryPageLinkSetup();
    libraryStyleSortLinkSetup();
    dashboardSetup();
    starredButtons();

    var settingFontSize = document.querySelector('#set-size');
    if (settingFontSize !== null) {
        formRangeTip(settingFontSize, formRangeFontSize);
    }

    var settingReadSpeed = document.querySelector('#set-read-speed');
    if (settingReadSpeed !== null) {
        formRangeTip(settingReadSpeed, formRangeReadSpeed);
    }
});
