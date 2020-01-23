/* eslint-disable strict */
/* global vocabCheck */

// Glossary-related functionality

var glossaryCurrentWord = null;

function find_selected_word() {
    // Look for selected text, first in the reader iframe, then in the top-level frame.
    var sel = null;
    var word = null;
    var reader = $('#D2Reader-Container iframe');
    if (reader.length) {
        sel = reader.get(0).contentDocument.getSelection();
    }
    if (sel === null || !sel.rangeCount) {
        sel = window.getSelection();
    }
    if (sel !== null && sel.rangeCount) {
        var text = sel.toString();
        var match = text.match('\\w+');
        if (match) {
            word = match[0];
        } else {
            console.log('Did not find any word in selection: ', text);
        }
    } else {
        console.log('No text selection found');
    }
    return word;
}

function load_definition(cued, word) {
    var title;
    var body;
    $('#glossaryFooter').hide();
    $('#glossaryInput').hide();
    if (word) {
        glossaryCurrentWord = word;
        title = word;
        $.get('/glossary/glossdef/' + window.pub_id + '/' + cued + '/' + word)
            // eslint-disable-next-line no-unused-vars
            .done(function(data, status) {
                $('#glossaryBody').html(data);
                $('#glossaryFooter').show();
            })
            .fail(function(err) {
                console.log(err);
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
                console.log(data);
                $('#glossaryInput input').prop('checked', false); // Uncheck all
                if (data.rating !== null) {
                    console.log('#ranking0-' + data.rating);
                    $('#ranking0-' + data.rating).prop('checked', true);
                }
                $('#glossaryInput').show();
            });
        body = 'Loading...';
    } else {
        title = 'Glossary';
        body = 'Select a word, then click \'lookup\' to see a definition';
    }
    $('#glossaryTitle').html(title);
    $('#glossaryBody').html(body);
}

// Methods related to the wordbank page

window.wordBank = {};

window.wordBank.removeWord = function(elt, word) {
    $(elt).closest('div.wordbank-item').hide();
    $.get('/glossary/interest/remove/' + word);
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
            console.log(err);
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
    // When lookup button clicked, show definition of selected word
    $('#glossaryButton').on('click', function() {
        load_definition(0, find_selected_word());
        $(this).CFW_Popover('show');
    });

    // When ranking in the glossary popup is selected, notify server
    $('#glossaryInput').on('change', 'input', function() {
        console.log('input change detected', $(this).val());
        $.get('/glossary/rating/' + glossaryCurrentWord + '/' + $(this).val());
    });

    // When ranking in the check-in modal is selected, notify server
    $('#vocabCheckModal').on('change', 'input[type="radio"]', function() {
        var value = $(this).val();
        $.get('/glossary/rating/' + vocabCheck.words[vocabCheck.wordIndex] + '/' + value);
        vocabCheck.selected(value);
    });

    $('a.wordbank-del').on('click', function() {
        var word = $(this).closest('div.wordbank-item').find('.wordbank-word').text();
        window.wordBank.removeWord(this, word);
    });
});
