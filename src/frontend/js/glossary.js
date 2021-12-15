/* eslint-disable strict */
/* global vocabCheck, clusiveEvents, clusivePrefs, confettiCannon, DJANGO_CSRF_TOKEN, pub_id, interact */
/* exported load_translation */

// Glossary-related functionality

var glossaryCurrentWord = null;
var glossaryBeenDragged = false;
var translateBeenDragged = false;

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
        $.get('/glossary/glossdef/' + pub + '/' + cued + '/' + word)
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

function load_translation(text) {
    var lang = clusivePrefs.prefsEditorLoader.model.preferences.cisl_prefs_translationLanguage;
    $('#translateSource').text(text);
    var $translateOutput = $('#translateOutput');
    $translateOutput.text('Loading...');
    $('#translateLocator').CFW_Popover('show');
    $.ajax('/translation/translate', {
        method: 'POST',
        headers: {
            'X-CSRFToken': DJANGO_CSRF_TOKEN
        },
        data: {
            text: text,
            language: lang,
            book_id: pub_id
        }
    })
        .done(function(data) {
            $translateOutput.html(data.result);
            $translateOutput.attr('lang', data.lang);
            $translateOutput.css('direction', data.direction);
        })
        .fail(function(err) {
            console.error(err);
            $translateOutput.html(err.responseText);
        })
        .always(function() {
            var $translatePop = $('#translatePop');
            if ($translatePop.is(':visible') && !translateBeenDragged) {
                $translatePop.CFW_Popover('locateUpdate');
            }
        });
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
    var control = delta > 0 ? 'wb_shift_right' : 'wb_shift_left';
    var newrating = rating + delta;
    if (newrating >= 0 && newrating <= 3) {
        $.get('/glossary/rating/' + control + '/' + word.text() + '/' + newrating);
        window.wordBank.displayNewWordRating(item, newrating);
    }
};

window.wordBank.displayNewWordRating = function(item, newrating) {
    item.removeClass('offset' + item.data('rating'));
    item.data('rating', newrating);
    item[0].dataset.rating = newrating;
    item.addClass('offset' + newrating);
    item.find('.wordbank-word').attr('aria-describedby', 'rank' + newrating);
    window.wordBank.updateColumnCounts();
};

