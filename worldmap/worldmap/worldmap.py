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
from shapely.geometry.point import Point
from shapely.geos import TopologicalError


log = logging.getLogger(__name__)


#*************************** UTILITY FUNCTIONS ************************************************
def makePoint(pt):
    return Point(pt['lon']+360., pt['lat'])      #pad longitude by 360 degrees to avoid int'l date line problems

def makePolygon(list):
    arr = []
    for pt in list:
        arr.append((pt['lon']+360., pt['lat']))   #pad longitude by 360 degrees to avoid int'l date line problems
    return Polygon(arr)

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

    testLatitude = Float(help="latitude of test location point", default=None)
    testLongitude= Float(help="longitude of test location point", default=None)
    testRadius   = Float(help="acceptable hit radius (meters)",default=10000)

    opacityControls = Boolean(help="include opacity control sliders", default=True, scope=Scope.content)
    zoomLevel = Integer(help="zoom level of map", default=None, scope=Scope.user_state)
    centerLat = Float(help="center of map (latitude)", default=None, scope=Scope.user_state)
    centerLon = Float(help="center of map (longitude)", default=None, scope=Scope.user_state)

    has_children = True


    #@classmethod
    #def parse_xml(cls, node, runtime, keys, id_generator):
    #    """
    #    Parse the XML for a checker. A few arguments are handled specially,
    #    then the rest get the usual treatment.
    #    """
    #    block = runtime.construct_xblock_from_class(cls, keys)
    #
    #    # Find <script> children, turn them into script content.
    #    for child in node:
    #        block.runtime.add_node_as_child(block, child, id_generator)
    #
    #    return block

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
    def point_response(self, data, suffix=''):
        padding = data['answer']['padding']
        correctPoint = data['answer']['constraints'][0]['geometry']
        userAnswer = data['point']
        latitude = userAnswer['lat']
        longitude= userAnswer['lon']
        #dLatitude= latitude - correctPoint['lat']
        #dLongitude=longitude - correctPoint['lon']
        sinHalfDeltaLon = math.sin(math.pi * (correctPoint['lon']-longitude)/360)
        sinHalfDeltaLat = math.sin(math.pi * (correctPoint['lat']-latitude)/360)
        a = sinHalfDeltaLat * sinHalfDeltaLat + sinHalfDeltaLon*sinHalfDeltaLon * math.cos(math.pi*latitude/180)*math.cos(math.pi*correctPoint['lat']/180)
        isHit = 2*self.SPHERICAL_DEFAULT_RADIUS*math.atan2(math.sqrt(a), math.sqrt(1-a)) < padding
        return {
            'answer':data['answer'],
            'isHit': isHit
        }

    @XBlock.json_handler
    def polygon_response(self, data, suffix=''):

        arr = []
        for pt in data['polygon']:
            arr.append((pt['lon']+360., pt['lat']))
        answerPolygon = Polygon(arr)

        isHit = True
        try:
            for constraint in data['answer']['constraints']:
                if( constraint['type'] == 'matches'):

                    constraintPolygon = makePolygon(constraint['geometry']['points'])
                    percentMatch = constraint['percentMatch']

                    isHit = isHit and (answerPolygon.difference(constraintPolygon).area*100/constraintPolygon.area < (100-percentMatch)) \
                          and (answerPolygon.difference(constraintPolygon).area*100/answerPolygon.area < (100-percentMatch)) \
                          and (constraintPolygon.difference(answerPolygon).area*100/constraintPolygon.area < (100-percentMatch))

                elif( constraint['type'] == 'includes' or constraint['type'] == 'excludes'):
                    if( constraint['geometry']['type'] == 'polygon' ):
                        constraintPolygon = makePolygon(constraint['geometry']['points'])

                        if( constraint['type'] == 'includes' ):
                            isHit = isHit and (constraintPolygon.difference(answerPolygon)).area == 0.0
                        else:
                            isHit = isHit and constraintPolygon.disjoint(answerPolygon)
                    elif( constraint['geometry']['type'] == 'point' ):
                        if( constraint['type'] == 'includes' ):
                            isHit = isHit and answerPolygon.contains(makePoint(constraint['geometry']))
                        else:
                            isHit = isHit and answerPolygon.disjoint(makePoint(constraint['geometry']))

        except TopologicalError:
            return {
                'answer':data['answer'],
                'isHit': False,
                'error': 'Invalid polygon topology<br/><img src="http://robertlight.com/tmp/InvalidTopology.png"/>'
            }
        except:
            print "Unexpected error: ", sys.exc_info()[0]

        return {
            'answer':data['answer'],
            'isHit': isHit
        }

    @XBlock.json_handler
    def getAnswers(self, data, suffix=''):
        if isinstance(self.get_parent(), WorldmapQuizBlock):
            arr = []
            for answer in self.get_parent().answers:
                arr.append( answer.data )

            padding = 1
            try:
                padding = self.get_parent().padding
            except ValueError:
                print "Invalid value for attribute 'padding' on tag <worldmap-quiz>"

            return {
                'answers': arr,
                'padding': padding,
                'explanation': self.get_parent().explanation.content
            }
        return None

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
            #self.threadLock.acquire()
            #if self.layers == None:
            #    self.layers = {}
            #self.layers[id] = {'name': data.get("name"),  'opacity': data.get("opacity"), 'visibility': data.get("visibility")}
            #self.threadLock.release()
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
            try:
                print "center=(",self.centerLat,",",self.centerLon,")  zoom=",self.zoomLevel;
            except:
                print "Error: ", sys.exc_info()[0]
        return True


    #<worldmap href='http://23.21.172.243/maps/bostoncensus/embed?' opacityControls='false' baseLayer='OpenLayers_Layer_Bing_92'>
    #<worldmap href='https://worldmap.harvard.edu/maps/chinaX/embed?' opacityControls='false' baseLayer='OpenLayers_Layer_Bing_92'>
    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("WorldMapXBlock",
             """
             <vertical_demo>
               <worldmap-quiz padding='500'>
                    <explanation>
                         <B>A quiz about the Boston area</B>
                    </explanation>
                    <answer id='foobar' color='00FF00' type='point' hintAfterAttempt='3'>
                       <explanation>
                          Where is the biggest island in Boston harbor?
                       </explanation>
                       <constraints>
                          <matches percentOfGrade="25" percentMatch="100" >
                              <point lat="-70.9657058456866" lon="42.32011232390349"/>
                              <explanation>
                                 <B> Look at boston harbor - pick the biggest island </B>
                              </explanation>
                          </matches>
                       </constraints>
                    </answer>
                    <answer id='baz' color='0000FF' type='point'>
                       <explanation>
                          Where is the land bridge that formed Nahant bay?
                       </explanation>
                       <constraints>
                          <matches percentOfGrade="25" percentMatch="100">
                              <point lat="-70.93824002537393" lon="42.445896458204764"/>
                              <explanation>
                                 <B>Hint:</B> Look for Nahant Bay on the map
                              </explanation>
                          </matches>
                       </constraints>
                    </answer>
                    <answer id='area' color='FF00FF' type='polygon' hintAfterAttempt='3'>
                       <explanation>
                          Draw a polygon around "back bay"?
                       </explanation>
                       <constraints hintDisplayTime='-1'>
                          <matches percentOfGrade="25" percentMatch="80">
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
                          <includes percentOfGrade="25" >
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
                          <excludes percentOfGrade="25" >
                             <point lon="-71.07071969303735" lat="42.351962566661165"/>
                             <explanation>
                                Must <B>not</B> include intersection of Boylston and Arlington Streets
                             </explanation>
                          </excludes>
                          <excludes percentOfGrade="10" >
                            <polygon>
                               <point lon="-71.06994721684204" lat="42.349520439895464"/>
                               <point lon="-71.0687455872032" lat="42.34856893624958"/>
                               <point lon="-71.07140633854628" lat="42.34863237027384"/>
                            </polygon>
                            <explanation>
                              Must <b>not</b> include <i>Bay Village</i>
                            </explanation>
                          </excludes>
                          <includes percentOfGrade="25" >
                             <point lon="-71.08303639683305" lat="42.341527361626746"/>
                             <explanation>
                                <B>Must</B> include corner of <i>Mass ave.</i> and <i>SW Corridor Park</i>
                             </explanation>
                          </includes>
                       </constraints>
                    </answer>

                <worldmap href='http://23.21.172.243/maps/bostoncensus/embed?' debug='true' width='600' height='400' opacityControls='false' baseLayer='OpenLayers_Layer_Google_116'>
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
                      <layer-control layerid="OpenLayers_Layer_WMS_306" visible="true" name="7 Capitals of the Shang Dynasty"/>
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
                      <slider id="timeSlider" title="A" param="CensusYear" min="1972" max="1980" increment="0.2" position="left"/>
                      <slider id="timeSlider7" title="Abcdefg" param="CensusYear" min="1972" max="1980" increment="0.2" position="left"/>
                      <slider id="timeSlider2" title="B" param="CensusYear" min="1972" max="1980" increment="0.2" position="right">
                         <help>
                            <B>ABC</B><br/>
                            <i>yippity doo dah</i>
                         </help>
                      </slider>
                      <slider id="timeSlider6" title="Now is the time for" param="CensusYear" min="1972" max="1980" increment="0.2" position="right">
                         <help>
                             <B>This can be any html</B><br/>
                             <i>you can use to create help info for using the slider</i><br/>
                             <b>You can even include images:</b>
                             <img src="http://static.adzerk.net/Advertisers/bc85dff2b3dc44ddb9650e1659b1ad1e.png"/>
                         </help>
                      </slider>
                      <slider id="timeSlider3" title="Hello world" param="CensusYear" min="1972" max="1980" increment="0.2" position="top"/>
                      <slider id="timeSlider8" title="Hello world12345" param="CensusYear" min="1972" max="1980" increment="0.2" position="top"/>
                      <slider id="timeSlider4" title="Now is the time for all good men" param="CensusYear" min="1972" max="1980" increment="0.2" position="bottom"/>
                      <slider id="timeSlider5" title="to come to the aid of their country" param="CensusYear" min="1972" max="1980" increment="0.2" position="bottom">
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
            </vertical_demo>
              """
             #   <worldmap-quiz padding='10'>
             #       <worldmap name='worldmap' href='http://worldmap.harvard.edu/maps/chinaX/embed?' width='800' height='600' opacityControls='true' testLatitude='16.775800549402906' testLongitude='-3.0166396836062104' testRadius='10000' debug="true">
             #          <layers>
             #             <layer id="OpenLayers_Layer_WMS_276">
             #                <param name="EastAsiaTribes" min="449" max="545"/>
             #             </layer>
             #             <layer id="OpenLayers_Layer_WMS_274">
             #                <param name="EastAsiaTribes" min="546" max="571"/>
             #             </layer>
             #             <layer id="OpenLayers_Layer_WMS_320">
             #                <param name="EastAsiaTribes" min="73" max="261"/>
             #             </layer>
             #             <layer id="OpenLayers_Layer_WMS_324">
             #                <param name="EastAsiaTribes" min="-82" max="72"/>
             #             </layer>
             #             <layer id="OpenLayers_Layer_WMS_294">
             #                <param name="EastAsiaTribes" min="262" max="280"/>
             #             </layer>
             #             <layer id="OpenLayers_Layer_WMS_292">
             #                <param name="EastAsiaTribes" min="281" max="326"/>
             #             </layer>
             #             <layer id="OpenLayers_Layer_WMS_288">
             #                <param name="EastAsiaTribes" min="327" max="448"/>
             #             </layer>
             #             <layer id="OpenLayers_Layer_WMS_272">
             #                <param name="EastAsiaTribes" value="572"/>
             #             </layer>
             #
             #             <layer id="OpenLayers_Layer_WMS_248">
             #                <param name="YellowRiver" min="-602" max="11"/>
             #             </layer>
             #             <layer id="OpenLayers_Layer_WMS_246">
             #                <param name="YellowRiver" min="12" max="1048"/>
             #             </layer>
             #             <layer id="OpenLayers_Layer_WMS_244">
             #                <param name="YellowRiver" min="1049" max="1128"/>
             #             </layer>
             #             <layer id="OpenLayers_Layer_WMS_242">
             #                <param name="YellowRiver" min="1129" max="1368"/>
             #             </layer>
             #             <layer id="OpenLayers_Layer_WMS_240">
             #                <param name="YellowRiver" min="1369" max="1855"/>
             #             </layer>
             #          </layers>
             #          <sliders>
             #             <slider id="YellowRiver" title="Yellow River" param="YellowRiver" min="-602" max="1855" incr="10" position="bottom">
             #                <help>
             #                   <b>Yellow River diversions</b><br/>
             #                   From 602BCE through 1855CE
             #                </help>
             #             </slider>
             #          </sliders>
             #          <group-control name="ChinaX layers">
             #             <group-control name="geography">
             #               <layer-control layerid="OpenLayers_Layer_WMS_332" name="Coastline1"/>
             #               <layer-control layerid="OpenLayers_Layer_WMS_330" name="Yellow River"/>
             #               <layer-control layerid="OpenLayers_Layer_WMS_232" name="Major Rivers"/>
             #               <layer-control layerid="OpenLayers_Layer_WMS_246" name="Yellow River 1048CE-1128CE"/>
             #               <layer-control layerid="OpenLayers_Layer_WMS_114" name="Expedition Route"/>
             #             </group-control>
             #          </group-control>
             #       </worldmap>
             #       <explanation>
             #            <B>How well do you know the history of the Yellow River?</B>
             #       </explanation>
             #       <answer id='foobar' color='00FF00' type='point'>
             #          <explanation>
             #             Use the tool button below and show where the diversion point for the alteration in the Yellow River circa 1855
             #          </explanation>
             #          <constraints>
             #             <matches percentOfGrade="25" percentAnswerInsidePaddedGeometry="100" percentGeometryInsidePaddedAnswer="100">
             #                 <point lat="113.523" lon="34.97248"/>
             #                 <explanation>
             #                    <B> The diversion point was just northwest of Zhengzhou </B>
             #                 </explanation>
             #             </matches>
             #          </constraints>
             #       </answer>
             #       <answer id='baz' color='0000FF' type='point'>
             #          <explanation>
             #             Where is Hong Kong?
             #          </explanation>
             #          <constraints>
             #             <matches percentOfGrade="25" percentAnswerInsidePaddedGeometry="100" percentGeometryInsidePaddedAnswer="100">
             #                 <point lat="114.21516592567018" lon="22.346155606846434"/>
             #                 <explanation>
             #                    <B> Hong Kong is on the coast north east of Macau </B>
             #                 </explanation>
             #             </matches>
             #          </constraints>
             #       </answer>
             #   </worldmap-quiz>
             #</vertical_demo>
             #"""
            ),
        ]


