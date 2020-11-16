/* eslint-disable strict */
/* global vocabCheck */

// Glossary-related functionality

var glossaryCurrentWord = null;
var glossaryBeenDragged = false;

// Ensure focus for glossary popover on open,
// and re-focus on word when popover closed
function glossaryPop_focus($elm) {
    $('#glossaryLocator')
        .off('afterHide.cfw.popover.refocus')
        .one('afterHide.cfw.popover.refocus', function() {
            if ($elm.get(0) !== $('#glossaryLocator').get(0)) {
                $elm.trigger('focus');
            }
        });
    $('#glossaryPop').trigger('focus');
}

function load_definition(cued, word) {
    var title;
    var body;
    $('#glossaryFooter').hide();
    $('#glossaryInput').hide();
    if (word) {
        glossaryCurrentWord = word;
        title = word;
        var pub = window.pub_id || 0;
        $.get('/glossary/glossdef/' + pub + '/' + cued + '/' + word, {"eventId": PAGE_EVENT_ID})
            // eslint-disable-next-line no-unused-vars
            .done(function(data, status) {
                $('#glossaryBody').html(data);
                $('#glossaryFooter').show();
            })
            .fail(function(err) {
                console.error(err);
                $('#glossaryBody').html(err.responseText);
            })
            .always(function() {
                if ($('#glossaryPop').is(':visible') && !glossaryBeenDragged) {
                    $('#glossaryPop').CFW_Popover('locateUpdate');
                }
            });
        $.get('/glossary/rating/' + word)
            // eslint-disable-next-line no-unused-vars
            .done(function(data, status) {
                $('#glossaryInput input').prop('checked', false); // Uncheck all
                if (data.rating !== null) {
                    $('#ranking0-' + data.rating).prop('checked', true);
                }
                $('#glossaryInput').show();
            });
        body = 'Loading...';
    } else {
        title = 'Lookup';
        body = 'Select a word, then click \'lookup\' to see a definition';
    }
    $('#glossaryTitle').html(title);
    $('#glossaryBody').html(body);
}

// Methods related to the wordbank page

window.wordBank = {};

window.wordBank.removeWord = function(elt) {
    var item = $(elt).closest('div.wordbank-item');
    var word = item.find('.wordbank-word').text();
    item.remove();
    $.get('/glossary/interest/remove/' + word);
    window.wordBank.updateColumnCounts();
};

window.wordBank.moveRating = function(elt, delta) {
    var item = $(elt).closest('div.wordbank-item');
    var word = item.find('.wordbank-word');
    var rating = Number(item.data('rating'));
    var newrating = rating + delta;
    if (newrating >= 0 && newrating <= 3) {
        $.get('/glossary/rating/' + word.text() + '/' + newrating);
        window.wordBank.displayNewWordRating(item, newrating);
    }
};

window.wordBank.displayNewWordRating = function(item, newrating) {
    item.removeClass('offset' + item.data('rating'));
    item.data('rating', newrating);
    item.addClass('offset' + newrating);
    item.find('.wordbank-word').attr('aria-describedby', 'rank' + newrating);
    window.wordBank.updateColumnCounts();
};

window.wordBank.updateColumnCounts = function() {
    for (var rank = 0; rank <= 3; rank++) {
        var n = $('.wordbank-item.offset' + rank).length;
        var indicator = $('#count' + rank);
        indicator.text(n);
        if (n === 0) {
            indicator.closest('.wordbank-count').addClass('wordbank-count-empty');
        } else {
            indicator.closest('.wordbank-count').removeClass('wordbank-count-empty');
        }
    }
};

window.wordBank.wordClicked = function(elt) {
    var item = $(elt).closest('div.wordbank-item');
    var word = item.find('.wordbank-word').text();
    load_definition(1, word);
    $('#glossaryLocator').CFW_Popover('show');
    glossaryPop_focus($(elt));
};

// Methods related to the vocabulary check-in process

window.vocabCheck = {};

vocabCheck.start = function(link, article) {
    vocabCheck.pendingArticle = article;
    $.get('/glossary/checklist/' + article)
        // eslint-disable-next-line no-unused-vars
        .done(function(data, status) {
            vocabCheck.words = data.words;
            vocabCheck.wordCount = vocabCheck.words.length;
            if (vocabCheck.wordCount === 0) { vocabCheck.done(); } // No words to show
            (vocabCheck.ratings = []).length = vocabCheck.wordCount; vocabCheck.ratings.fill(null);
            vocabCheck.wordIndex = 0;
            vocabCheck.update();
            $(link).CFW_Modal({
                target: '#vocabCheckModal',
                unlink: true
            });
            $(link).CFW_Modal('show');
        })
        .fail(function(err) {
            console.error(err);
        });
};

