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
    MESSAGING.getInstance().addHandler(getUniqueId(),"answer-tool-done", function(m) { on_answer_tool_done(element, m.getMessage()); });

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

        selectLayer(true,$('.frame',element).attr("baseLayer"));

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
                        result.answers[i].padding = result.padding;
                        html += "<li><span id='answer-"+result.answers[i].id+"'><span>"+result.answers[i].explanation+"</span><br/><span class='"+result.answers[i].type+"-tool'/><span id='score-"+result.answers[i].id+"'/><div id='dialog-"+result.answers[i].id+"'/></span></li>";
                    }
                    html += "</ol>";
                    $('.answerControls',element).html(html);
                    for(var i in result.answers) {
                        var tool = $('.answerControls',element).find('#answer-'+result.answers[i].id).find('.'+result.answers[i].type+'-tool');
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
             }
        });


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
            }
        });
//        tree.visit(function(node){
//             node.expand(false);
//        });

        MESSAGING.getInstance().addHandler(getUniqueId(),"point-response", function(m) {
            var data = JSON.parse(JSON.parse(m.message));
            $.ajax({
                type: "POST",
                url: runtime.handlerUrl(element, 'point_response'),
                data: JSON.stringify(data),
                success: function(result) {
                    if( !result ) {
                        console.log("Failed to test point-response for map: "+$('.frame', el).attr('id'));
                    } else {  //TODO: Fix url to point to local image
                        var div = $('#score-'+result.answer.id);
                        if( result.isHit ) {
                            div.html("<img src='/resource/equality_demo/public/images/correct-icon.png'/>");
                            MESSAGING.getInstance().sendAll( new Message("reset-answer-tool",null));
                            info2("Correct!", 1000);
                        } else {
                            div.html("<img src='/resource/equality_demo/public/images/incorrect-icon.png'/>");
                            var nAttempt = div.attr("nAttempts");
                            if( nAttempt == undefined ) nAttempt = 0;
                            nAttempt++;
                            div.attr("nAttempts",nAttempt);
                            var hintAfterAttempt = result.answer.hintAfterAttempt;
                            if( hintAfterAttempt != null ) {
                                if( nAttempt % hintAfterAttempt == 0) {
                                    var html = "<ul>";
                                    for( var i=0;i<result.answer.constraints.length; i++) {
                                        html += "<li>"+result.answer.constraints[i].explanation+"</li>";
                                    }
                                    html += "</ul>";
                                    info2(html);
                                }
                            }
                        }

                    }
                }
            });
        })

        MESSAGING.getInstance().addHandler(getUniqueId(),"polygon-response", function(m) {
            var data = JSON.parse(JSON.parse(m.message));

            $.ajax({
                type: "POST",
                url: runtime.handlerUrl(element, 'polygon_response'),
                data: JSON.stringify(data),
                success: function(result) {
                    if( !result ) {
                        console.log("Failed to test point-response for map: "+$('.frame', el).attr('id'));
                    } else {  //TODO: Fix url to point to local image
                        var div = $('#score-'+result.answer.id);
                        if( result.isHit ) {
                            div.html("<img src='/resource/equality_demo/public/images/correct-icon.png'/>");
                            MESSAGING.getInstance().sendAll( new Message("reset-answer-tool",null));
                            info2("Correct!", 1000);
                        } else {
                            div.html("<img src='/resource/equality_demo/public/images/incorrect-icon.png'/>");
                            var nAttempt = div.attr("nAttempts");
                            if( nAttempt == undefined ) nAttempt = 0;
                            nAttempt++;
                            div.attr("nAttempts",nAttempt);

                            if( result.error != null ) {
                                error2("<B>Error</B> "+result.error);
                            } else {
                                var hintAfterAttempt = result.answer.hintAfterAttempt;
                                if( hintAfterAttempt != null ) {
                                    if( nAttempt % hintAfterAttempt == 0) {
                                        var html = "<ul>";
                                        for( var i=0;i<result.answer.constraints.length; i++) {
                                            var constraint = result.answer.constraints[i];
                                            if( !constraint.satisfied ) {
                                                html += "<li>"+constraint.explanation+"</li>";
                                            }
                                        }
                                        html += "</ul>";
                                        info2(html,data.answer.hintDisplayTime);
                                    }
                                }
                            }
                        }

                    }
                }
            });
        })



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
            data: JSON.stringify({centerLat: data.center.y,  centerLon: data.center.x, zoomLevel:data.zoomLevel}),
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

        var legendData = layer.legendData;
        var legendUrl = null;
        if( legendData ) {
            legendUrl = legendData.url+"?TRANSPARENT=TRUE&EXCEPTIONS=application%2Fvnd.ogc.se_xml&VERSION=1.1.1&SERVICE=WMS&REQUEST=GetLegendGraphic&TILED=true&LAYER="
                                    + legendData.name+"&STYLE="+legendData.styles+"&transparent=true&format=image%2Fpng&legend_options=fontAntiAliasing%3Atrue";
        }

        $(".layerControls",el).dynatree("getRoot").visit( function(node) {
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

        if( $('.frame',el).attr('debug') ) {
            if( layer.visibility ) {
                $(".layerIdInfo",el).text(layer.id);
            }
        }

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
                }).draggable(); //use touch-punch hack for touch screen compatibility

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
  //      $(document).tooltip();
        /* Here's where you'd do things on page load. */
    });



}

