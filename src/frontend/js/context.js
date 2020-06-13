var clusiveContext = {
    docNode: null,
    menuId: '#contextMenu',
    menu: null,
    helper: null,
    preventSelRecursion: false
};

clusiveContext.debounce = function(fn, delay) {
    var timer = null;
    return function() {
        var context = this, args = arguments;
        clearTimeout(timer);
        timer = setTimeout(function() {
            fn.apply(context, args);
        }, delay);
    };
}

clusiveContext.hasReader = function() {
    return $('#D2Reader-Container').length > 0;
};

clusiveContext.getReaderIframeSelection = function() {
    return $('#D2Reader-Container').find('iframe')[0].contentWindow.getSelection();
};

clusiveContext.getReaderIFrameBody = function() {
    var readerIframe = $('#D2Reader-Container').find('iframe');
    return readerIframe.contents().find('body');
};

clusiveContext.getBody = function() {
    var $body;
    if (clusiveContext.hasReader()) {
        $body = clusiveContext.getReaderIFrameBody();
    } else {
        $body = $(document.body);
    }
    return $body;
};

clusiveContext.getSelection = function() {
    var selObj;

    if (clusiveContext.hasReader()) {
        selObj = clusiveContext.getReaderIframeSelection();
    } else {
        selObj = window.getSelection();
    }

    if (!selObj.rangeCount) {
        return null;
    }
    return selObj;
};

clusiveContext.getSelectionProperties = function(selObj) {
    var props = {};
    props.range = selObj.getRangeAt(0);
    props.string = props.range.toString();
    props.len = props.string.length;
    props.rect = props.range.getBoundingClientRect();
    return props;
};

clusiveContext.helperPlacement = function() {
    var selObj = clusiveContext.getSelection();
    var elRect = clusiveContext.getSelectionProperties(selObj).rect;
    var posRect = $.extend({}, elRect);
    var frameRect = {
        top: 0,
        left: 0
    };

    if (!clusiveContext.preventSelRecursion) {
        clusiveContext.iosNoContext();
    }

    if (clusiveContext.hasReader()) {
        if (selObj.anchorNode.ownerDocument === clusiveContext.getReaderIFrameBody()[0].ownerDocument) {
            frameRect = $('#D2Reader-Container').find('iframe')[0].getBoundingClientRect();
            posRect.top += frameRect.top;
            posRect.left += frameRect.left;
        }
    }

    var docScroll = {
        top: document.documentElement.scrollTop,
        left: document.documentElement.scrollLeft
    };
    posRect.top += docScroll.top;
    posRect.left += docScroll.left;

    clusiveContext.helper.css({
        top: posRect.top,
        left: posRect.left,
        width: posRect.width,
        height: posRect.height
    });

    if (clusiveContext.menu !== null) {
        clusiveContext.menu.CFW_Tooltip('locateUpdate');
    }
};

clusiveContext.helperSet = function() {
    if (clusiveContext.helper === null) {
        clusiveContext.helper = $(document.createElement('div'));
        clusiveContext.helper.addClass('context-helper');
        document.body.append(clusiveContext.helper[0]);

        $(window).on('resize.clusiveContext', function() {
            clusiveContext.helperPlacement();
        });

        clusiveContext.docNode.on('selectionchange.clusiveContext', function() {
            clusiveContext.helperPlacement();
        });
    }

    clusiveContext.helperPlacement();
};

clusiveContext.helperReset = function() {
    $(window).off('resize.clusiveContext');
    clusiveContext.docNode.off('selectionchange.clusiveContext');

    if (clusiveContext.helper !== null) {
        // TODO: Do someting else here ?

        clusiveContext.helper.remove();
    }
    clusiveContext.helper = null;
};

clusiveContext.menuSet = function() {
    clusiveContext.menu = $(clusiveContext.menuId);

    clusiveContext.helper
        .CFW_Tooltip({
            target: clusiveContext.menuId,
            trigger: 'manual',
            placement: 'bottom auto'
        })
        .CFW_Tooltip('show');
};

clusiveContext.menuReset = function() {
    if (clusiveContext.menu !== null) {
        clusiveContext.helper
            .CFW_Tooltip('unlink');
        clusiveContext.menu = null;
    }
};

clusiveContext.showMenu = function() {
    var selObj = clusiveContext.getSelection();

    if (selObj === null || selObj.isCollapsed) {
        clusiveContext.hideMenu();
        return;
    }

    console.log('selection\n', selObj, "\n" + selObj.anchorNode.ownerDocument);

    // clusiveContext.helperReset();
    clusiveContext.helperSet();
    clusiveContext.menuSet();
};

clusiveContext.hideMenu = function() {
    clusiveContext.menuReset();
    clusiveContext.helperReset();

};

// Hide the iOS Safari context menu
// Reference: https://stackoverflow.com/a/30046936
clusiveContext.iosNoContext = clusiveContext.debounce(function() {
    if (/(iPad|iPhone|iPod)/g.test(navigator.userAgent) ||
        (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1) ) {

        // Selection remove and re-add should remove context menu
        var S = clusiveContext.getSelection();
        var r = S.getRangeAt(0);
        clusiveContext.preventSelRecursion = true;

        S.removeAllRanges();
        setTimeout(function() {
            S.addRange(r);
            setTimeout(function(){
                clusiveContext.preventSelRecursion = false;
            });
        }, 5);
    }
}, 750);

// Use load event to watch allow iframe to become ready
$(window).on('load', function() {
    clusiveContext.docNode = $(document);
    if (clusiveContext.hasReader()) {
        clusiveContext.docNode = clusiveContext.docNode.add($(clusiveContext.getReaderIFrameBody()[0].ownerDocument));
    }

    clusiveContext.docNode.on('keyup mouseup touchend selectstart', function() {
        // Slight delay to 'allow selection update to finish'
        setTimeout(function() {
            clusiveContext.showMenu();
        }, 150);
    });

    //$(document).on('mousedown touchstart focus blur', 'p', function() {
    clusiveContext.docNode.on('mousedown touchstart focus blur', function() {
        clusiveContext.hideMenu();
    });

    // Hide context menu for Android Chrome
    clusiveContext.docNode.on('contextmenu', function(e) {
        e.preventDefault();
    });
});
