"""TO-DO: Write a description of what this XBlock is."""
import json

import pkg_resources
import logging

from xblock.core import XBlock
from xblock.fields import Scope, Integer, Any, String, Float
from xblock.fragment import Fragment

log = logging.getLogger(__name__)

class WorldMapXBlock(XBlock):
    """
    A testing block that checks the behavior of the container.
    """

    # Fields are defined on the class.  You can access them in your code as
    # self.<fieldname>.

    # TO-DO: delete count, and define your own fields.
    count = Integer(
        default=0, scope=Scope.user_state,
        help="A simple counter, to show something happening",
    )
    worldmapId = Integer(
        default=0, scope=Scope.user_state,
        help="The id of this worldmap on the page - needs to be unique page-wide",
    )

    href = String(help="URL of the worldmap page at the provider", default=None, scope=Scope.content)
    zoomLevel = Integer(help="zoom level of map", default=None, scope=Scope.user_state)
    centerLat = Float(help="center of map (latitude)", default=None, scope=Scope.user_state)
    centerLon = Float(help="center of map (longitude)", default=None, scope=Scope.user_state)

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

        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/worldmap.css"))
        frag.add_javascript(unicode(pkg_resources.resource_string(__name__, "static/js/src/xBlockCom-master.js")))
        frag.add_javascript(self.resource_string("static/js/src/worldmap.js"))
        frag.initialize_js('WorldMapXBlock')
        return frag

    # TO-DO: change this handler to perform your own actions.  You may need more
    # than one handler, or you may not need any handlers at all.
    @XBlock.json_handler
    def increment_count(self, data, suffix=''):
        """
        An example handler, which increments the data.
        """
        # Just to show data coming in...
        assert data['hello'] == 'world'

        self.count += 1
        return {"count": self.count}


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
             """<vertical_demo>
                <worldmap href='http://23.21.172.243/maps/bostoncensus/embed?'/>
                <worldmap href='http://23.21.172.243/maps/bostoncensus/embed?'/>
                <worldmap href='http://23.21.172.243/maps/bostoncensus/embed?'/>
                </vertical_demo>
             """
            ),
        ]
