/* Javascript for WorldMapXBlock. */
"use strict";
/**
 * called once for each frag on the page
 */
function WorldMapXBlock(runtime, element) {

    console.log("Initializing WorldMapXBlock "+$('.frame', element).attr('id'))

    MESSAGING.getInstance().addHandler(getUniqueId(),"info", function(m) { alert("info: "+m.getMessage()); });
    MESSAGING.getInstance().addHandler(getUniqueId(),"zoomend", function(m) { on_setZoomLevel(element, m.getMessage()); });
    MESSAGING.getInstance().addHandler(getUniqueId(),"moveend", function(m) { on_setCenter(element, m.getMessage()); });

    MESSAGING.getInstance().addHandler(getUniqueId(),"portalReady", function(m) {
       if( $('.frame', element).attr('centerLat') != 'None' ) {
           MESSAGING.getInstance().send(
               getUniqueId(),
               new Message("setCenter", {
                   zoomLevel: $('.frame', element).attr('zoomLevel'),
                   centerLat: $('.frame', element).attr('centerLat'),
                   centerLon: $('.frame', element).attr('centerLon')
               })
           );
       }
    });
    function getUniqueId() {
        return $('.frame', element).attr('id');
    }
    function updateCount(result) {
        $('.count', element).text(result.count);
    }

    function on_setZoomLevel(el, level) {
        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(el, 'set_zoom_level'),
            data: JSON.stringify({zoomLevel: level}),
            success: function(result) {
//                var id = $('.frame', el).attr('id');
//                alert("zoomlevel of "+id+" successfully changed to: "+result.zoomLevel);
            }
        });
    }
    function on_setCenter(el, json) {
        var data = JSON.parse(json);
        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(el, 'set_center'),
            data: JSON.stringify({centerLat: data.center.lat,  centerLon: data.center.lon, zoomLevel:data.zoomLevel}),
            success: function(result) {
                if( !result ) {
                    alert("Failed to setCenter for map: "+$('.frame', el).attr('id'));
                }
//                var id = $('.frame', el).attr('id');
//                alert("viewLimits of "+id+" successfully changed to: "+result.viewLimits);
            }
        });
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


