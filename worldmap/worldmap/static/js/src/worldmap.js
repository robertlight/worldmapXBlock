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
    MESSAGING.getInstance().addHandler(getUniqueId(),"click", function(m) { on_click(element, m.getMessage()); });

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
//        if( $('.layerData',element).text() != "{}" ) {
//           MESSAGING.getInstance().send(
//               getUniqueId(),
//               new Message("setLayers", $('.layerData',element).text())
//           );
//        } else {
//           console.log("no setLayers message sent, DOM info: "+$('.layerData',element).text());
//        }


        $.ajax({
             type: "POST",
             url: runtime.handlerUrl(element, 'getSliderSetup'),
             data: "null",
             success: function(result) {

                for( var i=0; i<result.length; i++) {
                    var sliderSpec = result[i];
                    var sliderSpecId = sliderSpec.id;
                    console.log("sliderSpec.id = "+sliderSpecId);

                    var top=25;
                    var left=-10;

                    if( sliderSpec.position=="top" ) {
                        top=-15;
                    }

                    var tooltip = $('<div class="slider-tooltip" />').css({
                        top: top,
                        left: left
                    }).hide();

                    var title = $('<div class="slider-title"/>').text(sliderSpec.title).show();

                    var ctrl = document.createElement("div");
                    var startLabel = document.createElement("div");
                    var endLabel = document.createElement("div");
                    var sliderCtrl = document.createElement("div");

                    var orientation = (sliderSpec.position == "right" || sliderSpec.position == "left") ? "vertical" : "horizontal";
                    if( orientation == "horizontal" ) {
                        $(ctrl).addClass("horizontal-slider");
                        $(startLabel).addClass("horizontal-label").addClass("horizontal-label-left").text(sliderSpec.min).appendTo(ctrl);
                        $(sliderCtrl).addClass("horizontal-label").appendTo(ctrl);
                        $(endLabel).addClass("horizontal-label").text(sliderSpec.max).appendTo(ctrl);
                        $(title).addClass("horizontal-label-title");
                    } else {
                        $(title).addClass("vertical-label-title");
                        $(ctrl).addClass("vertical-slider-container");
                        $(endLabel).addClass("vertical-label").text(sliderSpec.max).appendTo(ctrl);
                        $(sliderCtrl).addClass("vertical-slider").appendTo(ctrl);
                        $(startLabel).addClass("vertical-label").addClass("vertical-label-bottom").text(sliderSpec.min).appendTo(ctrl);
                    }

                    var handler = function(e) {
                        var tooltip = $(e.target).find(".slider-tooltip");
                        if(e.type == "mouseenter") {
                            tooltip.show()
                        } else {
                            tooltip.hide()
                        }
                    }


                    $(sliderCtrl).attr("id","slider-"+sliderSpec.id).slider({
                        value: sliderSpec.min,
                        min:   sliderSpec.min,
                        max:   sliderSpec.max,
                        step:  sliderSpec.incr,
                        orientation: orientation,
                        animate: "fast",
                        slide: function(e, ui) {
                            $(this).find(".ui-slider-handle .slider-tooltip").text(ui.value);

                            var layerSpecs = window.worldmapLayerSpecs[getUniqueId()];
                            for (var i=0; i<layerSpecs.length; i++) {
                                for( var j=0; j<layerSpecs[i].params.length; j++) {
                                    if( sliderSpec.param == layerSpecs[i].params[j].name ) {
                                        var paramValue = layerSpecs[i].params[j].value;
                                        var nFrac = 0;
                                        if( paramValue != null ) {
                                            var loc = paramValue.indexOf(".");
                                            if( loc != -1 ) nFrac = paramValue.length - loc - 1;
                                        }
                                        var visible =  (paramValue != null && paramValue == Math.floor(ui.value * Math.pow(10,nFrac))/Math.pow(10,nFrac))
                                            || (ui.value >= layerSpecs[i].params[j].min && ui.value <= layerSpecs[i].params[j].max);
                                        selectLayer(visible, layerSpecs[i].id);
                                    }
                                }
                            }
                        }
                    }).css(orientation == "vertical" ? {height:250} : {width:250})
                      .find(".ui-slider-handle")
                      .append(tooltip)
                      .hover(handler);

                    $(title).appendTo(ctrl);

                    $(ctrl).appendTo($('.sliders-'+sliderSpec.position,element));
                }
             }
        });

        $.ajax({
             type: "POST",
             url: runtime.handlerUrl(element, 'getLayerSpecs'),
             data: "null",
             success: function(result) {
                if( typeof window.worldmapLayerSpecs == "undefined" ) window.worldmapLayerSpecs = [];
                window.worldmapLayerSpecs[getUniqueId()] = result;
             }
        });

        $('.layerControls',element).dynatree({
            title: "LayerControls",
//            minExpandLevel: 1, // 1=rootnote not collapsible
            imagePath: 'static/js/vendor/dynatree/skin/',
//            autoFocus:true,
//            keyboard: true,
//            persist: true,
//            autoCollapse: false,
//            clickFolderMode: 3, //1:activate, 2:expand, 3: activate+expand
//            activeVisible: true, // make sure, active nodes are visible (expand)
            checkbox: true,
            selectMode: 3,
//            fx: null, // or  {height: "toggle", duration:200 }
//            noLink: true,
            debugLevel: 2, // 0:quiet, 1:normal, 2:debug
            onRender: function(node, nodeSpan) {
                $(nodeSpan).find('.dynatree-icon').remove();
            },
            initAjax: {
                   type: "POST",
                   url: runtime.handlerUrl(element, 'layerTree'),
                   data: JSON.stringify({
                       key: "root", // Optional arguments to append to the url
                       mode: "all",
                       id: $('.frame', element).attr('id')
                   })
            },
        	ajaxDefaults: null,
            onSelect: function(select, node) {
                node.visit( function(n) {
                    if( !n.data.isFolder ) {
                        selectLayer(select, n.data.key);
                    }
                }, true);
            }
        });

    });

    var layerVisibilityCache = [];
    function selectLayer(select,layerid) {
        var uniqId = getUniqueId();
        var cachedValue = layerVisibilityCache[uniqId+layerid];
        if( typeof cachedValue == "undefined" || cachedValue != select) {
            var layer = {opacity:1.0, visibility:select};
            var layerData = JSON.stringify(JSON.parse("{\""+layerid+"\":"+JSON.stringify(layer)+"}"));
           // var layerData = JSON.parse('{"'+layerid+'": {"opacity":1.0, "visibility":"'+select+'}}');
            MESSAGING.getInstance().send(
                uniqId,
                new Message('setLayers', layerData)
            )
            layerVisibilityCache[uniqId+layerid] = select;
        }
    }
    function getUniqueId() {
        return $('.frame', element).attr('id');
    }

    function on_click(el, location) {
        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(el, 'test_click'),
            data: location,
            success: function(result) {
                if( result.hit ) {
                    alert("Congratulations - you found it");
                }
            }
        });
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
        var layer = JSON.parse(json);
        $(".layerControls",el).dynatree("getRoot").visit( function(node) {
            if( node.data.key == layer.id ) {
                node.select(layer.visibility);
            }
        });
        var useOpacityControls = $('.frame', element).attr('opacityControls');
        if( useOpacityControls && useOpacityControls.toLowerCase() == 'true' ) {
            var id = "layerOpacityCtrl_"+layer.id.replace((/[\. ]/g),'_');
            if( $('#'+id,el).length == 0 && layer.visibility ) {
                var ctrl = document.createElement("div");  //$(".opacityControl-"+id, el);

                $(ctrl).attr("id",id).slider({
                    value: layer.opacity,
                    min: 0,
                    max: 1,
                    step: .01,
                    animate: "fast",
                    slide: function(event, ui) {
                        layer.opacity = ui.value;
                        var newJson = JSON.stringify(layer);
                        console.log('slide handler: ui='+ui.value+"  for element: "+getUniqueId());

//                        MESSAGING.getInstance().send(
//                            getUniqueId(),
//                            new Message("setLayers", JSON.stringify(JSON.parse("{\""+layer.id+"\":"+JSON.stringify(layer)+"}")))
//                        );
                        $.ajax({
                            type: "POST",
                            url: runtime.handlerUrl(el, 'change_layer_properties'),
                            data: newJson,
                            success: function(result) {
                                if( !result ) {
                                    console.log("Failed to change layer for map: "+$('.frame', el).attr('id'));
                                }
                            }
                        });
                    }
                });
                ctrl.appendTo($('#layerControl-'+layer.id.replace((/[\. ]/g),'_')));
            } else if( !layer.visibility && $('#'+id,el).length > 0 ) {
              //  console.log("Removing control for id: "+layer.id);
                $('#'+id,el).remove();
            }
        }
        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(el, 'change_layer_properties'),
            data: json,
            success: function(result) {
                if( !result ) {
                    console.log("Failed to change layer for map: "+$('.frame', el).attr('id'));
                }
            }
        });
    }


    $(function ($) {
        console.log("initialize on page load");
        /* Here's where you'd do things on page load. */
    });
}