window.wordBank.updateColumnCounts = function() {
    var wordCount = 0;
    var msgElmEmpty = document.querySelector('#wordbankEmptyMsg');
    var msgElmPersonalize = document.querySelector('#wordbankPersonalizeMsg');
    for (var rank = 0; rank <= 3; rank++) {
        var n = $('.wordbank-item.offset' + rank).length;
        var indicator = $('#count' + rank);
        indicator.text(n);
        wordCount += n;
        if (n === 0) {
            indicator.closest('.wordbank-count').addClass('wordbank-count-empty');
        } else {
            indicator.closest('.wordbank-count').removeClass('wordbank-count-empty');
        }
    }
    if (wordCount === 0) {
        if (msgElmEmpty !== null) {
            msgElmEmpty.classList.remove('d-none');
        }
        if (msgElmPersonalize !== null) {
            msgElmPersonalize.classList.add('d-none');
        }
    } else {
        if (msgElmPersonalize !== null) {
            msgElmPersonalize.classList.remove('d-none');
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

// Methods related to dragging word bank words between ratings

window.wordBank.dragWord = {
    dragging: false,
    delta: 5,
    position: {
        x: 0,
        y: 0
    }
};

window.wordBank.enableDragDrop = function() {
    // Check to see if on word bank page
    if (document.querySelector('.wordbank') === null) {
        return;
    }

    interact.pointerMoveTolerance(5);
    interact('.wordbank-drag')
        .draggable({
            // manualStart: true,
            startAxis: 'x',
            lockAxis: 'x',
            // hold: 300,
            max: 1,
            modifiers: [
                interact.modifiers.restrict({
                    restriction: '.wordbank-scroll',
                    elementRect: {
                        top: 0,
                        right: 1,
                        bottom: 1,
                        left: 0
                    }
                })
            ],
            listeners: {
                start: function start(event) {
                    window.wordBank.dragWord.position = {
                        x: 0,
                        y: 0
                    };
                    // Add outline and block links
                    if (window.wordBank.dragWord.dragging) {
                        event.target.classList.add('dragging');
                    }
                },
                move: function move(event) {
                    if (window.wordBank.dragWord.dragging) {
                        window.wordBank.dragWord.position.x += event.dx;
                        window.wordBank.dragWord.position.y += event.dy;
                        event.target.style.transform = 'translate(' + window.wordBank.dragWord.position.x + 'px, ' + window.wordBank.dragWord.position.y + 'px)';
                        return;
                    }

                    // Check for minimum delta
                    if (Math.abs(event.x0 - event.dx) >= window.wordBank.dragWord.delta) {
                        window.wordBank.dragWord.dragging = true;
                        // Add outline and block links
                        event.target.classList.add('dragging');
                        // Disallow sliding animation
                        var item = event.target.closest('.wordbank-item');
                        item.classList.add('dragging');
                    }
                },
                end: function end(event) {
                    event.target.style.transform = '';

                    // Remove outline and and unblock links
                    event.target.classList.remove('dragging');
                    // Allow sliding animation
                    var item = event.target.closest('.wordbank-item');
                    setTimeout(function() {
                        item.classList.remove('dragging');
                    });
                    window.wordBank.dragWord.dragging = false;
                }
            }
        })
        .pointerEvents({
            holdDuration: 300
        })
        .on('hold', function(event) {
            // Use manual hold check and call due to clicks making false positive auto-start holds
            var interaction = event.interaction;
            if (!interaction.interacting()) {
                window.wordBank.dragWord.dragging = true;
                interaction.start(
                    {
                        name: 'drag',
                        axis: 'x'       // See: https://github.com/taye/interact.js/issues/786
                    },
                    event.interactable,
                    event.currentTarget
                );
            }
        });

    interact('.wordbank-col').dropzone({
        accept: '.wordbank-drag',
        overlap: 'pointer',
        ondragenter: function(event) {
            // Drag enters dropzone overlap area
            event.target.classList.add('active');
        },
        ondragleave: function(event) {
            // Drag leaves dropzone overlap area
            event.target.classList.remove('active');
        },
        ondrop: function(event) {
            // Item dropped
            var elmDrag = event.relatedTarget;
            var elmDrop = event.target;
            var item = elmDrag.closest('.wordbank-item');
            var word = item.querySelector('.wordbank-word');
            var prevrating = Number(item.dataset.rating);
            var newrating = Number(elmDrop.dataset.dropzoneRating);

            if (prevrating !== newrating && newrating >= 0 && newrating <= 3) {
                // TODO: eventlog
                //var control = 'wb_drag??_??'
                //$.get('/glossary/rating/' + control + '/' + word.text() + '/' + newrating);
                window.wordBank.displayNewWordRating($(item), newrating);
                setTimeout(function() {
                    $(item).CFW_transition(null, function() { confettiCannon(word); });
                });
            }
        },
        ondropdeactivate: function(event) {
            // Drop finished
            event.target.classList.remove('active');
        }
    });
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
            if (vocabCheck.wordCount === 0) {
                vocabCheck.done(); // No words to show
            } else {
                (vocabCheck.ratings = []).length = vocabCheck.wordCount;
                vocabCheck.ratings.fill(null);
                vocabCheck.wordIndex = 0;
                vocabCheck.update();
                $(link).CFW_Modal({
                    target: '#vocabCheckModal',
                    unlink: true
                });
                $(link).CFW_Modal('show');
            }
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

vocabCheck.selected = function(value, target) {
    vocabCheck.ratings[vocabCheck.wordIndex] = value;
    if (vocabCheck.wordIndex < vocabCheck.wordCount - 1) {
        $('#vocabCheckNext').prop('disabled', false);
    } else {
        $('#vocabCheckThanks').show();
        $('#vocabCheckDone').prop('disabled', false);
        confettiCannon(target);
    }
};

vocabCheck.skip = function() {
    clusiveEvents.addVocabCheckSkippedEventToQueue();
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

    $('#translateLocator').CFW_Popover({
        target: '#translatePop',
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
            translateBeenDragged = false;
        })
        .on('dragStart.cfw.popover', function() {
            translateBeenDragged = true;
        });

    // When ranking in the glossary popup is selected, notify server
    $('#glossaryInput').on('change', 'input', function() {
        var newValue = $(this).val();
        $.get('/glossary/rating/defpanel/' + glossaryCurrentWord + '/' + newValue);
        // If we're on the word bank page, need to update the word's position as well
        $('div.wordbank-item .wordbank-word').each(function() {
            var wbw = $(this);
            if (wbw.text() === glossaryCurrentWord) {
                window.wordBank.displayNewWordRating(wbw.closest('div.wordbank-item'), newValue);
            }
        });
    });

    // When ranking in the check-in modal is selected, notify server
    $('#vocabCheckModal').on('change', 'input[type="radio"]', function(event) {
        var value = $(this).val();
        var bookId = vocabCheck.pendingArticle;
        $.get('/glossary/rating/checkin/' + vocabCheck.words[vocabCheck.wordIndex] + '/' + value + '?bookId=' + bookId);
        vocabCheck.selected(value, event.target);
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
        var item = e.target.closest('.wordbank-item');
        var word = item.querySelector('.wordbank-word');
        window.wordBank.moveRating(this, +1);
        $(item).CFW_transition(null, function() { confettiCannon(word); });
    });

    $('a.wordbank-prev').on('click', function(e) {
        e.preventDefault();
        var item = e.target.closest('.wordbank-item');
        var word = item.querySelector('.wordbank-word');
        window.wordBank.moveRating(this, -1);
        $(item).CFW_transition(null, function() { confettiCannon(word); });
    });

    window.wordBank.updateColumnCounts();
    window.wordBank.enableDragDrop();
});
