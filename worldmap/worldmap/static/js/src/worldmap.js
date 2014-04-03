/* Javascript for WorldMapXBlock. */
"use strict";
/**
 * called once for each frag on the page
 */

var WorldMapRegistry = Array();

function gettext(s) { return s;}  //TODO: replace with django's javascript i18n utilities

function WorldMapXBlock(runtime, element) {

    WorldMapRegistry[ getUniqueId()] = { runtime: runtime, element: element };

    console.log("Initializing WorldMapXBlock "+$('.frame', element).attr('id'))

    MESSAGING.getInstance().addHandler(getUniqueId(),"info", function(m) { alert("info: "+m.getMessage()); });
    MESSAGING.getInstance().addHandler(getUniqueId(),"zoomend", function(m) { on_setZoomLevel(m.getMessage()); });
    MESSAGING.getInstance().addHandler(getUniqueId(),"moveend", function(m) { on_setCenter(m.getMessage()); });
    MESSAGING.getInstance().addHandler(getUniqueId(),"changelayer", function(m) { on_changeLayer(m.getMessage()); });

    MESSAGING.getInstance().addHandler(getUniqueId(),"portalReady", function(m) {

        $.ajax({
             type: "POST",
             url: runtime.handlerUrl(element, 'getViewInfo'),
             data: "null",
             success: function(result) {
                if( result ) {
                   MESSAGING.getInstance().send(
                       getUniqueId(),
                       new Message("setCenter", {
                           zoomLevel: result.zoomLevel,
                           centerLat: result.centerLat,
                           centerLon: result.centerLon
                       })
                   );
                }
             }
        });

        if( $('.frame',element).attr("baseLayer") != undefined ) {
            selectLayer(true,$('.frame',element).attr("baseLayer"));
        }



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

                    var tooltip = $('<div class="slider-thumb-value" />').css({
                        top: top,
                        left: left
                    }).hide();



                    var title = $('<div class="slider-title"/>').text(sliderSpec.title).show();

                    var ctrl = document.createElement("div");
                    var startLabel = document.createElement("div");
                    var endLabel = document.createElement("div");
                    var sliderCtrl = document.createElement("div");

                    var orientation = (sliderSpec.position == "right" || sliderSpec.position == "left") ? "vertical" : "horizontal";
//                    var helpTop = orientation=="vertical"?0:0;
//                    var helpLeft= orientation=="vertical"?0:0;

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

//                    var help = $('<div class="slider-help" />').text(sliderSpec.help).css({
//                        top: helpTop,
//                        left: helpLeft
//                    }).hide();

                    var handler = function(e) {
                        var tooltip = $(e.target).find(".slider-thumb-value");
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
                        step:  sliderSpec.increment,
                        orientation: orientation,
                        animate: "fast",
                        slide: function(e, ui) {
                            $(this).find(".ui-slider-handle .slider-thumb-value").text(ui.value);

                            var layerSpecs = window.worldmapLayerSpecs[getUniqueId()];
                            for (var i=0; i<layerSpecs.length; i++) {
                                for( var j=0; j<layerSpecs[i].params.length; j++) {
                                    if( layerSpecs[i].params[j].name == null ) {
                                        console.log("ERROR:  unnamed param in layer specification");
                                    } else {
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
                        }
                    }).css(orientation == "vertical" ? {height:250} : {width:250})
                      .find(".ui-slider-handle")
                      .append(tooltip)
                      .hover(handler);

//                    $('.ui-slider',ctrl).tooltip({content: sliderSpec.help});
                    if( sliderSpec.help != null) {
                        $(title).tooltip({ items:"div",content: sliderSpec.help, position: {my: 'left center', at: 'right+10 center'}});
                    }
//                    $('.ui-slider', ctrl).hover( function(e) {
//                        var obj = $(e.target).find(".slider-help");
//                        if(e.type == "mouseenter") {
//                            obj.show()
//                        } else {
//                            obj.hide()
//                        }
//                    });

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

        if( $('.frame', element).attr('type') == "quiz" ) {
            //********************** POINT & POLYGON TOOLS**************************
            $.ajax({
                 type: "POST",
                 url: runtime.handlerUrl(element, 'getAnswers'),
                 data: "null",
                 success: function(result) {
                    //window.alert(JSON.stringify(result));
                    if( result != null ) {
                        var html = "<ol>"+result.explanation;
                        for(var i in result.answers) {
                            //result.answers[i].padding = result.padding;  //TODO: should be done on xml read, not here!
                            html += "<li><span id='answer-"+result.answers[i].id+"'><span>"+result.answers[i].explanation+"</span><br/><span class='"+result.answers[i].type+"-tool'/><span id='score-"+result.answers[i].id+"'/><div id='dialog-"+result.answers[i].id+"'/></span></li>";
                        }
                        html += "</ol>";
                        $('.auxArea',element).html(addUniqIdToArguments(getUniqueId(), html));
                        for(var i in result.answers) {
                            var tool = $('.auxArea',element).find('#answer-'+result.answers[i].id).find('.'+result.answers[i].type+'-tool');
                            tool.css('background-color',result.answers[i].color);
                            tool.click( result.answers[i], function(e) {
                                MESSAGING.getInstance().sendAll( new Message("reset-answer-tool",null));
                                MESSAGING.getInstance().send(
                                    getUniqueId(),
                                    new Message("set-answer-tool", e.data)
                                );
                            });
                        }
                    }
                 },
                 failure: function(){
                     window.alert("getAnswers returned failure");
                 }
            });
        } else if( $('.frame', element).attr('type') == "expository" ) {

            var uniqId = getUniqueId();

            $.ajax({
                type: "POST",
                url: runtime.handlerUrl(element, 'getExplanation'),
                data: "null",
                success: function(result) {
                    $('.auxArea',element).html(addUniqIdToArguments(getUniqueId(), result));
                }
            });
        }
        //****************** LAYER CONTROLS ***************************
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
            },
            onPostInit: function() {
                //now that the control is created, we need to update layer visibility based on state stored serverside
                $.ajax({
                   type: "POST",
                   url:  runtime.handlerUrl(element,"getLayerStates"),
                   data: "null",
                   success: function(result) {
                       for (var id in result) {
                           selectLayer(result[id]['visibility'], id);
                       }
                   }
                });
            }
        });

        MESSAGING.getInstance().addHandler(getUniqueId(),"point_response", responseHandler );
        MESSAGING.getInstance().addHandler(getUniqueId(),"polygon_response", responseHandler);
        MESSAGING.getInstance().addHandler(getUniqueId(),"polyline_response", responseHandler);
    });


    function responseHandler(m) {
        var data = JSON.parse(JSON.parse(m.message));

        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(element, m.type),
            data: JSON.stringify(data),
            success: function(result) {
                if( !result ) {
                    console.log("Failed to test "+ m.type+" for map: "+$('.frame', el).attr('id'));
                } else {  //TODO: Fix url to point to local image
                    var worldmap_block = $('#'+getUniqueId()).closest('div[class="worldmap_block"]');
                    var div = $(worldmap_block).find('#score-'+result.answer.id);
                    if( result.isHit ) {
                        div.html("<img src='/resource/equality_demo/public/images/correct-icon.png'/>");
                        MESSAGING.getInstance().sendAll( new Message("reset-answer-tool",null));
                        info("Correct!", 1000);
                    } else {
                        div.html("<img src='/resource/equality_demo/public/images/incorrect-icon.png'/>&nbsp;"+result.correctExplanation);
                        if( result.error != null ) {
                            error(result.error);
                        } else {
                            var nAttempt = div.attr("nAttempts");
                            if( nAttempt == undefined ) nAttempt = 0;
                            nAttempt++;
                            div.attr("nAttempts",nAttempt);
                            var hintAfterAttempt = result.answer.hintAfterAttempt;
                            if( hintAfterAttempt != null ) {
                                if( nAttempt % hintAfterAttempt == 0) {
                                    var uniqId = getUniqueId();
                                    var html = "<ul>";
                                    HintManager.getInstance().reset();
                                    for( var i=0;i<result.answer.constraints.length; i++) {
                                        var constraint = result.answer.constraints[i];
                                        if( !constraint.satisfied ) {
                                            HintManager.getInstance().addConstraint(i,constraint);
                                            html += "<li>"+constraint.explanation+"<a href='#' onclick='return HintManager.getInstance().flashHint(\""+uniqId+"\","+i+")'>hint</a></li>";
                                        }
                                    }
                                    html += "</ul>";
                                    info(html,result.answer.hintDisplayTime);
                                }
                            }
                        }
                    }
                }
            }
        });
    }

    var layerVisibilityCache = [];
    function selectLayer(select,layerid,moveTo) {
        var uniqId = getUniqueId();
        var cachedValue = layerVisibilityCache[uniqId+layerid];
        if( moveTo == undefined ) moveTo = false;
        if( typeof cachedValue == "undefined" || cachedValue != select || moveTo ) {
            var layer = {opacity:1.0, visibility:select, moveTo: moveTo};
            var layerData = JSON.stringify(JSON.parse("{\""+layerid+"\":"+JSON.stringify(layer)+"}"));

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

    function on_setZoomLevel(level) {
        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(element, 'set_zoom_level'),
            data: JSON.stringify({zoomLevel: level}),
            success: function(result) {
//                var id = $('.frame', el).attr('id');
//                alert("zoomlevel of "+id+" successfully changed to: "+result.zoomLevel);
            }
        });
    }
    function on_setCenter(json) {
        var data = JSON.parse(json);
        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(element, 'set_center'),
            data: JSON.stringify({centerLat: data.center.y,  centerLon: data.center.x, zoomLevel:data.zoomLevel}),
            success: function(result) {
                if( !result ) {
                    alert("Failed to setCenter for map: "+$('.frame', el).attr('id'));
                }
            }
        });
    }

    function on_changeLayer(json) {
        var layer = JSON.parse(json);

        var legendData = layer.legendData;
        var legendUrl = null;
        if( legendData ) {
            legendUrl = legendData.url+"?TRANSPARENT=TRUE&EXCEPTIONS=application%2Fvnd.ogc.se_xml&VERSION=1.1.1&SERVICE=WMS&REQUEST=GetLegendGraphic&TILED=true&LAYER="
                                    + legendData.name+"&STYLE="+legendData.styles+"&transparent=true&format=image%2Fpng&legend_options=fontAntiAliasing%3Atrue";
        }

        $(".layerControls",element).dynatree("getRoot").visit( function(node) {
            if( !node.isExpanded() ) { //if it isn't expanded, we need to expand/contract it so that all the children get loaded
                node.expand(true);
                node.expand(false);
            }
            if( node.data.key == layer.id ) {
                node.select(layer.visibility);
                if( legendUrl ) {
                    $(node.span).tooltip( {items: "a", content: '<img src="'+legendUrl+'" />'});
                }
            }
        });

        if( $('.frame',element).attr('debug') ) {
            if( layer.visibility ) {
                $(".layerIdInfo",element).text(layer.id);
            }
        }

        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(element, 'change_layer_properties'),
            data: json,
            success: function(result) {
                if( !result ) {
                    console.log("Failed to change layer for map: "+$('.frame', element).attr('id'));
                }
            }
        });
    }

    $(function ($) {
        console.log("initialize on page load");
  //      $(document).tooltip();
        /* Here's where you'd do things on page load. */
    });

    function info(msgHtml, duration) {
        if( duration == undefined ) duration = 5000;
        if( document.getElementById("dialog") == undefined ) {
            $("body").append($('<div/>', {id: 'dialog'}));
        }
        try {
            $('#dialog').prop("title",gettext("Info")).html(msgHtml).dialog({
                modal: true,
                width: 500,
                closeOnEscape: true,
                title: "Info:",
                position: ['center', 'middle'],
                show: 'blind',
                hide: 'blind',
                dialogClass: 'ui-dialog-osx',
                beforeClose: function() {
                    $(".ui-widget-overlay").css("opacity","0.3");
                },
                open: function() {
                    $(".ui-widget-overlay").css("opacity","0.15");
                }
            });
            if( duration > 0 ) {
                window.setTimeout( function() {
                    $('#dialog').dialog("close");
                }, duration);
            }
        } catch (e) {
            console.log("exception: "+e+"\n"+ e.stack);
        }
    }

    function error(msgHtml) {
        if( document.getElementById("dialog") == undefined ) {
            $("body").append($('<div/>', {id: 'dialog'}));
        }
        try {
        $('#dialog').html(msgHtml).dialog({
            modal: true,
            width: 400,
            title: gettext("Error!"),
            position: ['center', 'middle'],
            show: 'blind',
            hide: 'blind',
            dialogClass: 'ui-dialog-osx',
            open: function() {
                $(".ui-widget-overlay").css("opacity","0.3");
            }
        });
        } catch (e) {
            console.log("exception: "+e);
        }
    }

}

