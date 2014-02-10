"""TO-DO: Write a description of what this XBlock is."""
import json

import pkg_resources
import logging
import threading
import math

from xblock.core import XBlock
from xblock.fields import Scope, Integer, Any, String, Float, Dict, Boolean,List
from xblock.fragment import Fragment
from lxml import etree

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
        html = self.resource_string("static/html/worldmap.html")

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
                    """
                    #  <layer-control layerid="OpenLayers_Layer_Bing_92" visible="false" name="layerD"/>
                    +"""
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

                <problem_demo>
                    <html_demo>
                        <p>Please click on the location of <i>Timbuktu</i></p>
                    </html_demo>

                    <worldmap name='worldmap' href='http://worldmap.harvard.edu/maps/chinaX/embed?' width='800' height='600' opacityControls='true' testLatitude='16.775800549402906' testLongitude='-3.0166396836062104' testRadius='10000' debug="true">
                       <layers>
                          <layer id="OpenLayers_Layer_WMS_276">
                             <param name="EastAsiaTribes" min="449" max="545"/>
                          </layer>
                          <layer id="OpenLayers_Layer_WMS_274">
                             <param name="EastAsiaTribes" min="546" max="571"/>
                          </layer>
                          <layer id="OpenLayers_Layer_WMS_320">
                             <param name="EastAsiaTribes" min="73" max="261"/>
                          </layer>
                          <layer id="OpenLayers_Layer_WMS_324">
                             <param name="EastAsiaTribes" min="-82" max="72"/>
                          </layer>
                          <layer id="OpenLayers_Layer_WMS_294">
                             <param name="EastAsiaTribes" min="262" max="280"/>
                          </layer>
                          <layer id="OpenLayers_Layer_WMS_292">
                             <param name="EastAsiaTribes" min="281" max="326"/>
                          </layer>
                          <layer id="OpenLayers_Layer_WMS_288">
                             <param name="EastAsiaTribes" min="327" max="448"/>
                          </layer>
                          <layer id="OpenLayers_Layer_WMS_272">
                             <param name="EastAsiaTribes" value="572"/>
                          </layer>
                       </layers>
                       <sliders>
                          <slider id="EastAsiaTribes" title="East Asia Tribes" param="EastAsiaTribes" min="-82" max="572" incr="1" position="bottom">
                             <help>
                                <b>East Asia Tribes migration patterns</b>
                                From 82BCE through 572CE
                             </help>
                          </slider>
                       </sliders>
                       <group-control name="ChinaX layers">
                          <group-control name="geography">
                            <layer-control layerid="OpenLayers_Layer_WMS_332" name="Coastline1"/>
                            <layer-control layerid="OpenLayers_Layer_WMS_330" name="Yellow River"/>
                            <layer-control layerid="OpenLayers_Layer_WMS_232" name="Major Rivers"/>
                          </group-control>
                       </group-control>
                    </worldmap>
                </problem_demo>
                </vertical_demo>
             """
            ),
        ]

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

    #@classmethod
    #def parse_xml(cls, node, runtime, keys, id_generator):
    #    block = runtime.construct_xblock_from_class(cls, keys)
    #
    #    # Attributes become fields.
    #    for name, value in node.items():
    #        if name in block.fields:
    #            setattr(block, name, value)
    #
    #    # Find <help> children, turn them into help-text content.
    #    for child in node:
    #        if child.tag == "help":
    #            block.help += child.text
    #        else:
    #            block.runtime.add_node_as_child(block, child, id_generator)
    #
    #    return block


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
