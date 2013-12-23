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
    MESSAGING.getInstance().addHandler(getUniqueId(),"changelayer", function(m) { on_changeLayer(element, m.getMessage()); });

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
       if( $('.layerData',element).text() != "{}" ) {
           MESSAGING.getInstance().send(
               getUniqueId(),
               new Message("setLayers", $('.layerData',element).text())
           );
       } else {
           console.log("no setLayers message sent, DOM info: "+$('.layerData',element).text());
       }
    });

    function getUniqueId() {
        return $('.frame', element).attr('id');
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
    function on_changeLayer(el, json) {
        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(el, 'change_layer_properties'),
            data: json,
            success: function(result) {
                if( !result ) {
                    alert("Failed to change layer for map: "+$('.frame', el).attr('id'));
                }
            }
        });
    }


    $(function ($) {
        /* Here's where you'd do things on page load. */
        $( '.slider', element ).slider({
            value: 0,
            min: 0,
            max: 24,
            step: 1,
            slide: function(event, ui) {
                console.log('slide: ui='+ui.value);
            }
        });
    });
}



