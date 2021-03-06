# coding=utf-8
"""TO-DO: Write a description of what this XBlock is."""
import json

import pkg_resources
import logging
import threading
import math
import sys

from xblock.core import XBlock
from xblock.fields import Scope, Integer, Any, String, Float, Dict, Boolean,List
from xblock.fragment import Fragment
from lxml import etree
from shapely.geometry.polygon import Polygon
from shapely.geometry import LineString
from shapely.geometry.point import Point
from shapely.geos import TopologicalError
from django.utils.translation import ugettext as _
from shapely import affinity
from shapely import ops
from random import randrange
from django.utils.translation import ugettext as _    #see - https://docs.djangoproject.com/en/1.3/topics/i18n/internationalization/

log = logging.getLogger(__name__)


#*************************** UTILITY FUNCTIONS ************************************************
def makePoint(pt):
    return Point(pt['lon']+360., pt['lat'])      #pad longitude by 360 degrees to avoid int'l date line problems

def makePolygon(list):
    arr = []
    for pt in list:
        arr.append((pt['lon']+360., pt['lat']))   #pad longitude by 360 degrees to avoid int'l date line problems
    return Polygon(arr)

def makeLineString(list):
    arr = []
    for pt in list:
        arr.append((pt['lon']+360., pt['lat']))   #pad longitude by 360 degrees to avoid int'l date line problems
    return LineString(arr)

#***********************************************************************************************

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
    baseLayer = String(help="id of base layer", default=None, scope=Scope.content)
    width= Integer(help="width of map", default=750)
    height=Integer(help="height of map", default=550)
    debug =Boolean(help="enable the debug pane", default=False)

    zoomLevel = Integer(help="zoom level of map", default=None, scope=Scope.user_state)
    centerLat = Float(help="center of map (latitude)", default=None, scope=Scope.user_state)
    centerLon = Float(help="center of map (longitude)", default=None, scope=Scope.user_state)

    layerState= Dict(help="dictionary of layer states, layer name is key", default={}, scope=Scope.user_state)

    has_children = True


    @property
    def worldmapType(self):
        if isinstance(self.get_parent(), WorldmapQuizBlock):
            return "quiz"
        elif isinstance(self.get_parent(), WorldmapExpositoryBlock):
            return "expository"
        else:
            return "unknown"

    @property
    def sliders(self):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, SlidersBlock):
                return child.sliders
        return None

    @property
    def layers(self):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, LayersBlock):
                return child.layers
        return None

    @property
    def topLayerGroup(self):
        for child_id in self.children: #pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if( isinstance(child, GroupControlBlock) ):
                return child
        return None

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
        self.runtime.publish(self,
            {
                'event_type': 'grade',
                'value': 5,
                'max_value': 10
            }
        )

        delimiter = "?"
        try:
            self.href.index("?")
            delimiter = "&"
        except:
            pass

        self.url = self.href + delimiter + "xblockId=worldmap_" + self.scope_ids.usage_id

        html = self.resource_string("static/html/worldmap.html")

        url = self.runtime.local_resource_url(self,"static/images/markerIcon.png")

        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/worldmap.css"))
        frag.add_css_url("http://code.jquery.com/ui/1.10.3/themes/smoothness/jquery-ui.css")
#        frag.add_css_url("http://ajax.googleapis.com/ajax/libs/jqueryui/1.8.14/themes/base/jquery-ui.css")
#        frag.add_javascript_url("http://code.jquery.com/ui/1.10.3/jquery-ui.js")
#        frag.add_javascript_url("http://code.jquery.com/ui/1.8.18/jquery-ui.min.js")
#        frag.add_javascript_url("http://ajax.googleapis.com/ajax/libs/jqueryui/1.8.16/jquery-ui.js")
        frag.add_javascript(unicode(pkg_resources.resource_string(__name__, "static/js/src/xBlockCom-master.js")))
        frag.add_javascript(self.resource_string("static/js/src/worldmap.js"))
        #frag.add_javascript_url("static/js/jquery.cookie.js")
        #frag.add_javascript_url("static/js/jquery.dynatree.js")

        frag.initialize_js('WorldMapXBlock')
        return frag

    problem_view = student_view

    #Radius of earth:
    SPHERICAL_DEFAULT_RADIUS = 6378137    #Meters

    @XBlock.json_handler
    def getSliderSetup(self, data, suffix=''):
        result = []
        if( self.sliders != None ):
            for slider in self.sliders:
                result.append({
                   'id':   slider.id,
                   'min':  slider.min,
                   'max':  slider.max,
                   'increment': slider.increment,
                   'position': slider.position,
                   'param': slider.param,
                   'title': slider.title,
                   'help':  slider.help
                })
        return result

    @XBlock.json_handler
    def getLayerSpecs(self, data, suffix=''):
        result = []
        if( self.layers != None ):
            for layer in self.layers:
                params = []
                for param in layer.params:
                    params.append({ 'name':param.name, 'value':param.value, 'min':param.min, 'max':param.max})

                result.append({
                   'id':   layer.id,
                   'params':  params
                })
        return result

    @XBlock.json_handler
    def getLayerStates(self, data, suffix=''):
        return self.layerState

    @XBlock.json_handler
    def point_response(self, data, suffix=''):
