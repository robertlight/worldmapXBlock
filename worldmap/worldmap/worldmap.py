"""TO-DO: Write a description of what this XBlock is."""
import json

import pkg_resources
import logging
import threading
import math

from xblock.core import XBlock
from xblock.fields import Scope, Integer, Any, String, Float, Dict, Boolean
from xblock.fragment import Fragment

log = logging.getLogger(__name__)

class WorldMapXBlock(XBlock):
    """
    A testing block that checks the behavior of the container.
    """
    threadLock = threading.Lock()

    # Fields are defined on the class.  You can access them in your code as
    # self.<fieldname>.

    worldmapId = Integer(
        default=0, scope=Scope.user_state,
        help="The id of this worldmap on the page - needs to be unique page-wide",
    )

    href = String(help="URL of the worldmap page at the provider", default=None, scope=Scope.content)

    testLatitude = Float(help="latitude of test location point", default=None)
    testLongitude= Float(help="longitude of test location point", default=None)
    testRadius   = Float(help="acceptable hit radius (meters)",default=10000)

    opacityControls = Boolean(help="include opacity control sliders", default=True, scope=Scope.content)
    zoomLevel = Integer(help="zoom level of map", default=None, scope=Scope.user_state)
    centerLat = Float(help="center of map (latitude)", default=None, scope=Scope.user_state)
    centerLon = Float(help="center of map (longitude)", default=None, scope=Scope.user_state)

    layers = Dict(help="layer properties", default=None, scope=Scope.user_state)

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    # TO-DO: change this view to display your data your own way.
    def student_view(self, context=None):
        """
        The primary view of the WorldMapXBlock, shown to students
        when viewing courses.
        """
        html = self.resource_string("static/html/worldmap.html")

        layerData = "{}"
        if self.layers != None:
            layerData = json.dumps(self.layers)
        frag = Fragment(html.format(self=self, layerData=layerData))
        frag.add_css(self.resource_string("static/css/worldmap.css"))
        frag.add_css_url("http://code.jquery.com/ui/1.10.3/themes/smoothness/jquery-ui.css")
#        frag.add_css_url("http://ajax.googleapis.com/ajax/libs/jqueryui/1.8.14/themes/base/jquery-ui.css")
#        frag.add_javascript_url("http://code.jquery.com/ui/1.10.3/jquery-ui.js")
#        frag.add_javascript_url("http://code.jquery.com/ui/1.8.18/jquery-ui.min.js")
#        frag.add_javascript_url("http://ajax.googleapis.com/ajax/libs/jqueryui/1.8.16/jquery-ui.js")
        frag.add_javascript(unicode(pkg_resources.resource_string(__name__, "static/js/src/xBlockCom-master.js")))
        frag.add_javascript(self.resource_string("static/js/src/worldmap.js"))
        frag.initialize_js('WorldMapXBlock')
        return frag

    problem_view = student_view

    #Radius of earth is approx 6371km
   # DEG_PER_KM = 360./(2*6371*math.pi)
    SPHERICAL_DEFAULT_RADIUS = 6378137; #Meters

    @XBlock.json_handler
    def test_click(self, data, suffix=''):
        """
        Called when user clicks
        """
        isHit=False
        if self.testLatitude != None:
            if not data.get('y'):
               log.warn('latitude not found')
            else:
               latitude = float(data.get('y'))
               longitude= float(data.get('x'))
               dLatitude= latitude - self.testLatitude
               dLongitude=longitude - self.testLongitude
               sinHalfDeltaLon = math.sin(math.pi * (self.testLongitude-longitude)/360)
               sinHalfDeltaLat = math.sin(math.pi * (self.testLatitude-latitude)/360)
               a = sinHalfDeltaLat * sinHalfDeltaLat + sinHalfDeltaLon*sinHalfDeltaLon * math.cos(math.pi*latitude/180)*math.cos(math.pi*self.testLatitude/180)
               isHit = 2*self.SPHERICAL_DEFAULT_RADIUS*math.atan2(math.sqrt(a), math.sqrt(1-a)) < self.testRadius

        return {'hit': isHit}

    @XBlock.json_handler
    def set_zoom_level(self, data, suffix=''):
        """
        Called when zoom level is changed
        """
        if not data.get('zoomLevel'):
            log.warn('zoomLevel not found')
        else:
            self.zoomLevel = int(data.get('zoomLevel'))

        return {'zoomLevel': self.zoomLevel}

    @XBlock.json_handler
    def change_layer_properties(self, data, suffix=''):
        """
        Called when layer properties have changed
        """
        id = data.get('id')
        if not id:
            log.warn('no layerProperties found')
            return False
        else:
            # we have a threading problem... need to behave in single-threaded mode here
            self.threadLock.acquire()
            if self.layers == None:
                self.layers = {}
            self.layers[id] = {'name': data.get("name"),  'opacity': data.get("opacity"), 'visibility': data.get("visibility")}
            self.threadLock.release()
        return True

    @XBlock.json_handler
    def set_center(self, data, suffix=''):
        """
        Called when window zoomed/scrolled
        """
        if not data.get('centerLat'):
            log.warn('centerLat not found')
            return False
        else:
            self.centerLat = data.get('centerLat')
            self.centerLon = data.get('centerLon')
            self.zoomLevel = data.get('zoomLevel')

        return True

    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("WorldMapXBlock",
             """
                <vertical_demo>
                <worldmap href='http://23.21.172.243/maps/bostoncensus/embed?' opacityControls='false'/>

                <problem_demo>
                    <html_demo>
                        <p>Please click on the location of <i>Timbuktu</i></p>
                    </html_demo>

                    <worldmap name='worldmap' href='http://23.21.172.243/maps/bostoncensus/embed?' opacityControls='true' testLatitude='16.775800549402906' testLongitude='-3.0166396836062104' testRadius='10000'/>
                </problem_demo>
                </vertical_demo>
             """
            ),
        ]
