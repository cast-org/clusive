// Glossary functionality

function find_selected_word() {
    // Look for selected text, first in the reader iframe, then in the top-level frame.
    var sel = null, word = null;
    var reader = $('#D2Reader-Container iframe');
    if(reader.length)
        sel = reader.get(0).contentDocument.getSelection();
    if (sel==null || !sel.rangeCount) {
        sel = window.getSelection();
    }
    if (sel!=null && sel.rangeCount) {
        var text = sel.toString();
        var match = text.match('\\w+');
        if (match) {
            word = match[0];
        } else {
            console.log("Did not find any word in selection: ", text);
        }
    } else {
        console.log("No text selection found");
    }
    return word;
}

function load_definition(cued, word) {
    var title, body;
    if (word) {
        title = word;
        $.get('/glossary/glossdef/'+window.pub_id+'/'+cued+'/'+word)
            .done(function(data, status) {
                $('#glossaryBody').html(data);
            })
            .fail(function(err) {
                console.log(err);
                $('#glossaryBody').html(err.responseText);
            })
            .always(function() {
                $('#glossaryPop').CFW_Popover('locateUpdate');
            });
        body = "Loading...";
    } else {
        title = "Glossary";
        body = "Select a word, then click 'lookup' to see a definition";
    }
    $('#glossaryTitle').html(title);
    $('#glossaryBody').html(body);
}

// When lookup button is clicked, try to show a definition in the popover.
$(function() {
    $('#glossaryButton').on('click', function () {
        load_definition(0, find_selected_word());
        $(this).CFW_Popover('show');
    });
});

