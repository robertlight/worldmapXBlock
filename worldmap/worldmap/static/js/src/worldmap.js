/* Javascript for WorldMapXBlock. */
"use strict";
/**
 * called once for each frag on the page
 */
function WorldMapXBlock(runtime, element) {

    console.log("Initializing WorldMapXBlock "+$('.frame', element).attr('id'))

    MESSAGING.getInstance().addHandler(getUniqueId(),"info", function(m) { alert("info: "+m.getMessage()); });

    function getUniqueId() {
        return $('.frame', element).attr('id');
    }
    function updateCount(result) {
        $('.count', element).text(result.count);
    }

    var handlerUrl = runtime.handlerUrl(element, 'increment_count');

    $('p', element).click(function(eventObject) {
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify({"hello": "world"}),
            success: updateCount
        });
    });

    $(function ($) {
        /* Here's where you'd do things on page load. */
    });
}

function initializeWorldMap(id) {
   alert("initializing worldmap: id="+id);
}


