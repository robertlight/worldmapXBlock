/* Javascript for WorldMapXBlock. */
"use strict";

function WorldMapXBlock(runtime, element) {

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
/***** xBlock-master.js ********/

var MESSAGING = (function Messaging() { // declare 'Singleton' as the return value of a self-executing anonymous function
    var _instance = null;
    var _constructor = function() {
        this.host = location.protocol+"//"+location.host+":"+(location.port ? location.port : "80")+"/";
        this.clientCredentials = [];
        this.handlers = [];
    };
    _constructor.prototype = { // *** prototypes will be "public" methods available to the instance
        setClientCredentials: function( id, creds ) {
    //       if( !this.clientCredentials[id] ) {
             this.clientCredentials[id] = creds;
             console.log("setClientCredentials: xblockId: "+id+" host: "+creds.clientHost+"   uniqueId: "+creds.uniqueClientId);
    //       } else {
    //         console.log("ERROR: no credentials found for id="+id);
    //       }
        },
        addHandler: function(id, type, h) {
           if( !this.handlers[id] ) {
              this.handlers[id] = [];
           }
           this.handlers[id][type] = h;
        },
        handleMessage: function(id,uniqId, msg) {
           var cred;
           try {
              cred = this.clientCredentials[id];
              cred.uniqueClientId; //make sure it exists
          } catch (e) {
              throw "SecurityException: cannot handle event for clientId: "+id+" - no such id.  Message: "+msg.getMessage();
          }
          if( cred.uniqueClientId != uniqId ) {  //SECURITY: make sure we've received credentials from this client
             throw "SecurityException: bad uniqueId("+uniqId+") for clientId: "+id+". Should be: "+this.clientCredentials[id].uniqueClientId;
          } else {
             try {
                this.handlers[id][msg.getType()](msg);
             } catch (e) { // SECURITY: make sure we have a handler for this message type
                throw "SecurityException: no handler for id: "+id+" for message type: "+msg.getType();
             }
          }
        },
        send: function(id,msg) {
           var creds = this.clientCredentials[id];
           if( creds ) {
              creds.source.postMessage(JSON.stringify( {type: msg.getType(), message: msg.getMessageStr()}), creds.clientHost);
           } else {
              throw "SecurityException: unknown xblockId: "+id+"  can't send message type="+msg.getType()+"   message="+msg.getMessageStr();
           }
        },
        getHost: function() {
           return this.host;
        }
    };
    return {
        // because getInstance is defined within the same scope, it can access the "private" '_instance' and '_constructor' vars
        getInstance: function() {
           if( !_instance ) {
              console.log("creating Messaging singleton");
              _instance = new _constructor();
           }
           return _instance;
        }
    }      
})();

function Message(t,m) {
   this.type = t;
   this.message = JSON.stringify(m);
}
Message.prototype = {
    constructor: Message,
    getType: function() { return this.type; },
    getMessage: function() { return JSON.parse(this.message); },
    getMessageStr: function() { return this.message; }

};

var messageHandler = function(e){
    if( e.data.message.type == "init" ) {
       MESSAGING.getInstance().setClientCredentials(e.data.xblockId, {uniqueClientId: e.data.uniqueClientId, source: e.source, clientHost: e.origin});
       e.source.postMessage(JSON.stringify( new Message("master-acknowledge",e.data.uniqueClientId)),e.origin);
    } else {
       var msg = new Message(e.data.message.type, e.data.message.message);
       MESSAGING.getInstance().handleMessage(e.data.xblockId, e.data.uniqueClientId, msg);
    }
}

window.addEventListener('message',messageHandler, false);