//
//function info(msgHtml, duration) {
//      if( duration == undefined ) duration = 2500;
//      jNotify(
//		msgHtml + (duration < 0?'<br/><center><i>Click window to dismiss</i></center>':''),  //TODO: I18n
//		{
//		  autoHide : duration>0, // added in v2.0
//		  clickOverlay : false, // added in v2.0
//		  MinWidth : 250,
//		  TimeShown : duration,
//		  ShowTimeEffect : 200,
//		  HideTimeEffect : 200,
//		  LongTrip :20,
//		  HorizontalPosition : 'center',
//		  VerticalPosition : 'top',
//		  ShowOverlay : true,
//          closeLabel: "&times;",
//   		  ColorOverlay : '#000',
//		  OpacityOverlay : 0.3,
//		  onClosed : function(){ // added in v2.0
//
//		  },
//		  onCompleted : function(){ // added in v2.0
//
//		  }
//		});
//}

function info2(msgHtml, duration) {
    if( duration == undefined ) duration = 5000;
    if( document.getElementById("dialog") == undefined ) {
        $("body").append($('<div/>', {id: 'dialog'}));
    }
    try {
        $('#dialog').prop("title","Info").html(msgHtml).dialog({
            modal: false,
            title: "Info:",
            position: ['center', 'middle'],
            show: 'blind',
            hide: 'blind',
            dialogClass: 'ui-dialog-osx'
        });
        if( duration > 0 ) {
            window.setTimeout( function() {
                $('#dialog').dialog("close");
            }, duration);
        }
    } catch (e) {
        console.log("exception: "+e);
    }
}
//function error(msgHtml) {
//      jError(
//		msgHtml,
//		{
//		  autoHide : false, // added in v2.0
//		  clickOverlay : true, // added in v2.0
//		  MinWidth : 250,
//		  ShowTimeEffect : 200,
//		  HideTimeEffect : 200,
//		  LongTrip :20,
//		  HorizontalPosition : 'center',
//		  VerticalPosition : 'top',
//		  ShowOverlay : true,
//   		  ColorOverlay : '#000',
//		  OpacityOverlay : 0.3,
//          CloseLabel: "&times;",
//          onClosed : function(){ // added in v2.0
//
//		  },
//		  onCompleted : function(){ // added in v2.0
//
//		  }
//		});
//}

function error2(msgHtml) {
    if( document.getElementById("dialog") == undefined ) {
        $("body").append($('<div/>', {id: 'dialog'}));
    }
    try {
    $('#dialog').html(msgHtml).dialog({
        modal: true,
        title: "Error!",
        position: ['center', 'middle'],
        show: 'blind',
        hide: 'blind',
        dialogClass: 'ui-dialog-osx'
    });
    } catch (e) {
        console.log("exception: "+e);
    }
}