function addUniqIdToArguments( uniqId, str) {
    return str.replace(/highlight\(/g,"highlight('"+uniqId+"',").replace(/highlightLayer\(/g,"highlightLayer('"+uniqId+"',")
}

function highlight(uniqId, id, relativeZoom) {
    var relZoom = relativeZoom == undefined ? 0 : relativeZoom;
    var worldmapData = WorldMapRegistry[uniqId];
    $.ajax({
        type: "POST",
        url: worldmapData.runtime.handlerUrl(worldmapData.element, 'getGeometry'),
        data: JSON.stringify(id),
        success: function(result) {
            result['relativeZoom'] = relZoom;
            MESSAGING.getInstance().send(uniqId, new Message("highlight-geometry", result));
        }
    });
    return false;
}

function highlightLayer(uniqId, layerid, relativeZoom) {
    var relZoom = relativeZoom == undefined ? 0 : relativeZoom;
    MESSAGING.getInstance().send(
        uniqId,
        new Message('highlight-layer', JSON.stringify({layer: layerid, relativeZoom:relZoom}))
    )
    return false;
}



var HintManager = (function HintManagerSingleton() { // declare 'Singleton' as the return value of a self-executing anonymous function
    var _instance = null;
    var _constructor = function() {
        this.constraints = [];
    };
    _constructor.prototype = { // *** prototypes will be "public" methods available to the instance
        reset: function() {
            this.constraints = [];
        },
        addConstraint: function(indx, constraint) {
           this.constraints[indx] = constraint;
//            console.log("addConstraint["+this.constraints.length+"] = "+JSON.stringify(constraint));
        },
        flashHint: function(uniqId, indx) {
            var _this = this;
            var type = _this.constraints[indx]['geometry']['type'];
            var geo = _this.constraints[indx]['geometry'];
            if( type == 'polygon' ) {
                geo = _this.constraints[indx]['geometry']['points'];
            }
            var worldmapData = WorldMapRegistry[uniqId];
            $.ajax({
                type: "POST",
                url: worldmapData.runtime.handlerUrl(worldmapData.element,"getFuzzyGeometry"),
                data: JSON.stringify({
                    buffer: _this.constraints[indx]['padding'],
                    type: type,
                    geometry: geo
                }),
                success: function(result) {
                    MESSAGING.getInstance().send(uniqId, new Message("flash-polygon", result));
                }
            })
            return false;
        }
    };
    return {
        // because getInstance is defined within the same scope, it can access the "private" '_instance' and '_constructor' vars
        getInstance: function() {
           if( !_instance ) {
              _instance = new _constructor();
           }
           return _instance;
        }
    }
})();