#******************************************************************************************************
# ASSESSMENT CLASSES
#******************************************************************************************************
class WorldmapQuizBlock(XBlock):

    padding = Integer(help="default padding distance (meters)", default=1, scope=Scope.content)

    has_score = True

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
    def answers(self):
        answers = []
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, AnswerBlock):
                answers.append(child)
        return answers

    @property
    def explanation(self):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, HelpBlock):
                return child
        return None

    problem_view = student_view

class ConstraintBlock(XBlock):

    has_children = True
    percentOfGrade = Float(help="how much of overall grade is dependent on this constraint being satisfied", default=100, scope=Scope.content)

    @property
    def data(self):
        return {
            'explanation':self.explanation.content,
            'geometry':self.geometry.data
        }
    @property
    def explanation(self):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, HelpBlock):
                return child
        return None

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
            'explanation':self.explanation.content
        }

class IncludesConstraintBlock(ConstraintBlock):

    has_children = True

    @property
    def data(self):
        return {
            'type':'includes',
            'geometry':self.geometry.data,
            'explanation':self.explanation.content
        }

class ExcludesConstraintBlock(ConstraintBlock):
    has_children = True

    @property
    def data(self):
        return {
            'type':'excludes',
            'geometry':self.geometry.data,
            'explanation':self.explanation.content
        }