vocabCheck.next = function() {
    vocabCheck.wordIndex++;
    vocabCheck.update();
    $('#vocabCheckBody').focus();
    return false;
};

vocabCheck.back = function() {
    if (vocabCheck.wordIndex > 0) {
        vocabCheck.wordIndex--;
        vocabCheck.update();
    }
    $('#vocabCheckBody').focus();
    return false;
};

vocabCheck.update = function() {
    $('#vocabCheckModal input[type="radio"]').prop('checked', false);
    var currentRating = vocabCheck.ratings[vocabCheck.wordIndex];
    if (currentRating !== null) { $('#vocabCheck' + currentRating).prop('checked', true); }
    if (vocabCheck.wordIndex > 0) { $('#vocabCheckBack').show(); } else { $('#vocabCheckBack').hide(); }
    $('#vocabCheckCount').html(vocabCheck.wordCount);
    $('#vocabCheckCountHead').html(vocabCheck.wordCount);
    $('#vocabCheckIndex').html(vocabCheck.wordIndex + 1);
    $('#vocabCheckWord').html(vocabCheck.words[vocabCheck.wordIndex]);
    if (vocabCheck.wordIndex < vocabCheck.wordCount - 1) {
        $('#vocabCheckNext').show().prop('disabled', currentRating === null);
        $('#vocabCheckThanks').hide();
        $('#vocabCheckDone').hide();
    } else {
        $('#vocabCheckNext').hide();
        $('#vocabCheckDone').show().prop('disabled', currentRating === null);
    }
};

vocabCheck.selected = function(value) {
    vocabCheck.ratings[vocabCheck.wordIndex] = value;
    if (vocabCheck.wordIndex < vocabCheck.wordCount - 1) {
        $('#vocabCheckNext').prop('disabled', false);
    } else {
        $('#vocabCheckThanks').show();
        $('#vocabCheckDone').prop('disabled', false);
    }
};

vocabCheck.skip = function() {
    window.location = '/reader/' + vocabCheck.pendingArticle;
    return false;
};

vocabCheck.done = function() {
    window.location = '/reader/' + vocabCheck.pendingArticle;
    return false;
};


// Set up listener functions after page is loaded

$(function() {
    $('#glossaryLocator').CFW_Popover({
        target: '#glossaryPop',
        trigger: 'manual',
        placement: 'reverse',
        drag: true,
        popperConfig: {
            positionFixed: true,
            eventsEnabled: false,
            modifiers: {
                preventOverflow: {
                    boundariesElement: 'viewport'
                },
                computeStyle: {
                    gpuAcceleration: false
                }
            }
        }
    })
        .on('afterHide.cfw.popover', function() {
            glossaryBeenDragged = false;
        })
        .on('dragStart.cfw.popover', function() {
            glossaryBeenDragged = true;
        });

    // When ranking in the glossary popup is selected, notify server
    $('#glossaryInput').on('change', 'input', function() {
        var newValue = $(this).val();
        $.get('/glossary/rating/' + glossaryCurrentWord + '/' + newValue);
        // If we're on the word bank page, need to update the word's position as well
        $('div.wordbank-item .wordbank-word').each(function() {
            var wbw = $(this);
            if (wbw.text() === glossaryCurrentWord) {
                window.wordBank.displayNewWordRating(wbw.closest('div.wordbank-item'), newValue);
            }
        });
    });

    // When ranking in the check-in modal is selected, notify server
    $('#vocabCheckModal').on('change', 'input[type="radio"]', function() {
        var value = $(this).val();
        $.get('/glossary/rating/' + vocabCheck.words[vocabCheck.wordIndex] + '/' + value);
        vocabCheck.selected(value);
    });

    $('a.wordbank-word').on('click', function(e) {
        e.preventDefault();
        window.wordBank.wordClicked(this);
    });

    $('a.wordbank-del').on('click', function(e) {
        e.preventDefault();
        window.wordBank.removeWord(this);
    });

    $('a.wordbank-next').on('click', function(e) {
        e.preventDefault();
        window.wordBank.moveRating(this, +1);
    });

    $('a.wordbank-prev').on('click', function(e) {
        e.preventDefault();
        window.wordBank.moveRating(this, -1);
    });

    window.wordBank.updateColumnCounts();
});