#        padding = data['answer']['padding']
        correctGeometry = data['answer']['constraints'][0]['geometry']
        padding = data['answer']['constraints'][0]['padding']
        userAnswer = data['point']
        latitude = userAnswer['lat']
        longitude= userAnswer['lon']
        hit = True

        if correctGeometry['type'] == 'polygon':
            correctPolygon = makePolygon(correctGeometry['points']).buffer(padding*180/(math.pi*self.SPHERICAL_DEFAULT_RADIUS))
            hit = correctPolygon.contains(makePoint(userAnswer))
        else:
            sinHalfDeltaLon = math.sin(math.pi * (correctGeometry['lon']-longitude)/360)
            sinHalfDeltaLat = math.sin(math.pi * (correctGeometry['lat']-latitude)/360)
            a = sinHalfDeltaLat * sinHalfDeltaLat + sinHalfDeltaLon*sinHalfDeltaLon * math.cos(math.pi*latitude/180)*math.cos(math.pi*correctGeometry['lat']/180)
            hit = 2*self.SPHERICAL_DEFAULT_RADIUS*math.atan2(math.sqrt(a), math.sqrt(1-a)) < padding

        correctExplanation = ""
        percentCorrect = 100
        if not hit :
            correctExplanation = _("incorrect location")
            percentCorrect = 0

        if isinstance(self.get_parent(), WorldmapQuizBlock ):
            self.get_parent().setScore(data['answer']['id'], percentCorrect, 100)

        return {
            'answer':data['answer'],
            'xml': "<point lon='%s' lat='%s'/>\n" % (longitude,latitude),
            'percentCorrect': percentCorrect,
            'correctExplanation': correctExplanation,
            'isHit': hit
        }

    @XBlock.json_handler
    def polygon_response(self, data, suffix=''):

        xml = "<polygon>\n"
        arr = []
        for pt in data['polygon']:
            arr.append((pt['lon']+360., pt['lat']))
            xml += "  <point lon='%s' lat='%s'/>\n" % (pt['lon'],pt['lat'])
        xml += "</polygon>"

        answerPolygon = Polygon(arr)

        additionalErrorInfo = ""

        isHit = True
        try:

            totalGradeValue = 0
            totalCorrect = 0
            for constraint in data['answer']['constraints']:
                constraintSatisfied = True


                if( constraint['type'] == 'matches'):

                    constraintPolygon = makePolygon(constraint['geometry']['points'])
                    overage = answerPolygon.difference(constraintPolygon).area
                    percentMatch = constraint['percentMatch']
                    constraintSatisfied = (overage*100/constraintPolygon.area < 1.5*(100-percentMatch))
                    if constraintSatisfied :
                        constraintSatisfied = (overage*100/answerPolygon.area < (100-percentMatch))
                        if constraintSatisfied :
                            constraintSatisfied = (constraintPolygon.difference(answerPolygon).area*100/constraintPolygon.area < (100-percentMatch))
                            if not constraintSatisfied :
                                additionalErrorInfo = _(" (polygon didn't include enough of correct area)")
                        else:
                            additionalErrorInfo = _(" (polygon didn't include enough of correct area)")
                    else:
                        additionalErrorInfo = _(" (polygon too big)")

                elif( constraint['type'] == 'includes' or constraint['type'] == 'excludes'):
                    if( constraint['geometry']['type'] == 'polygon' ):
                        constraintPolygon = makePolygon(constraint['geometry']['points'])

                        if( constraint['type'] == 'includes' ):
                            constraintSatisfied = answerPolygon.contains(constraintPolygon)
                            if constraintSatisfied and constraint['maxAreaFactor'] != None :
                                constraintSatisfied = answerPolygon.area/constraintPolygon.area < constraint['maxAreaFactor']
                                if not constraintSatisfied :
                                    additionalErrorInfo = _(" (polygon too big)")
                        else:
                            constraintSatisfied = constraintPolygon.disjoint(answerPolygon)
                    elif( constraint['geometry']['type'] == 'point' ):
                        if( constraint['type'] == 'includes' ):
                            constraintPt = makePoint(constraint['geometry'])

                            constraintSatisfied = answerPolygon.contains(constraintPt)
                            if constraintSatisfied and constraint['maxAreaFactor'] != None :
                                constraintSatisfied = answerPolygon.area/constraintPt.buffer(180*constraint['padding']/(self.SPHERICAL_DEFAULT_RADIUS*math.pi)).area < constraint['maxAreaFactor']
                                if not constraintSatisfied :
                                    additionalErrorInfo = _(" (polygon too big)")
                        else:
                            constraintSatisfied = answerPolygon.disjoint(makePoint(constraint['geometry']))
                    elif( constraint['geometry']['type'] == 'polyline' ):
                        constraintLine = makeLineString(constraint['geometry'])
                        if( constraint['type'] == 'includes' ) :
                            constraintSatisfied = answerPolygon.contains( constraintLine )
                            if constraintSatisfied and constraint['maxAreaFactor'] != None :
                                constraintSatisfied = answerPolygon.area/constraintLine.buffer(180*constraint['padding']/(self.SPHERICAL_DEFAULT_RADIUS*math.pi)).area < constraint['maxAreaFactor']
                                if not constraintSatisfied :
                                    additionalErrorInfo = _(" (polygon too big)")
                        else:
                            constraintSatisfied = not answerPolygon.disjoint( constraintLine )

                totalGradeValue += constraint['percentOfGrade']
                if constraintSatisfied :
                    totalCorrect += constraint['percentOfGrade']

                isHit = isHit and constraintSatisfied
                constraint['satisfied'] = constraintSatisfied

        except TopologicalError:
            return {
                'answer':data['answer'],
                'isHit': False,
                'error': _('Invalid polygon topology')+'<br/><img src="http://robertlight.com/tmp/InvalidTopology.png"/>'  #TODO: fix url
            }
        except:
            print _("Unexpected error: "), sys.exc_info()[0]

        percentIncorrect = math.floor( 100 - totalCorrect*100/totalGradeValue);

        if isinstance(self.get_parent(), WorldmapQuizBlock ):
            self.get_parent().setScore(data['answer']['id'], 100-percentIncorrect, 100)

        return {
            'answer':data['answer'],
            'xml': xml,
            'isHit': isHit,
            'percentCorrect': 100-percentIncorrect,
            'correctExplanation': "{:.0f}% incorrect".format(percentIncorrect)+additionalErrorInfo
        }

    @XBlock.json_handler
    def polyline_response(self, data, suffix=''):

        xml = "<polyline>\n"
        arr = []
        for pt in data['polyline']:
            arr.append((pt['lon']+360., pt['lat']))
            xml += "  <point lon='%s' lat='%s'/>\n" % (pt['lon'],pt['lat'])
        xml += "</polyline>"
        answerPolyline = LineString(arr)
        additionalErrorInfo = ""

        isHit = True
        try:

            totalGradeValue = 0
            totalCorrect = 0
            for constraint in data['answer']['constraints']:
                constraintSatisfied = True

                if constraint['type'] == 'matches' :
                    percentMatch = constraint['percentMatch']
                    answerPolygon  = answerPolyline.buffer(constraint['padding'])
                    constraintPolyline = makeLineString(constraint['geometry']['points'])

                    buffer = max(constraintPolyline.length*0.2, constraint['padding']*180/(math.pi*self.SPHERICAL_DEFAULT_RADIUS))

                    constraintPolygon = constraintPolyline.buffer(buffer)

                    constraintSatisfied = constraintPolygon.contains(answerPolyline)

                    if constraintSatisfied:
                        constraintSatisfied = abs(constraintPolyline.length - answerPolyline.length)/constraintPolyline.length < (100-percentMatch)/100.
                        if not constraintSatisfied:
                            additionalErrorInfo = _(" - The line wasn't long enough")
                    else:
                        additionalErrorInfo = _(" - You missed the proper area")
                elif constraint['type'] == "inside":
                    constraintPolygon = makePolygon(constraint['geometry']['points']).buffer(buffer)
                    constraintSatisfied = constraintPolygon.contains(answerPolyline)
                    if not constraintSatisfied:
                        additionalErrorInfo = _(" - Outside permissible boundary")
                elif constraint['type'] == 'excludes':
                    buffer = constraint['padding']*180/(math.pi*self.SPHERICAL_DEFAULT_RADIUS)
                    constraintPolygon = makePolygon(constraint['geometry']['points']).buffer(buffer)
                    constraintSatisfied = not constraintPolygon.crosses(answerPolyline)
                    if not constraintSatisfied:
                        additionalErrorInfo = _(" - Must be outside of a certain boundary")

                totalGradeValue += constraint['percentOfGrade']
                if constraintSatisfied :
                    totalCorrect += constraint['percentOfGrade']

                isHit = isHit and constraintSatisfied
                constraint['satisfied'] = constraintSatisfied

        except:
            print _("Unexpected error: "), sys.exc_info()[0]

        percentIncorrect = math.floor( 100 - totalCorrect*100/totalGradeValue);

        if isinstance(self.get_parent(), WorldmapQuizBlock ):
            self.get_parent().setScore(data['answer']['id'], 100-percentIncorrect, 100)

        return {
            'answer':data['answer'],
            'xml': xml,
            'isHit': isHit,
            'percentCorrect': 100-percentIncorrect,
            'correctExplanation': "{:.0f}% incorrect".format(percentIncorrect)+additionalErrorInfo
        }

    @XBlock.json_handler
    def getAnswers(self, data, suffix=''):
        if isinstance(self.get_parent(), WorldmapQuizBlock):
            arr = []
            for answer in self.get_parent().answers:
                try:
                    arr.append( answer.data )
                except:
                    print _("Unexpected error: "), sys.exc_info()[0]

            return {
                'answers': arr,
                'explanation': self.get_parent().explanationHTML
            }
        return None

    @XBlock.json_handler
    def getGeometry(self, data, suffix=''):
        g = self.get_parent().getGeometry(data)
        if g != None :
            return g.data
        else:
            return None

    @XBlock.json_handler
    def getFuzzyGeometry(self, data, suffix=''):
        buffer = data['buffer']*180./(self.SPHERICAL_DEFAULT_RADIUS*math.pi)

        # create a bunch of polygons that are more/less the shape of our original geometry
        geometryArr = []
        if data['type'] == 'point':
            point = Point(data['geometry']['lon']+360., data['geometry']['lat'])
            geometryArr.append( point.buffer(buffer))
            geometryArr.append( point.buffer(buffer*2))
            geometryArr.append( point.buffer(buffer*4))
            geometryArr.append( point.buffer(buffer*8))
        elif data['type'] == 'polygon' or data['type'] == 'polyline':
            arr = []
            if data['type'] == 'polygon':
                for pt in data['geometry']:
                    arr.append((pt['lon']+360., pt['lat']))
                polygon = Polygon(arr)
            else:
                for pt in data['geometry']['points']:
                    arr.append((pt['lon']+360., pt['lat']))
                polyline = LineString(arr)
                buffer = max(buffer, 0.2*polyline.length)
                polygon = LineString(arr).buffer(buffer)

            geometryArr.append( polygon.buffer(buffer*1.5))
            geometryArr.append( polygon.buffer(buffer*.5 ))
            geometryArr.append( polygon.buffer(2*buffer).buffer(-2*buffer) )
            geometryArr.append( polygon.buffer(-buffer))

        # move these polygons around a bit randomly
        r = []
        for g in geometryArr:
            arr = []
            for i in range(0,4):   # give it a blobby look
                arr.append(affinity.translate(g, 4*buffer*randrange(-500,500)/1000., 4*buffer*randrange(-500,500)/1000.,0))
            # union these randomly moved polygons back together and get their convex_hull
            hull = ops.unary_union(arr).convex_hull
            for i in range(0,10):
                r.append( affinity.translate(hull, 4*buffer*randrange(-500,500)/1000., 4*buffer*randrange(-500,500)/1000.,0))

        # output the polygons
        result = []
        for polygon in r:
            poly = []
            if( not polygon.is_empty ):
                for pt in polygon.exterior.coords:
                    poly.append( { 'lon': pt[0]-360., 'lat': pt[1]} )
                result.append(poly)

        return result

    @XBlock.json_handler
    def getExplanation(self,data,suffix=''):
        return self.get_parent().explanationHTML


    @XBlock.json_handler
    def layerTree(self, data, suffix=''):
        """
        Called to get layer tree for a particular map
        """
        if( self.topLayerGroup == None ):
            return []
        else:
            return self.topLayerGroup.renderToDynatree()

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
            self.layerState[id] = { 'name':data.get('name'), 'opacity':data.get('opacity'), 'visibility':data.get('visibility')}
            self.threadLock.release()

            pass
        return True

    @XBlock.json_handler
    def getViewInfo(self, data, suffix=''):
        """
        return most recent zoomLevel, center location
        """
        if self.zoomLevel == None or self.centerLat == None or self.centerLon == None:
            return None
        else:
            return {
                'zoomLevel': self.zoomLevel,
                'centerLat': self.centerLat,
                'centerLon': self.centerLon
            }

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
                <worldmap-expository>
                    <worldmap href='http://23.21.172.243/maps/bostoncensus/embed' debug='true' width='600' height='400' baseLayer='OpenLayers_Layer_Google_116'>
                       <layers>
                          <layer id="geonode:qing_charity_v1_mzg"/>
                          <layer id="OpenLayers_Layer_WMS_122">
                          </layer>
                          <layer id="OpenLayers_Layer_WMS_124">
                          </layer>
                          <layer id="OpenLayers_Layer_WMS_120">
                          </layer>
                          <layer id="OpenLayers_Layer_WMS_118">
                          </layer>
                          <layer id="OpenLayers_Layer_Vector_132">
                          </layer>
                       </layers>
                    </worldmap>
                    <explanation>
                          testing Chinese: 基區提供本站原典資料庫收藏之外的許多經典文獻的全文閱讀和檢索功<br/>
                          Lorem ipsum dolor sit amet, <a href='#' onclick='return highlight(\"backbay\", 0, -2)'>Back Bay</a> adipiscing elit. Aliquam a neque diam . Cras ac erat nisi. Etiam aliquet ultricies lobortis <a href='#' onclick='return highlight(\"esplanade\")'>Esplanade</a>. Etiam lacinia malesuada leo, pretium egestas mauris suscipit at. Fusce ante mi, faucibus a purus quis, commodo accumsan ipsum. Morbi vitae ultrices nibh. Quisque quis dolor elementum sem mollis pharetra vitae quis magna. Duis auctor pretium ligula a eleifend.
                          <p/>Curabitur sem <a href='#' onclick='return highlightLayer(\"OpenLayers_Layer_WMS_124\",5000, -2)'>layer diam</a>, congue sed vehicula vitae  <a href='#' onclick='return highlight(\"bay-village\", 10000, -5)'>Bay Village</a>, lobortis pulvinar odio. Phasellus ac lacus sapien. Nam nec tempus metus, sit amet ullamcorper tellus. Nullam ac nibh semper felis vulputate elementum eget in ligula. Integer semper pharetra orci, et tempor orci commodo a. Duis id faucibus felis. Maecenas bibendum accumsan nisi, ut semper quam elementum quis. Donec erat libero, pretium sollicitudin augue a, suscipit mollis libero. Mauris aliquet sem eu ligula rutrum imperdiet. Proin quis velit congue, fermentum ligula vitae, eleifend nisi. Sed justo est, egestas id nisl non, fringilla vulputate orci. Ut non nisl vitae lectus tincidunt sollicitudin. Donec ornare purus eu dictum sollicitudin. Aliquam erat volutpat.
                          <p/>Vestibulum ante ipsum primis <a href='#' onclick='return highlight(\"beltway\",4000, -1)'>beltway around boston</a> faucibus orci luctus et <a href='#' onclick='return highlight(\"big-island\", 2000)'>Big Island</a>ultrices posuere cubilia Curae; Quisque purus dolor, fermentum eu vestibulum nec, ultricies semper tellus. Vivamus nunc mi, fermentum a commodo vel, iaculis in odio. Vivamus commodo mi convallis, congue magna eget, sodales sem. Morbi facilisis nunc vitae porta elementum. Praesent auctor vitae nisi a pharetra. Mauris non urna auctor nunc dignissim mollis. In sem ipsum, porta sit amet dignissim ut, adipiscing eu dui. Nam sodales nisi quis urna malesuada, quis aliquet ipsum placerat.

                    </explanation>
                    <polygon id='backbay'>
                         <point lon="-71.09350774082822" lat="42.35148683512319"/>
                         <point lon="-71.09275672230382" lat="42.34706235935522"/>
                         <point lon="-71.08775708470029" lat="42.3471733715164"/>
                         <point lon="-71.08567569050435" lat="42.34328782922443"/>
                         <point lon="-71.08329388889936" lat="42.34140047917672"/>
                         <point lon="-71.07614848408352" lat="42.347379536438645"/>
                         <point lon="-71.07640597614892" lat="42.3480456031057"/>
                         <point lon="-71.0728225449051"  lat="42.34785529906382"/>
                         <point lon="-71.07200715336435" lat="42.34863237027516"/>
                         <point lon="-71.07228610310248" lat="42.34942529018035"/>
                         <point lon="-71.07011887821837" lat="42.35004376076278"/>
                         <point lon="-71.0708055237264"  lat="42.351835705270716"/>
                         <point lon="-71.07325169834775" lat="42.35616470553563"/>
                         <point lon="-71.07408854756031" lat="42.35600613935877"/>
                         <point lon="-71.07483956608469" lat="42.357131950552244"/>
                         <point lon="-71.09331462177917" lat="42.35166127043902"/>
                    </polygon>
                    <polygon id='esplanade'>
                        <point lon="-71.07466790470745" lat="42.35719537593463"/>
                        <point lon="-71.08492467197995" lat="42.35399231410341"/>
                        <point lon="-71.08543965611076" lat="42.35335802506911"/>
                        <point lon="-71.08822915348655" lat="42.35250172471913"/>
                        <point lon="-71.08814332279839" lat="42.352279719020736"/>
                        <point lon="-71.08689877781501" lat="42.35253343975517"/>
                        <point lon="-71.07411000523211" lat="42.355958569427614"/>
                        <point lon="-71.07466790470745" lat="42.35719537593463"/>
                    </polygon>
                    <polygon id="bay-village">
                       <point lon="-71.06994721684204" lat="42.349520439895464"/>
                       <point lon="-71.0687455872032" lat="42.34856893624958"/>
                       <point lon="-71.07140633854628" lat="42.34863237027384"/>
                    </polygon>
                    <polyline id="beltway">
                      <point lon='-71.0604629258' lat='42.3434622873'/>
                      <point lon='-71.0645827988' lat='42.3262044544'/>
                      <point lon='-71.0522231797' lat='42.3160505758'/>
                      <point lon='-71.0549697617' lat='42.3099574622'/>
                      <point lon='-71.0412368515' lat='42.2967536924'/>
                      <point lon='-71.0426101426' lat='42.2804990976'/>
                      <point lon='-71.0522231797' lat='42.268305399'/>
                      <point lon='-71.0275039414' lat='42.2428942831'/>
                      <point lon='-71.0247573594' lat='42.2296764566'/>
                      <point lon='-71.0467300156' lat='42.2093359332'/>
                      <point lon='-71.1030349472' lat='42.202215202'/>
                      <point lon='-71.1552200058' lat='42.2144216783'/>
                      <point lon='-71.1840591172' lat='42.2317101486'/>
                      <point lon='-71.2074050644' lat='42.2550928966'/>
                      <point lon='-71.2019119004' lat='42.2723702273'/>
                      <point lon='-71.2019119004' lat='42.285579109'/>
                      <point lon='-71.2197646836' lat='42.2987852218'/>
                      <point lon='-71.256843541' lat='42.3373718282'/>
                      <point lon='-71.2650832871' lat='42.3657889233'/>
                      <point lon='-71.260963414' lat='42.3931789538'/>
                      <point lon='-71.256843541' lat='42.4235983077'/>
                      <point lon='-71.258216832' lat='42.4580557417'/>
                      <point lon='-71.2444839219' lat='42.4722385889'/>
                      <point lon='-71.2074050644' lat='42.4823672268'/>
                      <point lon='-71.1909255722' lat='42.487430931'/>
                      <point lon='-71.164833043' lat='42.4965445656'/>
                      <point lon='-71.1208877305' lat='42.5046444593'/>
                      <point lon='-71.0920486191' lat='42.50363203'/>
                      <point lon='-71.082435582' lat='42.5188167484'/>
                      <point lon='-71.0590896347' lat='42.5238775014'/>
                      <point lon='-71.0439834336' lat='42.5167923324'/>
                      <point lon='-71.0316238144' lat='42.5157800999'/>
                      <point lon='-71.0069045762' lat='42.5167923324'/>
                      <point lon='-70.989051793' lat='42.5228653836'/>
                    </polyline>
                    <point id="big-island" lon="-70.9657058456866" lat="42.32011232390349"/>
                </worldmap-expository>

                <worldmap-quiz>
                    <explanation>
                         A quiz about the Boston area... particularly <B><a href='#' onclick='return highlight(\"backbay\", 5000, -2)'>Back Bay</a></B>
                    </explanation>
                    <polygon id='backbay'>
                         <point lon="-71.09350774082822" lat="42.35148683512319"/>
                         <point lon="-71.09275672230382" lat="42.34706235935522"/>
                         <point lon="-71.08775708470029" lat="42.3471733715164"/>
                         <point lon="-71.08567569050435" lat="42.34328782922443"/>
                         <point lon="-71.08329388889936" lat="42.34140047917672"/>
                         <point lon="-71.07614848408352" lat="42.347379536438645"/>
                         <point lon="-71.07640597614892" lat="42.3480456031057"/>
                         <point lon="-71.0728225449051"  lat="42.34785529906382"/>
                         <point lon="-71.07200715336435" lat="42.34863237027516"/>
                         <point lon="-71.07228610310248" lat="42.34942529018035"/>
                         <point lon="-71.07011887821837" lat="42.35004376076278"/>
                         <point lon="-71.0708055237264"  lat="42.351835705270716"/>
                         <point lon="-71.07325169834775" lat="42.35616470553563"/>
                         <point lon="-71.07408854756031" lat="42.35600613935877"/>
                         <point lon="-71.07483956608469" lat="42.357131950552244"/>
                         <point lon="-71.09331462177917" lat="42.35166127043902"/>
                    </polygon>
                    <answer id='foobar' color='00FF00' type='point' hintAfterAttempt='0'>
                       <explanation>
                          Where is the biggest island in Boston harbor?
                       </explanation>
                       <constraints>
                          <matches percentOfGrade="25" percentMatch="100" padding='1000'>
                              <point lon="-70.9657058456866" lat="42.32011232390349"/>
                              <explanation>
                                 <B> Look at boston harbor - pick the biggest island </B>
                              </explanation>
                          </matches>
                       </constraints>
                    </answer>
                    <answer id='baz' color='0000FF' type='polygon' hintAfterAttempt='2'>
                       <explanation>
                          Draw a polygon around the land bridge that formed Nahant bay?
                       </explanation>
                       <constraints>
                          <includes percentOfGrade="25" padding='500' maxAreaFactor='15'>
                              <point lon="-70.93824002537393" lat="42.445896458204764"/>
                              <explanation>
                                 <B>Hint:</B> Look for Nahant Bay on the map
                              </explanation>
                          </includes>
                       </constraints>
                    </answer>
                    <answer id='area' color='FF00FF' type='polygon' hintAfterAttempt='2'>
                       <explanation>
                          Draw a polygon around "back bay"?
                       </explanation>
                       <constraints hintDisplayTime='-1'>
                          <matches percentOfGrade="25" percentMatch="60" padding='1000'>
                             <polygon>
                                 <point lon="-71.09350774082822" lat="42.35148683512319"/>
                                 <point lon="-71.09275672230382" lat="42.34706235935522"/>
                                 <point lon="-71.08775708470029" lat="42.3471733715164"/>
                                 <point lon="-71.08567569050435" lat="42.34328782922443"/>
                                 <point lon="-71.08329388889936" lat="42.34140047917672"/>
                                 <point lon="-71.07614848408352" lat="42.347379536438645"/>
                                 <point lon="-71.07640597614892" lat="42.3480456031057"/>
                                 <point lon="-71.0728225449051"  lat="42.34785529906382"/>
                                 <point lon="-71.07200715336435" lat="42.34863237027516"/>
                                 <point lon="-71.07228610310248" lat="42.34942529018035"/>
                                 <point lon="-71.07011887821837" lat="42.35004376076278"/>
                                 <point lon="-71.0708055237264"  lat="42.351835705270716"/>
                                 <point lon="-71.07325169834775" lat="42.35616470553563"/>
                                 <point lon="-71.07408854756031" lat="42.35600613935877"/>
                                 <point lon="-71.07483956608469" lat="42.357131950552244"/>
                                 <point lon="-71.09331462177917" lat="42.35166127043902"/>
                             </polygon>
                             <explanation>
                                 <B>Hint:</B> Back bay was a land fill into the Charles River basin
                             </explanation>
                          </matches>
                          <includes percentOfGrade="25" padding='100'>
                             <polygon>
                                <point lon="-71.07466790470745" lat="42.35719537593463"/>
                                <point lon="-71.08492467197995" lat="42.35399231410341"/>
                                <point lon="-71.08543965611076" lat="42.35335802506911"/>
                                <point lon="-71.08822915348655" lat="42.35250172471913"/>
                                <point lon="-71.08814332279839" lat="42.352279719020736"/>
                                <point lon="-71.08689877781501" lat="42.35253343975517"/>
                                <point lon="-71.07411000523211" lat="42.355958569427614"/>
                                <point lon="-71.07466790470745" lat="42.35719537593463"/>
                             </polygon>
                             <explanation>
                                <B>Must</B> include the esplanade
                             </explanation>
                          </includes>
                          <excludes percentOfGrade="25" padding='25'>
                             <point lon="-71.07071969303735" lat="42.351962566661165"/>
                             <explanation>
                                Must <B>not</B> include intersection of Boylston and Arlington Streets
                             </explanation>
                          </excludes>
                          <excludes percentOfGrade="10" padding='150'>
                            <polygon>
                               <point lon="-71.06994721684204" lat="42.349520439895464"/>
                               <point lon="-71.0687455872032" lat="42.34856893624958"/>
                               <point lon="-71.07140633854628" lat="42.34863237027384"/>
                            </polygon>
                            <explanation>
                              Must <b>not</b> include <i>Bay Village</i>
                            </explanation>
                          </excludes>
                          <includes percentOfGrade="25" padding='50' >
                             <point lon="-71.08303639683305" lat="42.341527361626746" />
                             <explanation>
                                <B>Must</B> include corner of <i>Mass ave.</i> and <i>SW Corridor Park</i>
                             </explanation>
                          </includes>
                       </constraints>
                    </answer>
                    <answer id='esplanade' color='00FF00' type='polygon' hintAfterAttempt='2'>
                       <explanation>
                           Draw a polygon around the esplanade
                       </explanation>
                       <constraints hintDisplayTime='-1'>
                          <matches percentMatch='50' percentOfGrade="25"  padding='0'>
                             <polygon>
                                <point lon="-71.07466790470745" lat="42.35719537593463"/>
                                <point lon="-71.08492467197995" lat="42.35399231410341"/>
                                <point lon="-71.08543965611076" lat="42.35335802506911"/>
                                <point lon="-71.08822915348655" lat="42.35250172471913"/>
                                <point lon="-71.08814332279839" lat="42.352279719020736"/>
                                <point lon="-71.08689877781501" lat="42.35253343975517"/>
                                <point lon="-71.07411000523211" lat="42.355958569427614"/>
                                <point lon="-71.07466790470745" lat="42.35719537593463"/>
                             </polygon>
                             <explanation>
                                <B>Must</B> include the esplanade
                             </explanation>
                          </matches>
                       </constraints>
                    </answer>
                    <answer id='boffo' color='00FFFF' type='polyline' hintAfterAttempt='2'>
                       <explanation>
                          Draw a polyline on the land bridge that formed Nahant bay?
                       </explanation>
                       <constraints hintDisplayTime='-1'>
                          <matches percentOfGrade="100" padding='500'>
                              <polyline>
                                 <point lon="-70.93703839573509" lat="42.455142795067786"/>
                                 <point lon="-70.93978497776635" lat="42.44146279890606"/>
                                 <point lon="-70.93360516819578" lat="42.43082073646349"/>
                              </polyline>
                              <explanation>
                                 <B>Hint:</B> Look for Nahant Bay on the map - draw a polyline on the land bridge out to Nahant Island
                              </explanation>
                          </matches>
                          <inside percentOfGrade="25"  padding='1'>
                             <polygon>
                                 <point lon="-70.9210738876792" lat="42.47325152648776"/>
                                 <point lon="-70.95746609959279" lat="42.471732113995365"/>
                                 <point lon="-70.93686673435874" lat="42.42005014321707"/>
                                 <point lon="-70.91901395115596" lat="42.433734814183005"/>
                             </polygon>
                             <explanation>
                                The land bridge is somewhere inside this polygon
                             </explanation>
                          </inside>
                          <excludes percentOfGrade="25" padding="1">
                             <polygon>
                                <point lon="-70.9252795914228" lat="42.42955370389016"/>
                                <point lon="-70.93763921056394" lat="42.42581580857819"/>
                                <point lon="-70.93652341161325" lat="42.416438412427965"/>
                                <point lon="-70.92828366551946" lat="42.41795916653644"/>
                                <point lon="-70.92905614171568" lat="42.42112728581168"/>
                                <point lon="-70.91978642736025" lat="42.424105171979036"/>
                                <point lon="-70.91789815221426" lat="42.420683758749576"/>
                                <point lon="-70.90983006749771" lat="42.416375046873334"/>
                                <point lon="-70.90536687169678" lat="42.416628508708406"/>
                                <point lon="-70.90227696691106" lat="42.41992341934355"/>
                                <point lon="-70.91060254369391" lat="42.42708291670639"/>
                                <point lon="-70.91927144322945" lat="42.42949035158941"/>
                             </polygon>
                             <explanation>
                                Must not include Nahant Island
                             </explanation>
                          </excludes>
                       </constraints>
                    </answer>
                    <worldmap href='http://23.21.172.243/maps/bostoncensus/embed' debug='true' width='600' height='400' baseLayer='OpenLayers_Layer_Google_116'>
                       <layers>
                          <layer id="geonode:qing_charity_v1_mzg"/>
                          <layer id="OpenLayers_Layer_WMS_122">
                             <param name="CensusYear" value="1972"/>
                          </layer>
                          <layer id="OpenLayers_Layer_WMS_124">
                             <param name="CensusYear" min="1973" max="1977"/>
                          </layer>
                          <layer id="OpenLayers_Layer_WMS_120">
                             <param name="CensusYear" value="1976"/>
                          </layer>
                          <layer id="OpenLayers_Layer_WMS_118">
                             <param name="CensusYear" value="1978"/>
                          </layer>
                          <layer id="OpenLayers_Layer_Vector_132">
                             <param name="CensusYear" value="1980"/>
                          </layer>
                       </layers>
                       <group-control name="Census Data" visible="true">
                          <layer-control layerid="OpenLayers_Layer_WMS_120" visible="true" name="layer0"/>
                          <layer-control layerid="OpenLayers_Layer_WMS_122" visible="true" name="layerA"/>
                          <layer-control layerid="OpenLayers_Layer_WMS_124" visible="true" name="layerB"/>
                          <layer-control layerid="OpenLayers_Layer_WMS_120" visible="false" name="layerC"/>
                          <layer-control layerid="OpenLayers_Layer_WMS_118" visible="true" name="layerE"/>
                          <layer-control layerid="OpenLayers_Layer_Vector_132" visible="true" name="layerF"/>
                          <group-control name="A sub group of layers">
                             <group-control name="A sub-sub-group">
                                <layer-control layerid="OpenLayers_Layer_WMS_118" visible="true" name="layerE.1"/>
                                <layer-control layerid="OpenLayers_Layer_Vector_132" visible="true" name="layerF.1"/>
                             </group-control>
                             <group-control name="another sub-sub-group" visible="false">
                                <layer-control layerid="OpenLayers_Layer_WMS_118" visible="true" name="layerE.2"/>
                                <layer-control layerid="OpenLayers_Layer_Vector_132" visible="true" name="layerF.2"/>
                             </group-control>
                             <layer-control layerid="OpenLayers_Layer_WMS_122" visible="true" name="layerA.1"/>
                             <layer-control layerid="OpenLayers_Layer_WMS_124" visible="true" name="layerB.1"/>
                          </group-control>
                       </group-control>

                       <sliders>
                          <slider id="timeSlider5" title="slider:原典資料" param="CensusYear" min="1972" max="1980" increment="0.2" position="bottom">
                             <help>
                                 <B>This is some generalized html</B><br/>
                                 <i>you can use to create help info for using the slider</i>
                                 <ul>
                                    <li>You can explain what it does</li>
                                    <li>How to interpret things</li>
                                    <li>What other things you might be able to do</li>
                                 </ul>
                             </help>
                          </slider>
                        </sliders>
                    </worldmap>
                </worldmap-quiz>
                <worldmap-quiz>
                    <explanation>
                         <B>A quiz about the Boston area</B>
                    </explanation>
                    <answer id='foobar' color='00FF00' type='point' hintAfterAttempt='3'>
                       <explanation>
                          Where is the biggest island in Boston harbor?
                       </explanation>
                       <constraints>
                          <matches percentOfGrade="25" percentMatch="100" padding='1000'>
                              <point lon="-70.9657058456866" lat="42.32011232390349"/>
                              <explanation>
                                 <B> Look at boston harbor - pick the biggest island </B>
                              </explanation>
                          </matches>
                       </constraints>
                    </answer>
                    <answer id='baz' color='0000FF' type='polygon' hintAfterAttempt='2'>
                       <explanation>
                          Draw a polygon around the land bridge that formed Nahant bay?
                       </explanation>
                       <constraints>
                          <includes percentOfGrade="25" padding='500' maxAreaFactor='15'>
                              <point lon="-70.93824002537393" lat="42.445896458204764"/>
                              <explanation>
                                 <B>Hint:</B> Look for Nahant Bay on the map
                              </explanation>
                          </includes>
                       </constraints>
                    </answer>
                    <answer id='boffo' color='00FFFF' type='polyline' hintAfterAttempt='2'>
                       <explanation>
                          Draw a polyline on the land bridge that formed Nahant bay?
                       </explanation>
                       <constraints hintDisplayTime='-1'>
                          <matches percentOfGrade="100" padding='500'>
                              <polyline>
                                 <point lon="-70.93703839573509" lat="42.455142795067786"/>
                                 <point lon="-70.93978497776635" lat="42.44146279890606"/>
                                 <point lon="-70.93360516819578" lat="42.43082073646349"/>
                              </polyline>
                              <explanation>
                                 <B>Hint:</B> Look for Nahant Bay on the map - draw a polyline on the land bridge out to Nahant Island
                              </explanation>
                          </matches>
                          <inside percentOfGrade="25"  padding='1'>
                             <polygon>
                                 <point lon="-70.9210738876792" lat="42.47325152648776"/>
                                 <point lon="-70.95746609959279" lat="42.471732113995365"/>
                                 <point lon="-70.93686673435874" lat="42.42005014321707"/>
                                 <point lon="-70.91901395115596" lat="42.433734814183005"/>
                             </polygon>
                             <explanation>
                                The land bridge is somewhere inside this polygon
                             </explanation>
                          </inside>
                          <excludes percentOfGrade="25" padding="1">
                             <polygon>
                                <point lon="-70.9252795914228" lat="42.42955370389016"/>
                                <point lon="-70.93763921056394" lat="42.42581580857819"/>
                                <point lon="-70.93652341161325" lat="42.416438412427965"/>
                                <point lon="-70.92828366551946" lat="42.41795916653644"/>
                                <point lon="-70.92905614171568" lat="42.42112728581168"/>
                                <point lon="-70.91978642736025" lat="42.424105171979036"/>
                                <point lon="-70.91789815221426" lat="42.420683758749576"/>
                                <point lon="-70.90983006749771" lat="42.416375046873334"/>
                                <point lon="-70.90536687169678" lat="42.416628508708406"/>
                                <point lon="-70.90227696691106" lat="42.41992341934355"/>
                                <point lon="-70.91060254369391" lat="42.42708291670639"/>
                                <point lon="-70.91927144322945" lat="42.42949035158941"/>
                             </polygon>
                             <explanation>
                                Must not include Nahant Island
                             </explanation>
                          </excludes>
                       </constraints>
                    </answer>
                    <worldmap href='http://23.21.172.243/maps/bostoncensus/embed' debug='true' width='600' height='400' baseLayer='OpenLayers_Layer_Google_116'>

                       <group-control name="Census Data" visible="true" expand="true">
                          <layer-control layerid="OpenLayers_Layer_WMS_120" visible="true" name="原典資料"/>
                          <layer-control layerid="OpenLayers_Layer_WMS_122" visible="true" name="layerA"/>
                          <layer-control layerid="OpenLayers_Layer_WMS_124" visible="true" name="layerB"/>
                          <layer-control layerid="OpenLayers_Layer_WMS_120" visible="false" name="layerC"/>
                          <layer-control layerid="OpenLayers_Layer_WMS_118" visible="true" name="layerE"/>
                          <layer-control layerid="OpenLayers_Layer_Vector_132" visible="true" name="layerF"/>
                          <group-control name="A sub group of layers">
                             <group-control name="A sub-sub-group">
                                <layer-control layerid="OpenLayers_Layer_Vector_132" visible="true" name="layerF.1"/>
                             </group-control>
                             <group-control name="another sub-sub-group" visible="true">
                                <layer-control layerid="OpenLayers_Layer_WMS_118" visible="false" name="layerE.2"/>
                                <layer-control layerid="OpenLayers_Layer_Vector_132" visible="false" name="layerF.2"/>
                             </group-control>
                             <layer-control layerid="OpenLayers_Layer_WMS_122" visible="true" name="layerA.1"/>
                             <layer-control layerid="OpenLayers_Layer_WMS_124" visible="true" name="layerB.1"/>
                          </group-control>
                       </group-control>

                    </worldmap>
                </worldmap-quiz>
             </vertical_demo>
             """
            ),
        ]


#******************************************************************************************************
# ASSESSMENT CLASSES
#******************************************************************************************************
class WorldmapExpositoryBlock(XBlock):

    has_children = True

    def student_view(self, context=None):
        """Provide default student view."""
        result = Fragment()
        child_frags = self.runtime.render_children(self, context=context)
        result.add_frags_resources(child_frags)

        # for now, we'll render this just as a vertical layout....
        result.add_css("""
            .vertical {
                border: solid 1px #888; padding: 3px;
            }
            """)
        result.add_content(self.runtime.render_template("vertical.html", children=child_frags))
        return result

    @property
    def worldmap(self):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, WorldMapXBlock):
                return child
        return None

    @property
    def explanationHTML(self):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, HelpBlock):
                return child.content
        return ""

    def getGeometry(self, id):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, GeometryBlock) and child.id == id:
                return child
        return None

    problem_view = student_view

class WorldmapQuizBlock(WorldmapExpositoryBlock):

    has_children = True


    @property
    def answers(self):
        answers = []
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, AnswerBlock):
                answers.append(child)
        return answers

    def setScore(self, answerId, value, max_value):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if (isinstance(child, AnswerBlock) and child.id == answerId) :
                child.setScore(value,max_value)
                return
        raise "Answer not found for id="+answerId


class ConstraintBlock(XBlock):

    has_children = True
    percentOfGrade = Float(help="how much of overall grade is dependent on this constraint being satisfied", default=100, scope=Scope.content)
    padding = Integer(help="default padding distance (meters)", default=1, scope=Scope.content)

    @property
    def data(self):
        return {
            'explanation':self.explanationHTML,
            'geometry':self.geometry.data,
            'percentOfGrade':self.percentOfGrade,
            'padding':self.padding
        }

    @property
    def explanationHTML(self):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, HelpBlock):
                return child.content
        return ""


    @property
    def geometry(self):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, GeometryBlock):
                return child
        raise RuntimeError("no geometry found")

class MatchesConstraintBlock(ConstraintBlock):

    has_children = True
    percentMatch= Float("percent of answer matching ideal geometry", default=80, scope=Scope.content)

    @property
    def data(self):
        return {
            'type':'matches',
            'percentMatch':self.percentMatch,
            'geometry':self.geometry.data,
            'padding':self.padding,
            'percentOfGrade':self.percentOfGrade,
            'explanation':self.explanationHTML
        }

class InsideOfConstraintBlock(ConstraintBlock):

    has_children = True

    @property
    def data(self):
        return {
            'type':'inside',
            'geometry':self.geometry.data,
            'padding':self.padding,
            'percentOfGrade':self.percentOfGrade,
            'explanation':self.explanationHTML
        }

class IncludesConstraintBlock(ConstraintBlock):

    has_children = True

    maxAreaFactor = Float("drawn polygon must be no more than maxAreaFactor times the size of the included polygon", default=None, scope=Scope.content)

    @property
    def data(self):
        return {
            'type':'includes',
            'geometry':self.geometry.data,
            'padding':self.padding,
            'percentOfGrade':self.percentOfGrade,
            'maxAreaFactor':self.maxAreaFactor,
            'explanation':self.explanationHTML
        }

class ExcludesConstraintBlock(ConstraintBlock):
    has_children = True

    @property
    def data(self):
        return {
            'type':'excludes',
            'geometry':self.geometry.data,
            'padding':self.padding,
            'percentOfGrade':self.percentOfGrade,
            'explanation':self.explanationHTML
        }


class GeometryBlock(XBlock):

    has_children = True
    id = String(help="string id of geometry", default=None)

class PointBlock(GeometryBlock):

    lat = Float(help="latitude", default=None, scope=Scope.content)
    lon = Float(help="longitude",default=None, scope=Scope.content)

    def student_view(self, context=None):
        """no view"""
        pass

    @property
    def data(self):
        return {
            'type':'point',
            'lat':self.lat,
            'lon':self.lon
        }

class PolygonBlock(GeometryBlock):

    has_children = True

    def student_view(self, context=None):
        """no view"""
        pass

    @property
    def points(self):
        points = []
        for child_id in self.children: #pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child,PointBlock):
                points.append(child)
        return points

    @property
    def data(self):
        pts = []
        for pt in self.points:
            pts.append(pt.data)
        return {
            'type': 'polygon',
            'points':pts
        }

class PolylineBlock(PolygonBlock):

    @property
    def data(self):
        pts = []
        for pt in self.points:
            pts.append(pt.data)
        return {
            'type': 'polyline',
            'points':pts
        }

class AnswerBlock(XBlock):

    has_children = True

    has_score = True

    id = String(help="unique id among multiple answer clauses", default=None, scope=Scope.content)
    color = String(help="the color of the polyline,polygon or marker", default="#FF0000", scope=Scope.content)
    type  = String(help="the type of the answer point|polygon|polyline|directed-polyline", default=None, scope=Scope.content)
    hintAfterAttempt= Integer(help="display hint button after N failed attempts", default=None, scope=Scope.content)

    def student_view(self, context=None):
        """no view"""
        pass

    @property
    def data(self):
        constraints = []
        for constraint in self.constraints:
            constraints.append(constraint.data)

        return {
            'id':self.id,
            'color':self.color,
            'type':self.type,
            'explanation':self.explanationHTML,
            'constraints':constraints,
            'hintAfterAttempt': self.hintAfterAttempt,
            'hintDisplayTime' : self.hintDisplayTime
        }
    @property
    def explanationHTML(self):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, HelpBlock):
                return child.content
        return ""

    @property
    def constraints(self):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, ConstraintsBlock):
                return child.constraints
        return None

    @property
    def hintDisplayTime(self):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, ConstraintsBlock):
                return child.hintDisplayTime
        return None

    def setScore(self, value, max_value):
        self.runtime.publish(self, {
            'event_type':'grade',
            'value':value,
            'max_value':max_value
        })

    problem_view = student_view

class ConstraintsBlock(XBlock):
    """An XBlock that records the constraint definitions."""

    hintDisplayTime= Integer(help="how long to display hint (millis) use -1=until click", default="5000", scope=Scope.content)

    has_children = True

    @property
    def constraints(self):

        constraints = []
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, ConstraintBlock):
                constraints.append(child)
        return constraints


    def problem_view(self, context=None):
        """
        has no visible rendering
        """
        pass

    student_view = problem_view



#***********************************************************************************************************
#  Worldmap layout items
#***********************************************************************************************************
class SlidersBlock(XBlock):
    """An XBlock that records the slider definitions."""

    has_children = True

    @property
    def sliders(self):
        sliders = []
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, SliderBlock):
                sliders.append(child)
        return sliders


    def problem_view(self, context=None):
        """
        has no visible rendering
        """
        pass

    student_view = problem_view

class SliderBlock(XBlock):
    """An XBlock that records the slider definition."""

    has_children = True

    id = String(help="worldmap slider id", default=None, scope=Scope.content)
    param = String(help="the param the slider controls", default=None, scope=Scope.content)
    min = Float(help="the minimum value of the slider", default=None, scope=Scope.content)
    max = Float(help="the maximum value of the slider", default=None, scope=Scope.content)
    increment= Float(help="increment value for the slider", default=None, scope=Scope.content)
    position=String(help="position of slider.  Values: top,bottom,left,right", default="bottom", scope=Scope.content)
    title=String(help="title/label for slider",default=None, scope=Scope.content)

    @property
    def params(self):
        params = []
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, ParamBlock):
                params.append(child)
        return params

    @property
    def help(self):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, HelpBlock):
                return child.content
        return None

    def problem_view(self, context=None):
        """
        has no visible rendering
        """
        pass

    student_view = problem_view

#**** HelpBlock is also used for "explanation" tags
class HelpBlock(XBlock):
    """An XBlock that contains help-text for a slider."""

    content = String(help="The HTML to display", scope=Scope.content, default=u"")

    @classmethod
    def parse_xml(cls, node, runtime, keys, id_generator):
        """
        Parse the XML for an HTML block.

        The entire subtree under `node` is re-serialized, and set as the
        content of the XBlock.

        """
        block = runtime.construct_xblock_from_class(cls, keys)

        block.content = unicode(node.text or u"")
        for child in node:
            block.content += etree.tostring(child, encoding='unicode')

        return block

    def problem_view(self, context=None):
        """
        has no visible rendering
        """
        pass

    student_view = problem_view

class LayersBlock(XBlock):
    """An XBlock that records the layer definitions."""

    has_children = True

    @property
    def layers(self):
        layers = []
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, LayerBlock):
                layers.append(child)
        return layers


    def problem_view(self, context=None):
        """
        has no visible rendering
        """
        pass

    student_view = problem_view

class LayerBlock(XBlock):
    """An XBlock that records the layer definition."""

    has_children = True

    id = String(help="worldmap layer id", default=None, scope=Scope.content)

    @property
    def params(self):
        params = []
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, ParamBlock):
                params.append(child)
        return params

    def problem_view(self, context=None):
        """
        has no visible rendering
        """
        pass

    student_view = problem_view

class ParamBlock(XBlock):
    """An XBlock that records the layer parameter info."""

    has_children = False

    name  = String(help="worldmap layer parameter name",  default=None, scope=Scope.content)
    value = String(help="worldmap layer parameter value", default=None, scope=Scope.content)
    min   = Float(help="worldmap layer parameter range minimum", default=None, scope=Scope.content)
    max   = Float(help="worldmap layer parameter range maximum", default=None, scope=Scope.content)

    def problem_view(self, context=None):
        """
        has no visible rendering
        """
        pass

    student_view = problem_view

class LayerControlBlock(XBlock):
    """An XBlock that records the layer-control definition."""

    has_children = False

    layerid = String(help="worldmap layer id", default=None, scope=Scope.content)
    name    = String(help="visible name of the layer", default=None, scope=Scope.content)
    visible = Boolean(help="whether or not the control should be visible", default=True, scope=Scope.content)

    def problem_view(self, context=None):
        """
        has no visible rendering
        """
        pass

    student_view = problem_view

    def renderToDynatree(self):
        node = { 'title': self.name, 'key': self.layerid }
        if( self.visible == False ):
            node['hidden'] = True
#            node['addClass'] = "hidden"
        return node

class GroupControlBlock(LayerControlBlock):
    """An XBlock that records the layer group definition."""

    has_children = True

    name    = String(help="visible name of the group", default="Layer Group", scope=Scope.content)
    visible = Boolean(help="whether or not the control should be visible", default=True, scope=Scope.content)
    expand  = Boolean(help="whether or not the group control should be expanded", default=False, scope=Scope.content)

    @property
    def members(self):
        result = []
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, LayerControlBlock):
                result.append(child)
        return result

    def problem_view(self, context=None):
        """
        has no visible rendering
        """
        pass

    student_view = problem_view

    def renderToDynatree(self):
        result = []

        allInvisible = True
        for member in self.members :
            result.append(member.renderToDynatree())
            if member.visible :
                allInvisible = False

        node = {'title':self.name, 'isFolder': not allInvisible, 'children': result, 'expand': self.expand }
        if( self.visible == False ):
            node['hidden'] = True
#            node['addClass'] = "hidden"
            #node['hideCheckbox'] = True

        return node