class GeometryBlock(XBlock):

    has_children = True

class PointBlock(GeometryBlock):

    lat = Float(help="latitude", default=None, scope=Scope.content)
    lon = Float(help="longitude",default=None, scope=Scope.content)

    @property
    def data(self):
        return {
            'type':'point',
            'lat':self.lat,
            'lon':self.lon
        }

class PolygonBlock(GeometryBlock):

    has_children = True

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

class AnswerBlock(XBlock):

    has_children = True

    has_score = True

    id = String(help="unique id among multiple answer clauses", default=None, scope=Scope.content)
    color = String(help="the color of the polyline,polygon or marker", default="#FF0000", scope=Scope.content)
    type  = String(help="the type of the answer point|polygon|polyline|directed-polyline", default=None, scope=Scope.content)
    hintAfterAttempt= Integer(help="display hint button after N failed attempts", default=None, scope=Scope.content)

    # since we are currently only allowing a single answer, the percentOfGrade will be 100%
    percentOfGrade = Float(help="how much of overall grade is dependent on this answer", default=100, scope=Scope.content)

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
            'explanation':self.explanation.content,
            'constraints':constraints,
            'hintAfterAttempt': self.hintAfterAttempt,
            'hintDisplayTime' : self.hintDisplayTime
        }
    @property
    def explanation(self):
        for child_id in self.children:  # pylint: disable=E1101
            child = self.runtime.get_block(child_id)
            if isinstance(child, HelpBlock):
                return child
        return None

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

        for member in self.members :
            result.append(member.renderToDynatree());

        node = {'title':self.name, 'isFolder': True, 'children': result }
        if( self.visible == False ):
            node['hidden'] = True
#            node['addClass'] = "hidden"
            #node['hideCheckbox'] = True

        return node
