'''
------------------------------------------
Red9 Studio Pack: Maya Pipeline Solutions
Author: Mark Jackson
email: rednineinfo@gmail.com

Red9 blog : http://red9-consultancy.blogspot.co.uk/
MarkJ blog: http://markj3d.blogspot.co.uk
------------------------------------------

This is the core of the Animation Toolset Lib, a suite of tools 
designed from production experience to automate an animators life.

Setup : Follow the Install instructions in the Modules package
================================================================

Code examples: =================================================

#######################
 ProcessNodes 
#######################

    All of the functions which have the ProcessNodes call share the same
    underlying functionality as described below. This is designed to process the 
    given input nodes in a consistent manor across all the functions. 
    Params: 'nodes' and 'filterSettings' are treated as special and build up a 
    MatchedNode object that contains a tuple of matching pairs based on the given settings.

#######################
 snapTransform example: 
#######################
        
    import Red9_CoreUtils as r9Core
    import maya.cmds as cmds

    #Make a settings object and set the internal filters
    settings=r9Core.FilterNode_Settings()
    settings.nodeTypes='nurbsCurve'
    settings.searchAttrs='Control_Marker'
    settings.printSettings()
    
    #Option 1: Run the snap using the settings object to filter the hierarchies
    #for specific nodes within each root hierarchy
    anim=r9Anim.AnimFunctions()
    anim.snapTransform(nodes=cmds.ls(sl=True),time=r9Anim.timeLineRangeGet(),filterSettings=settings)
    
    #Option 2: Run the snap by passing in an already processed MatchedNodeInput object
    #Make the MatchedNode object and process the hierarchies by passing the settings object in
    matched=r9Core.MatchedNodeInputs(nodes=cmds.ls(sl=True),filterSettings=settings)
    matched.processMatchedPairs()
    for n in matched.MatchedPairs:print n #see what's been filtered
    
    #Rather than passing in the settings or nodes, pass in the already processed MatchedNode
    anim.snapTransform(nodes=matched,time=r9Anim.timeLineRangeGet())
        
'''


from __future__ import with_statement #required only for Maya2009/8
import maya.cmds as cmds
import maya.mel as mel

import Red9.startup.setup as r9Setup
import Red9_CoreUtils as r9Core
import Red9_General as r9General
import Red9_PoseSaver as r9Pose
import Red9_Meta as r9Meta

from functools import partial
import os
import random

import Red9.packages.configobj as configobj
#import configobj

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)



#===========================================================================
# Generic Utility Functions
#===========================================================================

def checkRunTimeCmds():
    '''
    Ensure the RedRuntime Command plugin is loaded. 
    '''
    try:
        if not cmds.pluginInfo('SnapRuntime.py', query=True, loaded=True):
            try:
                cmds.loadPlugin('SnapRuntime.py')
            except:
                raise StandardError('SnapRuntime Plug-in could not be loaded')
    except:
        raise StandardError('SnapRuntime Plug-in not found')
 
def getChannelBoxSelection():
    '''
    return a list of attributes selected in the ChannelBox
    '''
    return cmds.channelBox('mainChannelBox', q=True, selectedMainAttributes=True)

def getChannelBoxAttrs(node=None,asDict=True,incLocked=True):
    '''
    return a dict of attributes in the ChannelBox by their status
    @param node: given node
    @param asDict:  True returns a dict with keys 'keyable','locked','nonKeyable' of attrs
                    False returns a list (non ordered) of all attrs available on the channelBox
    @param incLocked: True by default - whether to include locked channels in the return (only valid if not asDict)
    '''
    statusDict={}
    if not node:
        node = cmds.ls(sl=True, l=True)[0]
    statusDict['keyable']=cmds.listAttr(node, k=True, u=True)
    statusDict['locked'] =cmds.listAttr(node, k=True, l=True)
    statusDict['nonKeyable'] =cmds.listAttr(node,cb=True)
    if asDict:
        return statusDict
    else:
        attrs=[]
        if statusDict['keyable']:
            attrs.extend( statusDict['keyable'])
        if statusDict['nonKeyable']:
            attrs.extend(statusDict['nonKeyable'])
        if incLocked and statusDict['locked']:
            attrs.extend(statusDict['locked'])
        return attrs

def getSettableChannels(node=None, incStatics=True):
    '''
    return a list of settable attributes on a given node
    @param node: node to inspect
    @param incStatics: whether to include non-keyable static channels (On by default)
    
    FIXME: BUG some Compund attrs such as constraints return invalid data for some of the
    base functions using this as they can't be simply set. Do we strip them here?
    ie: pointConstraint.target.targetWeight
    '''
    if not node:
        node = cmds.ls(sl=True, l=True)[0]
    if not incStatics:
        #keyable and unlocked only
        return cmds.listAttr(node, k=True, u=True)
    else:
        #all settable attrs in the channelBox
        return getChannelBoxAttrs(node,asDict=False,incLocked=False)
        

def getAnimLayersFromGivenNodes(nodes):
    '''
    return all animLayers associated with the given nodes
    '''
    if not isinstance(nodes,list):
        #This is a hack as the cmds.animLayer call is CRAP. It doesn't mention
        #anywhere in the docs that you can even pass in Maya nodes, yet alone 
        #that it has to take a list of nodes and fails with invalid flag if not
        nodes=[nodes]
    return cmds.animLayer(nodes, q=True, affectedLayers=True)

def timeLineRangeGet():
    '''
    Return the current PlaybackTimeline OR if a range is selected in the
    TimeLine, (Highlighted in Red) return that instead.
    @rtype: tuple
    @return: (start,end)
    '''
    playbackRange = None
    PlayBackSlider = mel.eval('$tmpVar=$gPlayBackSlider')
    if cmds.timeControl(PlayBackSlider , q=True, rangeVisible=True):
        time = cmds.timeControl(PlayBackSlider , q=True, rangeArray=True)
        playbackRange = (time[0], time[1])
    else:
        playbackRange = (cmds.playbackOptions(q=True, min=True), cmds.playbackOptions(q=True, max=True))
    return playbackRange

def timeLineRangeProcess(start, end, step):
    '''
    Simple wrapper function to take a given framerange and return
    a list[] containing the actual keys required for processing.
    This manages whether the step is negative, if so it reverses the 
    times. Basically just a wrapper to the python range function.
    '''
    startFrm = start
    endFrm = end
    if step < 0:
        startFrm = end
        endFrm = start
    return [time for time in range(int(startFrm), int(endFrm), int(step))]
 
    
#def timeLineRangeSet(time):
#    '''
#    Return the current PlaybackTimeline OR if a range is selected in the
#    TimeLine, (Highlighted in Red) return that instead.
#    '''
#    PlayBackSlider = mel.eval('$tmpVar=$gPlayBackSlider')
#    time=cmds.timeControl(PlayBackSlider ,e=True, rangeArray=True, v=time)


def pointOnPolyCmd(nodes):
    '''
    This is a BUG FIX for Maya's command wrapping of the pointOnPolyCon
    which doesn't support namespaces. This deals with that limitation
    '''
    import maya.app.general.pointOnPolyConstraint
    cmds.select(nodes)
    sourceName = nodes[0].split('|')[-1]
    
    cmdstring = "string $constraint[]=`pointOnPolyConstraint -weight 1`;"
    assembled = maya.app.general.pointOnPolyConstraint.assembleCmd()
    
    if ':' in sourceName:
        nameSpace = sourceName.replace(sourceName.split(':')[-1], '')
        assembled = assembled.replace(nameSpace, '')
    print(cmdstring + assembled)
    mel.eval(cmdstring + assembled)
    
def eulerSelected():
    '''
    cheap trick! for selected objects run a Euler Filter and then delete Static curves
    NOTE: delete sc fails if the nodes are in animLayers
    '''
    cmds.filterCurve(cmds.ls(sl=True,l=True))
    cmds.delete(cmds.ls(sl=True,l=True),sc=True)

class AnimationUI(object):
    
    def __init__(self, dockUI=True):
        self.buttonBgc = r9Setup.red9ButtonBGC(1)#[0.6, 0.8, 0.6]
        self.win = 'Red9AnimToolsWin'
        self.dockCnt = 'Red9AnimToolsDoc'
        self.label = 'Red9 AnimationTools'
        self.internalConfigPath=False
        self.dock = dockUI
        
        #take generic filterSettings Object
        self.filterSettings = r9Core.FilterNode_Settings()
        self.filterSettings.transformClamp=True
        self.presetDir = os.path.join(r9Setup.red9ModulePath(), 'presets')
        
        #Pose Management variables
        self.posePath=None #working variable
        self.posePathLocal='Local Pose Path not yet set' 
        self.posePathProject='Project Pose Path not yet set'
        self.posePathMode='localPoseMode' # or 'project' : mode of the PosePath field and UI
        self.poseSelected=None 
        self.poseGridMode='thumb'  # or text
        self.poseRootMode='RootNode' # or MetaRig
        self.poses=None
        self.poseButtonBGC=[0.27,0.3,0.3]         #[0.2,0.25,0.25] 
        self.poseButtonHighLight=[0.7,0.95,0.75]  #[0.6, 0.9,0.65]
        
        #Internal config file setup for the UI state
        if self.internalConfigPath:
            self.ui_optVarConfig = os.path.join(self.presetDir,'__red9config__')
        else:
            self.ui_optVarConfig = os.path.join(r9Setup.mayaPrefs(),'__red9config__')
        self.ANIM_UI_OPTVARS=dict()
        self.__uiCache_readUIElements()

    @classmethod
    def show(cls):
        cls()._showUI() 
           
    def _showUI(self):
        try:
            #'Maya2011 dock delete'
            if cmds.dockControl(self.dockCnt, exists=True):
                cmds.deleteUI(self.dockCnt, control=True)  
        except:
            pass
        
        if cmds.window(self.win, exists=True): cmds.deleteUI(self.win, window=True)
        animwindow = cmds.window(self.win , title=self.label)#, widthHeight=(325, 420))
        
        self.MainLayout = cmds.columnLayout(adjustableColumn=True)
        
        self.form = cmds.formLayout()
        self.tabs = cmds.tabLayout(innerMarginWidth=5, innerMarginHeight=5)
        cmds.formLayout(self.form, edit=True, attachForm=((self.tabs, 'top', 0), 
                                                          (self.tabs, 'left', 0), 
                                                          (self.tabs, 'bottom', 0), 
                                                          (self.tabs, 'right', 0)))

        #TAB1: ####################################################################
        
        self.AnimLayout = cmds.columnLayout(adjustableColumn=True)
        cmds.separator(h=5, style='none')
        
        #====================
        # CopyAttributes
        #====================
        cmds.frameLayout(label='Copy Attributes', cll=True, borderStyle='etchedOut')
        cmds.columnLayout(adjustableColumn=True)
        cmds.button(label='Copy Attributes', bgc=self.buttonBgc, 
                    ann='CopyAttributes : Modes:\n------------------------------' + \
                     '\nDefault > Selected Object Pairs (Obj2 to Obj1), (Obj3 to Obj4)' + \
                     '\nHierarchy > Uses Selection Filters on Hierarchy Tab' + \
                     '\nCopyToMany > Copy data from First selected to all Subsequent nodes' + \
                     '\nNote: This also handles CharacterSets and SelectionSets if selected, processing all members', 
                    command=partial(self.__uiCall, 'CopyAttrs'))
       
        cmds.separator(h=5, style='none')
        cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 100), (2, 100), (3, 100)], columnSpacing=[(1, 10), (2, 10)])
        self.uicbCAttrHierarchy = cmds.checkBox('uicbCAttrHierarchy', l='Hierarchy', al='left', v=False, 
                                                ann='Copy Attributes Hierarchy : Filter Hierarchies for transforms & joints then Match NodeNames')
                                                #onc="cmds.checkBox('uicbCAttrToMany', e=True, v=False)")    
        self.uicbCAttrToMany = cmds.checkBox('uicbCAttrToMany', l='CopyToMany', al='left', v=False, 
                                                ann='Copy Matching Attributes from First selected to all Subsequently selected nodes')
                                                #onc="cmds.checkBox('uicbCAttrHierarchy', e=True, v=False)")      
        self.uicbCAttrChnAttrs = cmds.checkBox(ann='Copy only those channels selected in the channelBox', 
                                            l='ChBox Attrs', al='left', v=False)       
        cmds.setParent(self.AnimLayout)
              
        #====================
        # CopyKeys
        #====================
        cmds.separator(h=10, st='in')
        cmds.frameLayout(label='Copy Keys', cll=True, borderStyle='etchedOut')
        cmds.columnLayout(adjustableColumn=True)
        cmds.button(label='Copy Keys', bgc=self.buttonBgc, 
                    ann='CopyKeys : Modes:\n-------------------------' + \
                     '\nDefault > Selected Object Pairs (Obj2 to Obj1), (Obj3 to Obj4)' + \
                     '\nHierarchy > Uses Selection Filters on Hierarchy Tab' + \
                     '\nCopyToMany > Copy data from First selected to all Subsequent nodes' + \
                     '\nNote: This also handles CharacterSets and SelectionSets if selected, processing all members', 
                    command=partial(self.__uiCall, 'CopyKeys'))
       
        cmds.separator(h=5, style='none')
        cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 100), (2, 100), (3, 100)], columnSpacing=[(1, 10), (2, 10)])
        self.uicbCKeyHierarchy = cmds.checkBox('uicbCKeyHierarchy', l='Hierarchy', al='left', v=False, 
                                            ann='Copy Keys Hierarchy : Filter Hierarchies for transforms & joints then Match NodeNames')#, \
                                            #onc="cmds.checkBox('uicbCKeyToMany', e=True, v=False)")      
        self.uicbCKeyToMany = cmds.checkBox('uicbCKeyToMany', l='CopyToMany', al='left', v=False, 
                                            ann='Copy Animation from First selected to all Subsequently selected nodes')#, \
                                            #onc="cmds.checkBox('uicbCKeyHierarchy', e=True, v=False)")  
        self.uicbCKeyChnAttrs = cmds.checkBox(ann='Copy only those channels selected in the channelBox', 
                                            l='ChBox Attrs', al='left', v=False)   
        self.uicbCKeyRange = cmds.checkBox(ann='ONLY Copy Keys over PlaybackTimeRange or Selected TimeRange (in Red on the timeline)', 
                                            l='TimeRange', al='left', v=False)   
        cmds.setParent(self.AnimLayout)


        #====================
        # SnapTransforms
        #====================
        cmds.separator(h=10, st='in')
        cmds.frameLayout(label='Snap Transforms', cll=True, borderStyle='etchedOut')
        cmds.columnLayout(adjustableColumn=True)
        cmds.button(label='Snap Transforms', bgc=self.buttonBgc, 
                     ann='Snap Selected Object Pairs (Obj2 to Obj1), (Obj4 to Obj3) or Snap Filtered Hierarchies' + \
                    '    Note: This also handles CharacterSets if selected, processing all members', 
                     command=partial(self.__uiCall, 'Snap'))
        cmds.separator(h=5, style='none')

        cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 100), (2, 100), (3, 100)], columnSpacing=[(1, 10), (2, 10)])

        self.uicbSnapRange = cmds.checkBox(ann='Snap Nodes over PlaybackTimeRange or Selected TimeRange (in Red on the timeline)', 
                                            l='TimeRange', al='left', v=False, 
                                            cc=partial(self.__uiCB_manageSnapTime))  
        self.uicbSnapPreCopyKeys = cmds.checkBox(ann='Copy all animation data for all channels prior to running the Snap over Time', 
                                            l='PreCopyKeys', al='left', en=False, v=True)               
        self.uiifgSnapStep = cmds.intFieldGrp('uiifgSnapStep', l='FrmStep', en=False, value1=1, cw2=(50, 40), 
                                           ann='Frames to advance the timeline after each Process Run')

        self.uicbSnapHierarchy = cmds.checkBox(ann='Filter Hierarchies with given args - then Snap Transforms for matched nodes', 
                                            l='Hierarchy', al='left', v=False, 
                                            cc=partial(self.__uiCB_manageSnapHierachy)) 
        self.uicbSnapPreCopyAttrs = cmds.checkBox(ann='Copy all Values for all channels prior to running the Snap', 
                                            l='PreCopyAttrs', al='left', en=False, v=True) 
        self.uiifSnapIterations = cmds.intFieldGrp('uiifSnapIterations', l='Iterations', en=False, value1=1, cw2=(50, 40), 
                                           ann='This is the number of iterations over each hierarchy node during processing, if you get issues during snap then increase this')
        cmds.setParent('..')
        cmds.separator(h=5, style='none')


        #====================
        # Stabilizer
        #====================
        cmds.separator(h=10, st='in')
        cmds.frameLayout(label='Track or Stabilize', cll=True, borderStyle='etchedOut')
        cmds.columnLayout(adjustableColumn=True)
        
        cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 80), (2, 110), (3, 115)], columnSpacing=[(1, 10), (3, 5)])
        self.uicbStabRange = cmds.checkBox(ann='Process over PlaybackTimeRange or Selected TimeRange (in Red on the timeline)', 
                                            l='TimeRange', al='left', v=False) 
        self.uiifgStabStep = cmds.intFieldGrp('uiifgStabStep', l='FrmStep', value1=1, cw2=(50, 50), 
                                           ann='Frames to advance the timeline between Processing - accepts negative values')
        cmds.button(label='Process', bgc=self.buttonBgc, 
                     ann='Stabilize Mode : Select a SINGLE Object - this will stabilize it in place over time\
                     \nTrack Object Mode : Select TWO Objects - first is source, second will track with offset\
                     \nTrack Component Mode :  Select a Component (poly,vert,edge) then an Object - second will track the component with offset',
                     command=partial(self.__uiCall, 'Stabilize'))   

        cmds.setParent(self.AnimLayout)  
        
        
        #====================
        # TimeOffset
        #====================
        cmds.separator(h=10, st='in')
        cmds.frameLayout(label='TimeOffset', cll=True, borderStyle='etchedOut')
        cmds.columnLayout(adjustableColumn=True)

        cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 100), (2, 100), (3, 100)], columnSpacing=[(1, 10), (2, 10), (3, 5)])
        self.uicbTimeOffsetHierarchy = cmds.checkBox('uicbTimeOffsetHierarchy', 
                                            l='Hierarchy', al='left', en=True, v=False, 
                                            ann='Offset Hierarchy', 
                                            ofc=partial(self.__uiCB_manageTimeOffsetChecks, 'Off'), 
                                            onc=partial(self.__uiCB_manageTimeOffsetChecks))
              
        self.uicbTimeOffsetScene = cmds.checkBox('uicbTimeOffsetScene', 
                                            l='FullScene', 
                                            ann='ON:Scene Level Processing: OFF:SelectedNode Processing - Offsets Animation, Sound and Clip data as appropriate', 
                                            al='left', v=False, 
                                            ofc=partial(self.__uiCB_manageTimeOffsetChecks, 'Off'), 
                                            onc=partial(self.__uiCB_manageTimeOffsetChecks, 'Full'))    
        
        self.uicbTimeOffsetPlayback = cmds.checkBox('OffsetTimelines', l='OffsetTimelines', 
                                            ann='ON:Scene Level Processing: OFF:SelectedNode Processing - Offsets Animation, Sound and Clip data as appropriate', 
                                            al='left', v=False, en=False)        
        cmds.setParent('..')   
        cmds.separator(h=5, style='none')
        cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 100), (2, 100), (3, 100)], columnSpacing=[(1, 10), (2, 10), (3, 5)])
        self.uicbTimeOffsetFlocking = cmds.checkBox('uicbTimeOffsetFlocking', 
                                            l='Flocking', al='left', en=True, v=False, 
                                            ann='Offset Selected Nodes by incremental amounts')
        self.uicbTimeOffsetRandom = cmds.checkBox('uicbTimeOffsetRandom', l='Randomizer', 
                                            ann='Randomize the offsets using the offset field as the max such that offsets are random(0,offset)', 
                                            al='left', v=False)  
        self.uiffgTimeOffset = cmds.floatFieldGrp('uiffgTimeOffset', l='Offset ', value1=1, cw2=(35, 60), 
                                            ann='Frames to offset the data by')
        cmds.setParent('..')
        cmds.button(label='Offset', bgc=self.buttonBgc, 
                     ann='If processing at Scene Level then this will offset all appropriate: AnimCurves,Sound and Clips\n\
                     If processing on selected it will deal with each node type as it finds', 
                     command=partial(self.__uiCall, 'TimeOffset'))  
        cmds.setParent(self.AnimLayout) 
        
        #====================
        # Mirror Controls
        #====================
        cmds.separator(h=10, st='in')
        cmds.frameLayout(label='Mirror Controls', cll=True, borderStyle='etchedOut')
        cmds.columnLayout(adjustableColumn=True)

        cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 100), (2, 100), (3, 100)], columnSpacing=[(1, 10), (2, 10), (3, 5)])
        self.uicbMirrorHierarchy = cmds.checkBox('uicbMirrorHierarchy', 
                                            l='Hierarchy', al='left', en=True, v=False, 
                                            ann='Mirror Hierarchy, or Mirror Selected nodes if they have the Mirror Marker data')
              
        cmds.setParent('..')   
        
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 160), (2, 160)], columnSpacing=[(2, 2)])
        cmds.button(label='Mirror Animation', bgc=self.buttonBgc, 
                     ann='Mirror the Animation - NOTE Layers and Trax are NOT supported yet', 
                     command=partial(self.__uiCall, 'MirrorAnim'))  
        cmds.button(label='Mirror Pose', bgc=self.buttonBgc, 
                     ann='Mirror the Current Pose', 
                     command=partial(self.__uiCall, 'MirrorPose'))  

        cmds.setParent(self.AnimLayout) 
        cmds.setParent(self.tabs)
        
    
        #TAB2: ####################################################################
        
        #=====================================================================
        # Hierarchy Controls Main filterSettings Object
        #=====================================================================
        
        self.FilterLayout = cmds.columnLayout(adjustableColumn=True)
        
        cmds.separator(h=15, style='none')
        cmds.text('Filter Settings : A Hierarchy search pattern\n'\
                  'used by all the Hierarchy checkboxes on the main tabs\n'\
                  'Particularly relevant for complex Animation Rigs\n'\
                  'as it allows you to pin-point required controllers\n\n'\
                  'Note that if these are all blank then hierarchy\n'\
                  'checkBoxes will process all children of the roots')
        cmds.separator(h=20,style='in')
                                          
        #This bit is bullshit! the checkBox align flag is now obsolete so the label is always on the left regardless :(                                  
        self.uiclHierarchyFilters = cmds.columnLayout('uiclHierarchyFilters', adjustableColumn=True, enable=True)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1,120),(2,200)],columnSpacing=[2,3])
        cmds.text(label='MetaRig',align='right')
        self.uicbMetaRig = cmds.checkBox('uicbMetaRig',
                                          ann='Switch to MetaRig Sub Systems', 
                                          l='', 
                                          v=True,
                                          cc=lambda x:self.__uiCB_managePoseRootMethod('uicbMetaRig'))
        cmds.setParent(self.uiclHierarchyFilters)
        
        self.uitfgSpecificNodeTypes = cmds.textFieldGrp('uitfgSpecificNodeTypes', 
                                            ann='RMB QuickSelector for Common Types : Search for "Specific NodeTypes" in the hierarchy, list separated by ","', 
                                            label='Specific NodeTypes', text="", cw2=(120, 200))
        cmds.popupMenu()
        cmds.menuItem(label='ClearAll', command=partial(self.__uiCB_addToNodeTypes, 'clearAll'))
        cmds.menuItem(label='nodeType : Transform', command=partial(self.__uiCB_addToNodeTypes, 'transform'))
        cmds.menuItem(label='nodeType : NurbsCurves', command=partial(self.__uiCB_addToNodeTypes, 'nurbsCurve'))
        cmds.menuItem(label='nodeType : NurbsSurfaces', command=partial(self.__uiCB_addToNodeTypes, 'nurbsSurface'))
        cmds.menuItem(label='nodeType : Joints', command=partial(self.__uiCB_addToNodeTypes, 'joint'))
        cmds.menuItem(label='nodeType : Locators', command=partial(self.__uiCB_addToNodeTypes, 'locator'))
        cmds.menuItem(label='nodeType : Meshes', command=partial(self.__uiCB_addToNodeTypes, 'mesh'))
        cmds.menuItem(label='nodeType : Cameras', command=partial(self.__uiCB_addToNodeTypes, 'camera'))
        cmds.menuItem(label='nodeType : hikIKEffector', command=partial(self.__uiCB_addToNodeTypes, 'hikIKEffector'))
        self.uitfgSpecificAttrs = cmds.textFieldGrp('uitfgSpecificAttrs', 
                                            ann='Search for "Specific Attributes" on Nodes in the hierarchy, list separated by ","', 
                                            label='Search Attributes', text="", cw2=(120, 200))
        self.uitfgSpecificPattern = cmds.textFieldGrp('uitfgSpecificPattern', 
                                            ann='Search for specific nodeName Patterns, list separated by "," - Note this is a Python.regularExpression - ^ clamps to the start, $ clamps to the end', 
                                            label='Search Name Pattern', text="", cw2=(120, 200))        
        cmds.separator(h=5, style='none')
        cmds.text('Internal Node Priorities:')
        self.uitslFilterPriority = cmds.textScrollList('uitslFilterPriority', numberOfRows=8, allowMultiSelection=False, 
                                               height=60, enable=True, append=self.filterSettings.filterPriority)
        cmds.popupMenu()
        cmds.menuItem(label='Clear Process Priorities', command=lambda x:self.__uiSetPriorities('clear'))
        cmds.menuItem(label='Set Priorities from Selected', command=lambda x:self.__uiSetPriorities('set'))
        cmds.menuItem(label='Append Priorities from Selected', command=lambda x:self.__uiSetPriorities('append'))
        cmds.menuItem(label='Remove selected from list', command=lambda x:self.__uiSetPriorities('remove'))
        cmds.menuItem(divider=True)
        cmds.menuItem(label='Move Up', command=lambda x:self.__uiSetPriorities('moveUp'))
        cmds.menuItem(label='Move Down', command=lambda x:self.__uiSetPriorities('moveDown'))        
        cmds.separator(h=20,style='in')
        cmds.text('Available Presets:')      
        self.uitslPresets = cmds.textScrollList(numberOfRows=8, allowMultiSelection=False, 
                                               selectCommand=partial(self.__uiPresetSelection), 
                                               height=80)
        cmds.popupMenu()
        cmds.menuItem(label='DeletePreset', command=partial(self.__uiPresetDelete))
        cmds.menuItem(label='OpenPresetDir', command=partial(self.__uiPresetOpenDir))
        
        cmds.separator(h=10, style='none')
        self.uicbIncRoots = cmds.checkBox('uicbIncRoots',
                                            ann='include RootNodes in the Filter', 
                                            l='Include Roots', 
                                            al='left', v=True,
                                            cc=lambda x:self.__uiCache_storeUIElements())
                                            #cc=lambda x:self.__uiCache_addCheckbox('uicbIncRoots'))
       
        cmds.separator(h=10, style='none')
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 162), (2, 162)])
        cmds.button(label='Test Filter', bgc=self.buttonBgc, 
                     ann='Test the Hierarchy Filter on the selected root node', 
                     command=partial(self.__uiCall, 'HierarchyTest')) 
        cmds.button(label='Store New Filter', bgc=self.buttonBgc, 
                     ann='Store this filterSetting Object', 
                     command=partial(self.__uiPresetStore)) 
        cmds.setParent(self.FilterLayout)
        cmds.setParent(self.tabs)
        

        #TAB3: ####################################################################
        
        #=====================================================================
        # Pose Saver Tab
        #=====================================================================
        
        self.poseUILayout = cmds.columnLayout(adjustableColumn=True)
        cmds.separator(h=10, style='none')
        self.uitfgPosePath = cmds.textFieldButtonGrp('uitfgPosePath', 
                                            ann='PosePath', 
                                            text="", 
                                            bl='PosePath',
                                            bc=lambda * x: self.__uiCB_setPosePath(fileDialog=True),
                                            cc=lambda * x:self.__uiCB_setPosePath(),
                                            cw=[(1,260),(2,40)])
        
        cmds.rowColumnLayout(nc=2,columnWidth=[(1, 120), (2, 120)],columnSpacing=[(1, 10)])
        self.uircbPosePathMethod = cmds.radioCollection('posePathMode')
        cmds.radioButton('localPoseMode', label='Local Poses',
                                        ann='local mode gives you full control to save,delete and load the library',
                                        onc=partial(self.__uiCB_switchPosePathMode,'local'),
                                        ofc=partial(self.__uiCB_switchPosePathMode,'project'))
        cmds.radioButton('projectPoseMode',label='Project Poses' ,
                                        ann='Project mode disables all but the load functionality of the library',
                                        onc=partial(self.__uiCB_switchPosePathMode,'project'),
                                        ofc=partial(self.__uiCB_switchPosePathMode,'local'))
        cmds.setParent(self.poseUILayout)
        cmds.separator(h=10, style='in')
        
        if r9Setup.mayaVersion()>2012: #tcc flag not supported in earlier versions
            self.searchFilter=cmds.textFieldGrp('tfPoseSearchFilter', label='searchFilter : ',text='', 
                                                cw=((1,87),(2,160)),
                                                tcc=lambda x:self.__uiCB_fillPoses(searchFilter=cmds.textFieldGrp('tfPoseSearchFilter',q=True,text=True)))         
        else :
            self.searchFilter=cmds.textFieldGrp('tfPoseSearchFilter', label='searchFilter : ',text='', 
                                                cw=((1,87),(2,160)),
                                                fcc=True,
                                                cc=lambda x:self.__uiCB_fillPoses(searchFilter=cmds.textFieldGrp('tfPoseSearchFilter',q=True,text=True)))
        cmds.separator(h=10, style='none')
        
        #Main PoseFields
        self.uitslPoses = cmds.textScrollList('uitslPoses',numberOfRows=8, allowMultiSelection=False, 
                                               selectCommand=partial(self.__uiPresetSelection), \
                                               height=350,vis=False)
        
        self.uiglPoseScroll = cmds.scrollLayout('uiglPoseScroll', 
                                                cr=True, 
                                                height=350, 
                                                hst=16,  
                                                vst=16, 
                                                vis=False, 
                                                rc=lambda * x:self.__uiCB_gridResize())
        self.uiglPoses = cmds.gridLayout('uiglPoses', cwh=(100,100), cr=False, ag=True)

        cmds.setParent(self.poseUILayout)
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 162), (2, 162)])
        cmds.button('loadPoseButton',label='Load Pose', bgc=self.buttonBgc, 
                     ann='Load Pose data for the given Hierarchy or Selections', 
                     command=partial(self.__uiCall, 'PoseLoad')) 
        cmds.button('savePoseButton',label='Save Pose', bgc=self.buttonBgc, 
                     ann='Save Pose data for the given Hierarchy or Selections', 
                     command=partial(self.__uiCall, 'PoseSave')) 
        cmds.setParent(self.poseUILayout)
        cmds.separator(h=10, style='in')
        cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 80), (2, 250)])
        self.uicbPoseHierarchy = cmds.checkBox('uicbPoseHierarchy', 
                                            l='Hierarchy', al='left', en=True, v=False, 
                                            ann="Hierarchy: if OFF during Load then the pose will load to the selected nodes IF they're in the pose file",
                                            cc=lambda x:self.__uiCache_addCheckbox('uicbPoseHierarchy'))
        self.uitfgPoseRootNode = cmds.textFieldButtonGrp('uitfgPoseRootNode', 
                                            ann='Hierarchy Root Node for the Pose', 
                                            text="", 
                                            bl='SetRootNode',
                                            bc=lambda * x: self.__uiCB_setPoseRootNode(),
                                            cw=[(1,180),(2,60)])

        cmds.setParent(self.poseUILayout)
        cmds.separator(h=10,style='in')
        self.uicbPoseRelative = cmds.checkBox('uicbPoseRelative', 
                                            l='RelativePose', al='left', en=True, v=False, 
                                            cc=lambda x:self.__uiCB_enableRelativeSwitches())

        cmds.separator(h=5,style='none')
        self.uiflPoseRelativeFrame=cmds.frameLayout('PoseRelativeFrame', label='Relative Offset Methods',cll=True,en=False)
        cmds.rowColumnLayout(nc=3,columnWidth=[(1, 120), (2, 80),(3,80)])
        
        self.uircbPoseRotMethod = cmds.radioCollection('relativeRotate')
        cmds.text(label='Rotate Method')
        cmds.radioButton('rotProjected', label='projected' )
        cmds.radioButton('rotAbsolute', label='absolute' )
        self.uircbPoseTranMethod = cmds.radioCollection('relativeTranslate')
        cmds.text(label='Translate Method')
        cmds.radioButton('tranProjected', label='projected' )
        cmds.radioButton('tranAbsolute', label='absolute' )
        cmds.setParent(self.poseUILayout)
        
        cmds.radioCollection(self.uircbPoseRotMethod, edit=True, select='rotProjected' )
        cmds.radioCollection(self.uircbPoseTranMethod, edit=True, select='tranProjected')
        
        self.uiflPosePointFrame=cmds.frameLayout('PosePointCloud', label='Pose Point Cloud',cll=True,cl=True,en=True)
        cmds.rowColumnLayout(nc=4,columnWidth=[(1,80), (2, 80),(3,80),(4,80)])
        cmds.button(label='Make PPC', bgc=self.buttonBgc, 
                     ann='Make a Pose Point Cloud - have to use hierarchy for this! - optional second selected node is a reference mesh', 
                     command=partial(self.__uiCall, 'PosePC_Make')) 
        cmds.button(label='Delete PPC', bgc=self.buttonBgc, 
                     ann='Delete the current Pose Point Cloud', 
                     command=partial(self.__uiCall, 'PosePC_Delete')) 
        cmds.button(label='Snap Pose', bgc=self.buttonBgc, 
                     ann='Snap the RIG to the PPC pose', 
                     command=partial(self.__uiCall, 'PosePC_Snap')) 
        cmds.button(label='Update PPC', bgc=self.buttonBgc, 
                     ann='Update the PPC to the RIGS current pose', 
                     command=partial(self.__uiCall, 'PosePC_Update')) 
        cmds.setParent(self.poseUILayout)        
        #====================
        #TabsEnd
        #====================
        cmds.tabLayout(self.tabs, edit=True, tabLabel=((self.AnimLayout, 'Animation_Toolkit'), 
                                                       (self.poseUILayout,'PoseManager'),
                                                       (self.FilterLayout, 'Hierarchy_Control')))
        #====================
        # Header
        #====================
        cmds.setParent(self.MainLayout)
        cmds.separator(h=10, style='none')
        cmds.iconTextButton(style='iconOnly', bgc=(0.7, 0, 0), image1='Rocket9_buttonStrap2.bmp', 
                             c=lambda * args:(r9Setup.red9ContactInfo()), h=22, w=200)
        
        #needed for 2009
        cmds.scrollLayout('uiglPoseScroll',e=True,h=330)
        
        #====================
        # Show and Dock
        #====================
        if self.dock:
            try:
                #Maya2011 QT docking
                allowedAreas = ['right', 'left']
                cmds.dockControl(self.dockCnt, area='right', label=self.label, content=animwindow, floating=False, allowedArea=allowedAreas, width=325)
            except:
                #Dock failed, opening standard Window
                cmds.showWindow(animwindow)
                cmds.window(self.win, edit=True, widthHeight=(355, 600))
        else:
            cmds.showWindow(animwindow)
            cmds.window(self.win, edit=True, widthHeight=(355, 600))
            
        #Set the initial Interface up
        self.__uiPresetsUpdate()
        self.__uiPresetReset() 
        self.__uiCache_loadUIElements()
          

    # UI Callbacks
    #------------------------------------------------------------------------------
    
    def __uiCB_manageSnapHierachy(self, *args):
        '''
        Disable all hierarchy filtering ui's when not running hierarchys
        '''
        val = False
        if cmds.checkBox(self.uicbSnapHierarchy, q=True, v=True):val = True
        cmds.intFieldGrp('uiifSnapIterations', e=True, en=val)
        cmds.checkBox(self.uicbSnapPreCopyAttrs, e=True, en=val)  
            
    def __uiCB_manageSnapTime(self, *args):
        '''
        Disable the frmStep and PreCopy when not running timeline
        '''
        val = False
        if cmds.checkBox(self.uicbSnapRange, q=True, v=True):val = True     
        cmds.checkBox(self.uicbSnapPreCopyKeys, e=True, en=val)        
        cmds.intFieldGrp('uiifgSnapStep', e=True, en=val)
        
    def __uiCB_manageTimeOffsetChecks(self, *args):
        '''
        Disable the frmStep and PreCopy when not running timeline
        '''
        if args[0] == 'Full':
            cmds.checkBox(self.uicbTimeOffsetHierarchy, e=True, v=False)
            cmds.checkBox(self.uicbTimeOffsetPlayback, e=True, en=True)
            cmds.checkBox(self.uicbTimeOffsetFlocking, e=True, en=False)
            cmds.checkBox(self.uicbTimeOffsetRandom, e=True, en=False)
        else:
            cmds.checkBox(self.uicbTimeOffsetPlayback, e=True, en=False)
            cmds.checkBox(self.uicbTimeOffsetScene, e=True, v=False)
            cmds.checkBox(self.uicbTimeOffsetFlocking, e=True, en=True)
            cmds.checkBox(self.uicbTimeOffsetRandom, e=True, en=True)
        
    def __uiCB_addToNodeTypes(self, nodeType, *args):
        '''
        Manage the RMB PopupMenu entries for easy adding nodeTypes to the UI
        '''
        nodeTypes = []
        if nodeType == 'clearAll':
            cmds.textFieldGrp('uitfgSpecificNodeTypes', e=True, text="")
            return
        current = cmds.textFieldGrp('uitfgSpecificNodeTypes', q=True, text=True)    
        if current:
            nodeTypes = current.split(',')
            if nodeType not in nodeTypes:
                nodeTypes.append(nodeType)
            else:
                nodeTypes.remove(nodeType)
        else:
            nodeTypes.append(nodeType)
        cmds.textFieldGrp('uitfgSpecificNodeTypes', e=True, text=','.join(nodeTypes))
 

    # Preset FilterSettings Object Management
    #------------------------------------------------------------------------------    
    
    def __uiPresetReset(self):
        '''
        Just reset the FilterUI widgets
        '''
        cmds.textFieldGrp('uitfgSpecificNodeTypes', e=True, text="")
        cmds.textFieldGrp('uitfgSpecificAttrs', e=True, text="")
        cmds.textFieldGrp('uitfgSpecificPattern', e=True, text="")
        cmds.textScrollList('uitslFilterPriority', e=True, ra=True)
        cmds.checkBox(self.uicbMetaRig, e=True, v=False)
        
    def __uiPresetsUpdate(self): 
        '''
        Fill the Preset TextField with files in the presets Dirs
        '''
        self.presets = os.listdir(self.presetDir)
        try:
            [self.presets.remove(hidden) for hidden in ['__red9config__','.svn','__config__'] \
                                            if hidden in self.presets]
        except:
            pass
        self.presets.sort()
        cmds.textScrollList(self.uitslPresets, edit=True, ra=True)
        cmds.textScrollList(self.uitslPresets, edit=True, append=self.presets)
        
    def __uiPresetStore(self, *args):
        '''
        Write a new Config Preset for the current UI state. Launches a ConfirmDialog
        '''
        result = cmds.promptDialog(
                title='Preset FileName',
                message='Enter Name:',
                button=['OK', 'Cancel'],
                defaultButton='OK',
                cancelButton='Cancel',
                dismissString='Cancel')
        if result == 'OK':
            self.__uiPresetFillFilter() #Fill the internal filterSettings object from the UI elements 
            self.filterSettings.printSettings()
            self.filterSettings.write('%s\%s.cfg' % (self.presetDir, cmds.promptDialog(query=True, text=True)))
            self.__uiPresetsUpdate() 
    
    def __uiPresetDelete(self, *args):
        '''
        Delete the selected preset file from disk
        '''
        preset = cmds.textScrollList(self.uitslPresets, q=True, si=True)[0]
        os.remove(os.path.join(self.presetDir, preset))
        self.__uiPresetsUpdate()
        
    def __uiPresetOpenDir(self,*args):
        import subprocess
        path=os.path.normpath(self.presetDir)
        subprocess.Popen('explorer "%s"' % path)
      
    def __uiPresetSelection(self, Read=True):
        '''
        Fill the UI from on config preset file select in the UI
        TODO: possibly anyway, we could add to the preset.cfg so that the initial posePath came from 
        the preset file. All we'd have to do would be to fill the self.ANIM_UI_OPTVARS['AnimationUI']['posePath']
        '''
        if Read:
            preset = cmds.textScrollList(self.uitslPresets, q=True, si=True)[0]
            self.filterSettings.read(os.path.join(self.presetDir, preset))
            #fill the cache up for the ini file
            self.ANIM_UI_OPTVARS['AnimationUI']['filterNode_preset']=preset
            log.info('preset loaded : %s' % preset)

        #JUST reset the UI elements
        self.__uiPresetReset()
        
        if self.filterSettings.nodeTypes:
            cmds.textFieldGrp('uitfgSpecificNodeTypes', e=True, 
                              text=r9General.forceToString(self.filterSettings.nodeTypes))
        if self.filterSettings.searchAttrs:
            cmds.textFieldGrp('uitfgSpecificAttrs', e=True, 
                                text=r9General.forceToString(self.filterSettings.searchAttrs))
        if self.filterSettings.searchPattern:
            cmds.textFieldGrp('uitfgSpecificPattern', e=True, 
                              text=r9General.forceToString(self.filterSettings.searchPattern))
        if self.filterSettings.filterPriority:
            cmds.textScrollList('uitslFilterPriority', e=True, 
                              append=self.filterSettings.filterPriority)

        cmds.checkBox(self.uicbMetaRig, e=True, v=self.filterSettings.metaRig) 
        cmds.checkBox(self.uicbIncRoots,e=True, v=self.filterSettings.incRoots)
        
        #need to run the callback on the PoseRootUI setup
        self.__uiCB_managePoseRootMethod()
        
        self.filterSettings.printSettings()
        self.__uiCache_storeUIElements()

    def __uiPresetFillFilter(self):
        '''
        Fill the internal filterSettings Object for the AnimationUI class calls
        '''
        self.filterSettings.resetFilters()
        self.filterSettings.transformClamp=True
        
        if cmds.textFieldGrp('uitfgSpecificNodeTypes', q=True, text=True): 
            self.filterSettings.nodeTypes = (cmds.textFieldGrp('uitfgSpecificNodeTypes', q=True, text=True)).split(',')
        if cmds.textFieldGrp('uitfgSpecificAttrs', q=True, text=True): 
            self.filterSettings.searchAttrs = (cmds.textFieldGrp('uitfgSpecificAttrs', q=True, text=True)).split(',')
        if cmds.textFieldGrp('uitfgSpecificPattern', q=True, text=True): 
            self.filterSettings.searchPattern = (cmds.textFieldGrp('uitfgSpecificPattern', q=True, text=True)).split(',')  
        if cmds.textScrollList('uitslFilterPriority', q=True, ai=True):
            self.filterSettings.filterPriority = cmds.textScrollList('uitslFilterPriority', q=True, ai=True)
       
        self.filterSettings.metaRig =cmds.checkBox(self.uicbMetaRig, q=True,v=True)
        self.filterSettings.incRoots=cmds.checkBox(self.uicbIncRoots,q=True,v=True)

        #If the above filters are blank, then the code switches to full hierarchy mode
        if not self.filterSettings.filterIsActive():  
            self.filterSettings.hierarchy = True      
        
    def __uiSetPriorities(self, mode='set',*args):
        if mode=='set' or mode=='clear':
            cmds.textScrollList('uitslFilterPriority', e=True, ra=True)
        if mode=='set' or mode=='append':
            node=[r9Core.nodeNameStrip(node) for node in cmds.ls(sl=True)]
            cmds.textScrollList('uitslFilterPriority', e=True, append=[r9Core.nodeNameStrip(node) for node in cmds.ls(sl=True)])
        
        if mode=='moveUp' or mode=='moveDown' or mode=='remove':
            selected=cmds.textScrollList('uitslFilterPriority', q=True, si=True)[0]
            data=cmds.textScrollList('uitslFilterPriority', q=True, ai=True)
            cmds.textScrollList('uitslFilterPriority', e=True, ra=True)
        if mode=='moveUp':
            data.insert(data.index(selected)-1, data.pop(data.index(selected)))
            cmds.textScrollList('uitslFilterPriority', e=True, append=data)
        if mode=='moveDown':
            data.insert(data.index(selected)+1, data.pop(data.index(selected)))
            cmds.textScrollList('uitslFilterPriority', e=True, append=data)
        if mode=='remove':
            data.remove(selected)
            cmds.textScrollList('uitslFilterPriority', e=True, append=data)
        self.__uiPresetFillFilter()
        self.__uiCache_storeUIElements()
    
    #------------------------------------------------------------------------------ 
    #PoseSaver Callbacks ----------------------------------------------------------
   
    def setPoseSelected(self,val=None,*args):
        '''
        set the PoseSelected cache for the UI calls
        '''
        if not self.poseGridMode=='thumb':
            self.poseSelected=cmds.textScrollList(self.uitslPoses, q=True,si=True)[0]
        else:
            self.poseSelected=val
        log.debug('PoseSelected : %s' % self.poseSelected)
        
    def getPoseSelected(self):
        if not self.poseSelected:
            raise StandardError('No Pose Selected in the UI')
        return self.poseSelected

    def buildPoseList(self):
        '''
        get a list of poses from the PoseRootDir, this then
        allows us to filter if needed
        '''
        self.poses=[]
        if not os.path.exists(self.posePath):
            log.debug('posePath is invalid')
            return self.poses
        files=os.listdir(self.posePath)
        files.sort()
        for f in files:
            if f.lower().endswith('.pose'):
                self.poses.append(f.split('.pose')[0])
        return self.poses
  
    def buildFilteredPoseList(self,searchFilter):
        filteredPoses=[]
        for pose in self.poses:
            if searchFilter and not searchFilter.upper() in pose.upper():
                continue
            filteredPoses.append(pose)
        return filteredPoses
    
    def __validatePoseFunc(self,func):
        '''
        called in some of the funcs so that they raise an error when called in 'Project' mode
        '''
        if self.posePathMode=='projectPoseMode':
            raise StandardError('%s : function disabled in Project Pose Mode!' % func)
        else:
            return True
         
    def __uiCB_selectPose(self,pose):
        if pose:
            if not self.poseGridMode=='thumb':
                cmds.textScrollList(self.uitslPoses, e=True,si=pose)
            else:
                self.__uiCB_iconGridSelection(pose)

    def __uiCB_switchPosePathMode(self,mode,*args):
        '''
        Switch the Pose mode from Project to Local. In project mode save is disabled.
        Both have different caches to store the 2 mapped root paths
        @param mode: 'local' or 'project', in project the poses are load only, save=disabled
        '''
        if mode=='local':
            self.posePath=self.posePathLocal
            self.posePathMode='localPoseMode'
            cmds.button('savePoseButton',e=True,en=True,bgc=r9Setup.red9ButtonBGC(1))
        elif mode=='project':
            self.posePath=self.posePathProject
            self.posePathMode='projectPoseMode'
            cmds.button('savePoseButton',e=True,en=False,bgc=r9Setup.red9ButtonBGC(2))      
        cmds.textFieldButtonGrp('uitfgPosePath',e=True,text=self.posePath)
        cmds.scrollLayout('uiglPoseScroll',e=True,sp='up')
        
        self.ANIM_UI_OPTVARS['AnimationUI']['posePathMode'] = self.posePathMode  
        self.__uiCB_fillPoses(rebuildFileList=True)

            
    def __uiCB_setPosePath(self,path=None,fileDialog=False):
        '''
        Manage the PosePath textfield and build the PosePath
        ''' 
        if fileDialog:
            try:
                if r9Setup.mayaVersion()>=2011:
                    self.posePath=cmds.fileDialog2(fileMode=3,dir=self.posePath)[0]
                else:
                    print 'Sorry Maya2009 and Maya2010 support is being dropped'
                    def setPosePath( fileName, fileType):
                        self.posePath=fileName
                    cmds.fileBrowserDialog( m=4, fc=setPosePath, ft='image', an='setPoseFolder', om='Import' )
            except:
                log.warning('No Folder Selected or Given')
        else:
            if not path:
                self.posePath=cmds.textFieldButtonGrp('uitfgPosePath',q=True,text=True)
            else:
                self.posePath=path
                
        #internal cache for the 2 path modes        
        if self.posePathMode=='localPoseMode':
            self.posePathLocal=self.posePath
        else:
            self.posePathProject=self.posePath
            
        cmds.textFieldButtonGrp('uitfgPosePath',e=True,text=self.posePath)                   
        self.__uiCB_fillPoses(rebuildFileList=True)
    
        #fill the cache up for the ini file
        self.ANIM_UI_OPTVARS['AnimationUI']['posePath']=self.posePath
        self.ANIM_UI_OPTVARS['AnimationUI']['posePathLocal']=self.posePathLocal
        self.ANIM_UI_OPTVARS['AnimationUI']['posePathProject']=self.posePathProject
        self.ANIM_UI_OPTVARS['AnimationUI']['posePathMode'] = self.posePathMode
        self.__uiCache_storeUIElements()
        
    def __uiCB_getPosePath(self):
        '''
        Return the full posePath for loading
        '''
        return os.path.join(cmds.textFieldButtonGrp('uitfgPosePath', query=True, text=True),\
                            '%s.pose' % self.getPoseSelected())
        
    def __uiCB_getIconPath(self):
        '''
        Return the full posePath for loading
        '''
        return os.path.join(cmds.textFieldButtonGrp('uitfgPosePath', query=True, text=True),\
                            '%s.bmp' % self.getPoseSelected())
    
      
                              
    def __uiCB_fillPoses(self, rebuildFileList=False, searchFilter=None ):
        '''
        Fill the Pose List/Grid from the given directory
        '''

        #Store the current mode to the Cache File
        self.ANIM_UI_OPTVARS['AnimationUI']['poseMode'] = self.poseGridMode 
        self.__uiCache_storeUIElements()
        searchFilter=cmds.textFieldGrp('tfPoseSearchFilter',q=True,text=True)
        
        if rebuildFileList:
            self.buildPoseList()
            log.debug('Rebuilt Pose internal Lists')        
        log.debug( 'searchFilter  : %s : rebuildFileList : %s' %(searchFilter, rebuildFileList))

        
        #TextScroll Layout
        #================================ 
        if not self.poseGridMode=='thumb':
            popupBind=self.uitslPoses
            cmds.textScrollList(self.uitslPoses, edit=True, vis=True)
            cmds.scrollLayout(self.uiglPoseScroll, edit=True, vis=False)
            cmds.textScrollList(self.uitslPoses, edit=True, ra=True)
            
            if searchFilter:
                cmds.scrollLayout('uiglPoseScroll',e=True,sp='up')
                
            for pose in self.buildFilteredPoseList(searchFilter):
                cmds.textScrollList(self.uitslPoses, edit=True, 
                                        append=pose,
                                        sc=partial(self.setPoseSelected))
        #Grid Layout
        #================================ 
        else:
            popupBind=self.uiglPoseScroll
            cmds.textScrollList(self.uitslPoses, edit=True, vis=False)
            cmds.scrollLayout(self.uiglPoseScroll, edit=True, vis=True)
            self.__uiCB_gridResize()
            
                
            #Clear the Grid if it's already filled
            try:
                [cmds.deleteUI(button) for button in cmds.gridLayout(self.uiglPoses,q=True,ca=True)]
            except:
                pass
            for pose in self.buildFilteredPoseList(searchFilter):
                try:
                    #:NOTE we prefix the buttons to get over the issue of non-numeric 
                    #first characters which are stripped my Maya!
                    cmds.iconTextCheckBox( '_%s' % pose, style='iconAndTextVertical', \
                                            image=os.path.join(self.posePath,'%s.bmp' % pose), \
                                            label=pose,\
                                            bgc=self.poseButtonBGC,\
                                            parent=self.uiglPoses,\
                                            onc=partial(self.__uiCB_iconGridSelection, pose),\
                                            ofc="import maya.cmds as cmds;cmds.iconTextCheckBox('_%s', e=True, v=True)" % pose) #we DONT allow you to deselect
                except StandardError,error:
                    raise StandardError(error)
             
            if searchFilter:
                #with search scroll the list to the top as results may seem blank otherwise
                cmds.scrollLayout('uiglPoseScroll',e=True,sp='up')   
                    
        #Finally Bind the Popup-menu                
        self.__uiCB_PosePopup(popupBind)
  
  
    def __uiCB_gridResize(self):
        if r9Setup.mayaVersion()>=2010:
            cells=int(cmds.scrollLayout('uiglPoseScroll',q=True,w=True)/cmds.gridLayout('uiglPoses',q=True,cw=True))
            cmds.gridLayout('uiglPoses',e=True,nc=cells)
        else:
            log.debug('this call FAILS in 2009???')
        
    def __uiCB_PosePopup(self,parentUI):
        '''
        RMB popup menu for the Pose functions
        '''
        try:
            cmds.deleteUI(self.posePopup)
        except:
            pass 
        enableState=True  
        if self.posePathMode=='projectPoseMode':
            enableState=False

        self.posePopup = cmds.popupMenu(parent=parentUI)                    
        cmds.menuItem(label='Delete Pose', en=enableState, command=partial(self.__uiCB_deletePose))
        cmds.menuItem(label='Rename Pose', en=enableState, command=partial(self.__uiCB_renamePose))
        cmds.menuItem(label='Update Pose', en=enableState, command=partial(self.__uiCB_updatePose))
        cmds.menuItem(label='Select IntenalPose Objects', command=partial(self.__uiCB_selectPoseObjects))
        cmds.menuItem(divider=True)
        cmds.menuItem(label='Debug: Open Pose File', command=partial(self.__uiCB_openPoseFile))
        cmds.menuItem(label='Debug: Open Pose Directory', command=partial(self.__uiCB_openPoseDir))
        cmds.menuItem(label='Debug: Pose Compare with current', command=partial(self.__uiCB_poseCompare))
        cmds.menuItem(divider=True)
        cmds.menuItem(label='Copy Pose >> Project Poses', en=enableState,command=partial(self.__uiCB_copyPoseToProject))     
        cmds.menuItem(divider=True)
        cmds.menuItem(label='Switch Pose Mode - Thumb/Text', command=partial(self.__uiCB_switchPoseMode))

        if self.poseGridMode=='thumb':
            cmds.menuItem(divider=True)
            cmds.menuItem(label='Update Thumb', command=partial(self.__uiCB_updateThumb))
            cmds.menuItem(label='Grid Size: Small', command=partial(self.__uiCB_setPoseGrid,'small'))
            cmds.menuItem(label='Grid Size: Medium', command=partial(self.__uiCB_setPoseGrid,'medium'))
            cmds.menuItem(label='Grid Size: Large', command=partial(self.__uiCB_setPoseGrid,'large'))

    def __uiCB_setPoseGrid(self,size,*args):
        '''
        Set size of the Thumnails used in the PoseGrid Layout
        '''
        if size=='small':
            cmds.gridLayout(self.uiglPoses,e=True,cwh=(75,80),nc=4)
        if size=='medium':
            cmds.gridLayout(self.uiglPoses,e=True,cwh=(100,90),nc=3)
        if size=='large':
            cmds.gridLayout(self.uiglPoses,e=True,cwh=(150,120),nc=2)     
        self.__uiCB_fillPoses()
        self.__uiCB_selectPose(self.poseSelected) 
        
    def __uiCB_iconGridSelection(self,current=None,*args):
        '''
        Unselect all other iconTextCheckboxes than the currently selected
        without this you would be able to multi-select the thumbs
        
        NOTE: because we prefix the buttons to get over the issue of non-numeric 
        first characters we now need to strip the first character back off
        '''
        for button in cmds.gridLayout(self.uiglPoses,q=True,ca=True):
            if current and not button[1:]==current:
                cmds.iconTextCheckBox(button,e=True,v=False,bgc=self.poseButtonBGC)
            else:
                cmds.iconTextCheckBox(button,e=True,v=True,bgc=self.poseButtonHighLight)
        self.setPoseSelected(current) 
    
    def __uiCB_switchPoseMode(self,*args):
        '''
        Toggle PoseField mode between Grid mode and TextScroll
        '''
        if self.poseGridMode=='thumb':
            self.poseGridMode='text'
        else:
            self.poseGridMode='thumb'
        self.__uiCB_fillPoses()
        self.__uiCB_selectPose(self.poseSelected) 
          
    def __uiCB_savePosePath(self,existingText=None):
        '''
        Build the path for the pose to be saved too
        '''
        result = cmds.promptDialog(
                title='Pose',
                message='Enter Name:',
                button=['OK', 'Cancel'],
                text=existingText,
                defaultButton='OK',
                cancelButton='Cancel',
                dismissString='Cancel')
        if result == 'OK':
            name=cmds.promptDialog(query=True, text=True)
            try:
                if r9Core.validateString(name):
                    return '%s\%s.pose' %  (cmds.textFieldButtonGrp('uitfgPosePath', query=True, text=True), name)
            except ValueError,error:
                raise ValueError(error)
                
    def __uiCB_deletePose(self,*args):
        self.__validatePoseFunc('DeletePose')
        result = cmds.confirmDialog(
                title='Confirm Pose Delete',
                button=['Yes', 'Cancel'],
                message='confirm deletion of pose file: "%s"' % self.poseSelected,
                defaultButton='Yes',
                cancelButton='Cancel',
                dismissString='Cancel')
        if result == 'Yes':
            try:
                os.remove(self.__uiCB_getPosePath())
            except:
                log.info('Failed to Delete PoseFile')
            try:
                os.remove(self.__uiCB_getIconPath())
            except:
                log.info('Failed to Delete PoseIcon')
            self.__uiCB_fillPoses(rebuildFileList=True)
        
    def __uiCB_renamePose(self,*args):
        try:
            newName=self.__uiCB_savePosePath(self.getPoseSelected())
        except ValueError,error:
            raise ValueError(error)
        try:
            os.rename(self.__uiCB_getPosePath(), newName)
            os.rename(self.__uiCB_getIconPath(), '%s.bmp' % newName.split('.pose')[0])
        except:
            log.info('Failed to Rename Pose')
        self.__uiCB_fillPoses(rebuildFileList=True)  
        pose=os.path.basename(newName.split('.pose')[0])
        self.__uiCB_selectPose(pose)   
        
    def __uiCB_openPoseFile(self,*args):
        import subprocess
        path=os.path.normpath(self.__uiCB_getPosePath())
        subprocess.Popen('notepad "%s"' % path)
        
    def __uiCB_openPoseDir(self,*args):
        import subprocess
        path=os.path.normpath(cmds.textFieldButtonGrp('uitfgPosePath', query=True, text=True))
        subprocess.Popen('explorer "%s"' % path)
     
    def __uiCB_updatePose(self,*args):
        self.__validatePoseFunc('UpdatePose')
        result = cmds.confirmDialog(
                title='PoseUpdate',
                message=('<< Replace & Update Pose file >>\n\n%s' % self.poseSelected),
                button=['OK', 'Cancel'],
                defaultButton='OK',
                cancelButton='Cancel',
                dismissString='Cancel')
        if result == 'OK':
            try:
                os.remove(self.__uiCB_getIconPath())
            except:
                log.debug('unable to delete the Pose Icon file')
            self.__PoseSave(self.__uiCB_getPosePath())
            self.__uiCB_selectPose(self.poseSelected)   
    
    def __uiCB_updateThumb(self,*args):
        sel=cmds.ls(sl=True,l=True)
        cmds.select(cl=True)
        thumbPath=self.__uiCB_getIconPath()
        if os.path.exists(thumbPath):
            try:
                os.remove(thumbPath)
            except:
                log.error('Unable to delete the Pose Icon file')
        r9General.thumbNailScreen(thumbPath,128,128)
        if sel:
            cmds.select(sel)
        self.__uiCB_fillPoses()
        self.__uiCB_selectPose(self.poseSelected)   

    def __uiCB_poseCompare(self,*args):

        mPoseA=r9Pose.PoseData()
        mPoseA.metaPose=True
        mPoseA.buildInternalPoseData(self.__uiCB_getPoseInputNodes())
        compare=r9Pose.PoseCompare(mPoseA,self.__uiCB_getPosePath(),compareDict='skeletonDict')
        
        if not compare.compare():
            info='Selected Pose is different to the rigs current pose\nsee script editor for debug details'
        else:
            info='Poses are the same'
        cmds.confirmDialog( title='Pose Compare Results',
                            button=['Close'],
                            message=info,
                            defaultButton='Close',
                            cancelButton='Close',
                            dismissString='Close')
        

    def __uiCB_selectPoseObjects(self,*args): 
        '''
        Select matching internal nodes
        '''
        rootNode=cmds.textFieldButtonGrp('uitfgPoseRootNode',q=True,text=True)
        if rootNode and cmds.objExists(rootNode):  
            self.__uiPresetFillFilter() #fill the filterSettings Object
            pose=r9Pose.PoseData(self.filterSettings)
            pose.readPose(self.__uiCB_getPosePath())
            nodes=pose.matchInternalPoseObjects(rootNode)
            if nodes:
                cmds.select(cl=True)
                [cmds.select(node,add=True) for node in nodes]
        else:
            raise StandardError('RootNode not Set for Hierarchy Processing')
           
    def __uiCB_setPoseRootNode(self):
        '''
        This changes the mode for the Button that fills in rootPath in the poseUI
        Either fills with the given node, or fill it with the connected MetaRig
        '''
        rootNode=cmds.ls(sl=True,l=True)
        
        def fillTextField(text):
            #bound to a function so it can be passed onto the MetaNoode selector UI
            cmds.textFieldButtonGrp('uitfgPoseRootNode',e=True,text=text)
            
        if self.poseRootMode=='RootNode':
            if not rootNode:
                raise StandardError('Warning nothing selected')
            fillTextField(rootNode[0])        
        elif self.poseRootMode=='MetaRoot':
            if rootNode:
                #metaRig=r9Meta.getConnectedMetaNodes(rootNode[0])
                metaRig=r9Meta.getConnectedMetaSystemRoot(rootNode[0])
                if not metaRig:
                    raise StandardError("Warning selected node isn't connected to a MetaRig node")
                fillTextField(metaRig.mNode)
            else:
                metaRigs=r9Meta.getMetaNodes(dataType='mClass')
                if metaRigs:
                    r9Meta.MClassNodeUI(closeOnSelect=True,\
                                        funcOnSelection=fillTextField,\
                                        mInstances=['MetaRig'],\
                                        allowMulti=False)._showUI()
                else:
                    
                    raise StandardError("Warning: No MetaRigs found in the Scene")
        #fill the cache up for the ini file
        self.ANIM_UI_OPTVARS['AnimationUI']['poseRoot']=cmds.textFieldButtonGrp('uitfgPoseRootNode',q=True,text=True)
        self.__uiCache_storeUIElements()
        
    def __uiCB_managePoseRootMethod(self,*args):
        '''
        Manage the PoseRootNode method, either switch to standard rootNode or MetaNode
        '''
        if cmds.checkBox('uicbMetaRig',q=True,v=True):
            self.poseRootMode='MetaRoot'
            cmds.textFieldButtonGrp('uitfgPoseRootNode',e=True,bl='MetaRoot')
        else: 
            self.poseRootMode='RootNode'  
            cmds.textFieldButtonGrp('uitfgPoseRootNode',e=True,bl='SetRoot')
        #self.__uiCache_addCheckbox('uicbMetaRig')
        self.__uiCache_storeUIElements()
        
    def __uiCB_getPoseInputNodes(self):
        '''
        Node passed into the PoseCall itself
        '''
        PoseNodes=[]
        if cmds.checkBox('uicbPoseHierarchy',q=True,v=True):
            #hierarchy processing so we MUST pass a root in
            PoseNodes=cmds.textFieldButtonGrp('uitfgPoseRootNode',q=True,text=True)
            if not PoseNodes or not cmds.objExists(PoseNodes):
                raise StandardError('RootNode not Set for Hierarchy Processing')
        else:
            PoseNodes=cmds.ls(sl=True,l=True)
        if not PoseNodes:
                raise StandardError('No Nodes Set or selected for Pose')
        return PoseNodes
    
    def __uiCB_enableRelativeSwitches(self):
        self.__uiCache_addCheckbox('uicbPoseRelative')
        cmds.frameLayout(self.uiflPoseRelativeFrame, e=True,en=cmds.checkBox(self.uicbPoseRelative,q=True,v=True))
    
    def __uiCB_copyPoseToProject(self,*args):
        '''
        Copy local pose to the Project Pose Folder
        '''
        import shutil
        if not os.path.exists(self.posePathProject):
            raise StandardError('Project Pose Path is inValid')
        log.info('Copying Local Pose: %s >> %s' % (self.poseSelected,self.posePathProject))
        try:
            shutil.copy2(self.__uiCB_getPosePath(),self.posePathProject)
            shutil.copy2(self.__uiCB_getIconPath(),self.posePathProject)
        except:
            raise StandardError('Unable to copy pose : %s > to Project dirctory' % self.poseSelected)
        
    #------------------------------------------------------------------------------
    #UI Elements ConfigStore Callbacks --------------------------------------------  
        
    def __uiCache_storeUIElements(self):
        '''
        Store some of the main components of the UI out to an ini file
        '''
        if not self.uiBoot:
            log.debug('UI configFile being written')
            ConfigObj = configobj.ConfigObj(indent_type='\t')
            self.__uiPresetFillFilter() #fill the internal filterSettings obj
            
            ConfigObj['filterNode_settings']=self.filterSettings.__dict__
            ConfigObj['AnimationUI']=self.ANIM_UI_OPTVARS['AnimationUI']
            ConfigObj.filename = self.ui_optVarConfig
            ConfigObj.write()
        
    
    def __uiCache_loadUIElements(self):
        '''
        Restore the main UI elements from the ini file
        '''
        self.uiBoot=True
        try: 
            log.debug('Loading UI Elements from the config file')
            def __uiCache_LoadCheckboxes():
                if self.ANIM_UI_OPTVARS['AnimationUI'].has_key('checkboxes'):
                    for cb,status in self.ANIM_UI_OPTVARS['AnimationUI']['checkboxes'].items():
                        cmds.checkBox(cb,e=True,v=r9Core.decodeString(status))
                
            AnimationUI=self.ANIM_UI_OPTVARS['AnimationUI']

            if AnimationUI.has_key('filterNode_preset') and AnimationUI['filterNode_preset']:
                cmds.textScrollList(self.uitslPresets, e=True, si=AnimationUI['filterNode_preset'])
                self.__uiPresetSelection(Read=True)   ###not sure on this yet????
            if AnimationUI.has_key('poseMode') and AnimationUI['poseMode']:
                self.poseGridMode=AnimationUI['poseMode']
                
            if AnimationUI.has_key('posePathMode') and AnimationUI['posePathMode']:
                self.posePathMode=AnimationUI['posePathMode']
            
            if AnimationUI.has_key('posePathLocal') and AnimationUI['posePathLocal']:
                self.posePathLocal=AnimationUI['posePathLocal']
            if AnimationUI.has_key('posePathProject') and AnimationUI['posePathProject']:
                self.posePathProject=AnimationUI['posePathProject']                
        
            #if AnimationUI.has_key('posePath') and AnimationUI['posePath']:
            #    self.__uiCB_setPosePath(path=AnimationUI['posePath'])
            if AnimationUI.has_key('poseRoot') and AnimationUI['poseRoot']:
                if cmds.objExists(AnimationUI['poseRoot']):
                    cmds.textFieldButtonGrp('uitfgPoseRootNode',e=True,text=AnimationUI['poseRoot'])
                    
            __uiCache_LoadCheckboxes()
            
            #callbacks
            cmds.radioCollection(self.uircbPosePathMethod, edit=True, select=self.posePathMode)
            self.__uiCB_enableRelativeSwitches()              # relativePose switch enables
            self.__uiCB_managePoseRootMethod()                # metaRig or SetRootNode for Pose Root
            self.__uiCB_switchPosePathMode(self.posePathMode) # pose Mode - 'local' or 'project'
            
            
        except StandardError,err:
            log.debug('failed to complete UIConfig load')
            log.warning(err)
        finally:
            self.uiBoot=False
             
             
    def __uiCache_readUIElements(self):
        '''
        read the config ini file for the initial state of the ui
        '''
        try:
            if os.path.exists(self.ui_optVarConfig):
                self.filterSettings.read(self.ui_optVarConfig) #use the generic reader for this
                self.ANIM_UI_OPTVARS['AnimationUI']=configobj.ConfigObj(self.ui_optVarConfig)['AnimationUI']
            else:
                self.ANIM_UI_OPTVARS['AnimationUI']={}
        except:
            pass
        
    def __uiCache_addCheckbox(self,checkbox):
        '''
        Now shifted into a sub dic for easier processing
        '''
        if not self.ANIM_UI_OPTVARS['AnimationUI'].has_key('checkboxes'):
            self.ANIM_UI_OPTVARS['AnimationUI']['checkboxes']={}
        self.ANIM_UI_OPTVARS['AnimationUI']['checkboxes'][checkbox]=cmds.checkBox(checkbox,q=True,v=True)
        self.__uiCache_storeUIElements()
        
        
    # MAIN UI FUNCTION CALLS
    #------------------------------------------------------------------------------
    
    def __CopyAttrs(self):
        '''
        Internal UI call for CopyAttrs
        '''
        self.kws['toMany'] = cmds.checkBox(self.uicbCAttrToMany, q=True, v=True)
        if cmds.checkBox(self.uicbCAttrChnAttrs, q=True, v=True):
            self.kws['attributes'] = getChannelBoxSelection()   
        if cmds.checkBox(self.uicbCAttrHierarchy, q=True, v=True): 
            if self.kws['toMany']:
                AnimFunctions().copyAttrs_ToMultiHierarchy(cmds.ls(sl=True, l=True), 
                                                          filterSettings=self.filterSettings, 
                                                          **self.kws)
            else:
                AnimFunctions().copyAttributes(nodes=None, filterSettings=self.filterSettings, **self.kws)
        else:
            print self.kws
            AnimFunctions().copyAttributes(nodes=None, **self.kws) 
            
    def __CopyKeys(self):
        '''
        Internal UI call for CopyKeys call
        '''
        self.kws['toMany'] = cmds.checkBox(self.uicbCKeyToMany, q=True, v=True)
        if cmds.checkBox(self.uicbCKeyRange, q=True, v=True):
            self.kws['time'] = timeLineRangeGet()
        if cmds.checkBox(self.uicbCKeyChnAttrs, q=True, v=True):
            self.kws['attributes'] = getChannelBoxSelection()   
        if cmds.checkBox(self.uicbCKeyHierarchy, q=True, v=True):  
            if self.kws['toMany']:
                AnimFunctions().copyKeys_ToMultiHierarchy(cmds.ls(sl=True, l=True), 
                                                          filterSettings=self.filterSettings, 
                                                          **self.kws)
            else:
                AnimFunctions().copyKeys(nodes=None, filterSettings=self.filterSettings, **self.kws)
        else:
            AnimFunctions().copyKeys(nodes=None, **self.kws)
    
    def __Snap(self):
        '''
        Internal UI call for Snap Transforms
        '''
        self.kws['preCopyKeys'] = False
        self.kws['preCopyAttrs'] = False
        self.kws['iterations'] = cmds.intFieldGrp('uiifSnapIterations', q=True, v=True)[0]
        self.kws['step'] = cmds.intFieldGrp('uiifgSnapStep', q=True, v=True)[0]
       
        if cmds.checkBox(self.uicbSnapRange, q=True, v=True):
            self.kws['time'] = timeLineRangeGet()
        if cmds.checkBox(self.uicbSnapPreCopyKeys, q=True, v=True):
            self.kws['preCopyKeys'] = True  
        if cmds.checkBox(self.uicbSnapPreCopyAttrs, q=True, v=True):
            self.kws['preCopyAttrs'] = True  
        if cmds.checkBox(self.uicbSnapHierarchy, q=True, v=True):
            AnimFunctions().snapTransform(nodes=None, filterSettings=self.filterSettings, **self.kws)     
        else:
            AnimFunctions().snapTransform(nodes=None, **self.kws)   
    
    def __Stabilize(self):
        '''
        Internal UI call for Stabilize
        '''
        time = ()
        step = cmds.intFieldGrp('uiifgStabStep', q=True, v=True)[0]
        if cmds.checkBox(self.uicbStabRange, q=True, v=True):
            time = timeLineRangeGet()
        AnimFunctions.stabilizer(cmds.ls(sl=True, l=True), time, step)  
                                      
    def __TimeOffset(self):
        '''
        Internal UI call for TimeOffset
        '''
        offset = cmds.floatFieldGrp('uiffgTimeOffset', q=True, v=True)[0]
        flocking = cmds.checkBox(self.uicbTimeOffsetFlocking, q=True, v=True)
        random = cmds.checkBox(self.uicbTimeOffsetRandom, q=True, v=True)
        if cmds.checkBox(self.uicbTimeOffsetScene, q=True, v=True):
            r9Core.TimeOffset.fullScene(offset, cmds.checkBox(self.uicbTimeOffsetPlayback, q=True, v=True))     
        else:
            if cmds.checkBox(self.uicbTimeOffsetHierarchy, q=True, v=True):
                r9Core.TimeOffset.fromSelected(offset, 
                                               filterSettings=self.filterSettings, 
                                               flocking=flocking, randomize=random)  
            else:
                r9Core.TimeOffset.fromSelected(offset, flocking=flocking, randomize=random)  
   
    def __Hierarchy(self):
        '''
        Internal UI call for Test Hierarchy
        '''
        if cmds.ls(sl=True):
            Filter = r9Core.FilterNode(cmds.ls(sl=True,l=True), filterSettings=self.filterSettings)
            try:
                self.filterSettings.printSettings() 
                cmds.select(Filter.ProcessFilter())
                log.info('=============  Filter Test Results  ==============')     
                print('\n'.join([node for node in Filter.intersectionData]))
                log.info('FilterTest : Object Count Returned : %s' % len(Filter.intersectionData))
            except:                             
                raise StandardError('Filter Returned Nothing')
        else:
            raise StandardError('No Root Node selected for Filter Testing')             
    
    def __PoseSave(self,path=None):
        '''
        Internal UI call for PoseLibrary
        '''
        if not path:
            try:
                path=self.__uiCB_savePosePath()
            except ValueError,error:
                raise ValueError(error)

        poseHierarchy=cmds.checkBox('uicbPoseHierarchy',q=True,v=True)
        r9Pose.PoseData(self.filterSettings).PoseSave(self.__uiCB_getPoseInputNodes(), 
                                                      path,
                                                      useFilter=poseHierarchy)
        log.info('Pose Stored to : %s' % path)
        self.__uiCB_fillPoses(rebuildFileList=True)
            
    def __PoseLoad(self):  
        poseHierarchy=cmds.checkBox('uicbPoseHierarchy',q=True,v=True)
        poseRelative=cmds.checkBox('uicbPoseRelative',q=True,v=True)
        rotRelMethod=cmds.radioCollection( self.uircbPoseRotMethod,q=True,select=True)
        tranRelMethod=cmds.radioCollection( self.uircbPoseTranMethod,q=True,select=True)
        relativeRots='projected'
        relativeTrans='projected'
        if not rotRelMethod=='rotProjected':
            relativeRots='absolute'
        if not tranRelMethod=='tranProjected':
            relativeTrans='absolute'
            
        path=self.__uiCB_getPosePath()
        log.info('PosePath : %s' % path)
        r9Pose.PoseData(self.filterSettings).PoseLoad(self.__uiCB_getPoseInputNodes(), 
                                                      path,
                                                      useFilter=poseHierarchy,
                                                      relativePose=poseRelative,
                                                      relativeRots=relativeRots,
                                                      relativeTrans=relativeTrans) 
    def __PosePointCloud(self,func):
        '''
        Note: this is dependant on EITHER a wire from the root of the pose to a GEO
        under the attr 'renderMeshes' OR the second selected object is the reference Mesh
        Without either of these you'll just get a locator as the PPC root
        '''
        objs=cmds.ls(sl=True)
 
        ref=objs[0]
        mesh=None
        mRef=r9Meta.MetaClass(self.__uiCB_getPoseInputNodes())
        if mRef.hasAttr('renderMeshes'):
            mesh=mRef.renderMeshes[0]
        elif len(objs)==2:
            if cmds.nodeType(cmds.listRelatives(objs[1])[0])=='mesh':
                mesh=objs[1]
        if func=='make':
            if not objs:
                raise StandardError('you need to select a reference object to use as pivot for the PPCloud')
            if cmds.ls('*posePointCloud',r=True):
                raise StandardError('PosePointCloud already exists in scsne')
            if not mesh:
                cmds.modelEditor(cmds.getPanel(wf=True), e=True, locators=True)
            self.ppc=r9Pose.PosePointCloud(ref,self.__uiCB_getPoseInputNodes(),
                                           self.filterSettings,
                                           mesh=mesh)
        elif func=='delete':
            self.ppc.delete()
        elif func=='snap':
            self.ppc.applyPosePointCloud()
        elif func=='update':
            self.ppc.snapPosePointsToPose()
         
    def __MirrorPoseAnim(self,func):
        '''
        Internal UI call for Mirror Animation / Pose
        '''
        mirror=MirrorHierarchy(nodes=cmds.ls(sl=True, l=True), filterSettings=self.filterSettings)
        mirrorMode='Anim'
        if func=='MirrorPose':
            mirrorMode='Pose' 
        if not cmds.checkBox('uicbMirrorHierarchy',q=True,v=True):
            mirror.mirrorData(cmds.ls(sl=True, l=True),mode=mirrorMode)   
        else:
            mirror.mirrorData(mode=mirrorMode)        

               
    # MAIN CALL
    #------------------------------------------------------------------------------                                                                                         
    def __uiCall(self, func, *args):
        '''
        MAIN ANIMATION UI CALL
        '''
        #issue : up to v2011 Maya puts each action into the UndoQueue separately
        #when called by lambda or partial - Fix is to open an UndoChunk to catch
        #everything in one block
        self.kws = {}

        #If below 2011 then we need to store the undo in a chunk
        if r9Setup.mayaVersion() < 2011:
            cmds.undoInfo(openChunk=True)
            
        # Main Hierarchy Filters ============= 
        self.__uiPresetFillFilter() #fill the filterSettings Object
        #self.filterSettings.transformClamp = True
         
        try:
            if func == 'CopyAttrs':
                self.__CopyAttrs()  
            elif func == 'CopyKeys':
                self.__CopyKeys()                        
            elif func == 'Snap':
                self.__Snap()   
            elif func == 'Stabilize':
                self.__Stabilize()
            elif func == 'TimeOffset':
                self.__TimeOffset()
            elif func == 'HierarchyTest':
                self.__Hierarchy()
            elif func == 'PoseSave': 
                self.__PoseSave()    
            elif func == 'PoseLoad':
                self.__PoseLoad()
            elif func == 'PosePC_Make':
                self.__PosePointCloud('make')
            elif func == 'PosePC_Delete':
                self.__PosePointCloud('delete')
            elif func == 'PosePC_Snap':
                self.__PosePointCloud('snap')
            elif func == 'PosePC_Update':
                self.__PosePointCloud('update')
            elif func =='MirrorAnim':
                self.__MirrorPoseAnim(func)
            elif func =='MirrorPose':
                self.__MirrorPoseAnim(func)

        except StandardError, error:
            raise StandardError(error)
        
        #close chunk
        if mel.eval('getApplicationVersionAsFloat') < 2011:
            cmds.undoInfo(closeChunk=True)     
            
        self.__uiCache_storeUIElements()
            
       
    
#===========================================================================
# Main AnimFunction code class
#===========================================================================
       
class AnimFunctions(object):
    
    def __init__(self):
        pass
              
            
    #===========================================================================
    # Copy Keys
    #===========================================================================

    def copyKeys_ToMultiHierarchy(self, nodes=None, time=(), pasteKey='replace', 
                 attributes=None, filterSettings=None,**kws):
        '''
        This isn't the best way by far to do this, but as a quick wrapper
        it works well enough. Really we need to process the nodes more intelligently
        prior to sending data to the copyKeys calls
        '''
        for node in nodes[1:]:
            self.copyKeys(nodes=[nodes[0], node], 
                          time=time, 
                          attributes=attributes, 
                          pasteKey=pasteKey,
                          filterSettings=filterSettings,
                          toMany=False)
               

    def copyKeys(self, nodes=None, time=(), pasteKey='replace', 
                 attributes=None, filterSettings=None, toMany=False, **kws):
        '''
        Copy Keys is a Hi-Level wrapper function to copy animation data between
        filtered nodes, either in hierarchies or just selected pairs. 
                
        @param nodes: List of Maya nodes to process. This combines the filterSettings
            object and the MatchedNodeInputs.processMatchedPairs() call, 
            making it capable of powerful hierarchy filtering and node matching methods.
        
        @param filterSettings: Passed into the decorator and onto the FilterNode code
            to setup the hierarchy filters - See docs on the FilterNode_Settings class
        
        @param pasteKey: Uses the standard pasteKey option methods - merge,replace,
            insert etc. This is fed to the internal pasteKey method. Default=replace
       
        @param time: Copy over a given timerange - time=(start,end). Default is
            to use no timeRange. If time is passed in via the timeLineRange() function
            then it will consider the current timeLine PlaybackRange, OR if you have a
            highlighted range of time selected(in red) it'll use this instead.
       
        @param attributes: Only copy the given attributes[]
        
        Generic filters passed into r9Core.MatchedNodeInputs class:
        -----------------------------------------------------------------
        @setting.nodeTypes: list[] - search for child nodes of type (wraps cmds.listRelatives types=)
        @setting.searchAttrs: list[] - search for child nodes with Attrs of name 
        @setting.searchPattern: list[] - search for nodes with a given nodeName searchPattern
        @setting.hierarchy: bool = lsHierarchy code to return all children from the given nodes      
        @setting.metaRig: bool = use the MetaRig wires to build the initial Object list up
        
        NOTE: with all the search and hierarchy settings OFF the code performs
        a Dumb copy, no matching and no Hierarchy filtering, copies using 
        selected pairs obj[0]>obj[1], obj[2]>obj[3] etc 
        -----------------------------------------------------------------
        '''

        log.debug('CopyKey params : nodes=%s : time=%s : pasteKey=%s : attributes=%s : filterSettings=%s' \
                   % (nodes, time, pasteKey, attributes, filterSettings))

        #Build up the node pairs to process
        nodeList = r9Core.processMatchedNodes(nodes, filterSettings, toMany).MatchedPairs
        
        if nodeList:       
            with r9General.HIKContext([d for _,d in nodeList]):
                for src, dest in nodeList: 
                    try:
                        if attributes:
                            #copy only specific attributes
                            for attr in attributes:
                                if cmds.copyKey(src, attribute=attr, hierarchy=False, time=time):
                                    cmds.pasteKey(dest, attribute=attr, option=pasteKey)
                        else:
                            if cmds.copyKey(src, hierarchy=False, time=time):
                                cmds.pasteKey(dest, option=pasteKey)
                    except:
                        pass
        else:
            raise StandardError('Nothing found by the Hierarchy Code to process')
        return True 
    
    
    #===========================================================================
    # Copy Attributes
    #===========================================================================

    def copyAttrs_ToMultiHierarchy(self, nodes=None, attributes=None, skipAttrs=None, \
                       filterSettings=None,**kws):
        '''
        This isn't the best way by far to do this, but as a quick wrapper
        it works well enough. Really we need to process the nodes more intelligently
        prior to sending data to the copyKeys calls
        '''
        for node in nodes[1:]:
            self.copyAttributes(nodes=[nodes[0], node], 
                          attributes=attributes, 
                          filterSettings=filterSettings,
                          skipAttrs=skipAttrs,
                          toMany=False)
            

    def copyAttributes(self, nodes=None, attributes=None, skipAttrs=None, 
                       filterSettings=None, toMany=False, **kws):
        '''
        Copy Attributes is a Hi-Level wrapper function to copy Attribute data between
        filtered nodes, either in hierarchies or just selected pairs. 
                
        @param nodes: List of Maya nodes to process. This combines the filterSettings
            object and the MatchedNodeInputs.processMatchedPairs() call, 
            making it capable of powerful hierarchy filtering and node matching methods.
        
        @param filterSettings: Passed into the decorator and onto the FilterNode code
            to setup the hierarchy filters - See docs on the FilterNode_Settings class

        @param attributes: Only copy the given attributes[]
        @param skipAttrs: Copy all Settable Attributes OTHER than the given, not
            used if an attributes list is passed
        
        Generic filters passed into r9Core.MatchedNodeInputs class:
        -----------------------------------------------------------------
        @setting.nodeTypes: list[] - search for child nodes of type (wraps cmds.listRelatives types=)
        @setting.searchAttrs: list[] - search for child nodes with Attrs of name 
        @setting.searchPattern: list[] - search for nodes with a given nodeName searchPattern
        @setting.hierarchy: bool = lsHierarchy code to return all children from the given nodes      
        @setting.metaRig: bool = use the MetaRig wires to build the initial Object list up
        
        NOTE: with all the search and hierarchy settings OFF the code performs
        a Dumb copy, no matching and no Hierarchy filtering, copies using 
        selected pairs obj[0]>obj[1], obj[2]>obj[3] etc 
        -----------------------------------------------------------------

        '''
        
        log.debug('CopyAttributes params : nodes=%s : attributes=%s : filterSettings=%s' 
                   % (nodes, attributes, filterSettings))
        
        #Build up the node pairs to process
        nodeList = r9Core.processMatchedNodes(nodes, filterSettings, toMany).MatchedPairs
        
        if nodeList:       
            with r9General.HIKContext([d for _,d in nodeList]):
                for src, dest in nodeList:  
                    try:
                        if attributes:
                            #copy only specific attributes
                            for attr in attributes:
                                if cmds.attributeQuery(attr, node=src, exists=True) \
                                    and cmds.attributeQuery(attr, node=src, exists=True):
                                    cmds.setAttr('%s.%s' % (dest, attr), cmds.getAttr('%s.%s' % (src, attr)))
                        else:
                            attrs = []
                            settableAttrs = getSettableChannels(src,incStatics=True)
                            if skipAttrs:
                                attrs = set(settableAttrs) - set(skipAttrs)
                            else:
                                attrs = settableAttrs
                                
                            for attr in attrs:
                                if cmds.attributeQuery(attr, node=dest, exists=True):
                                    #log.debug('attr : %s.%s' % (dest, attr))
                                    cmds.setAttr('%s.%s' % (dest, attr), cmds.getAttr('%s.%s' % (src, attr)))
                    except:
                        pass
        else:
            raise StandardError('Nothing found by the Hierarchy Code to process')
        return True 
    
    
    #===========================================================================
    # Transform Snapping 
    #===========================================================================
    
    #@processInputNodes 
    def snapTransform(self, nodes=None, time=(), step=1, preCopyKeys=1, preCopyAttrs=1, 
                      filterSettings=None, iterations=1, **kws):
        '''
        Snap objects over a timeRange. This wraps the default hierarchy filters
        so it's capable of multiple hierarchy filtering and matching methods.
        The resulting node lists are snapped over time and keyed.  
        @requires: SnapRuntime plugin to be available
        
        @param nodes: List of Maya nodes to process. This combines the filterSettings
            object and the MatchedNodeInputs.processMatchedPairs() call, 
            making it capable of powerful hierarchy filtering and node matching methods.
        
        @param filterSettings: Passed into the decorator and onto the FilterNode code
            to setup the hierarchy filters - See docs on the FilterNode_Settings class
                   
        @param time: Copy over a given timerange - time=(start,end). Default is
            to use no timeRange. If time is passed in via the timeLineRange() function
            then it will consider the current timeLine PlaybackRange, OR if you have a
            highlighted range of time selected(in red) it'll use this instead.

        @param step: Time Step between processing when using kws['time'] range
            this accepts negative values to run the time backwards if required
        
        @param preCopyKeys: Run a CopyKeys pass prior to snap - this means that
            all channels that are keyed have their data taken across
            
        @param preCopyAttrs: Run a CopyAttrs pass prior to snap - this means that
            all channel Values on all nodes will have their data taken across
        
        @param iterations: Number of times to process the frame.
         
        NOTE: you can also pass the CopyKey kws in to the preCopy call, see copyKeys above
        
        Generic filters passed into r9Core.MatchedNodeInputs class:
        -----------------------------------------------------------------
        @setting.nodeTypes: list[] - search for child nodes of type (wraps cmds.listRelatives types=)
        @setting.searchAttrs: list[] - search for child nodes with Attrs of name 
        @setting.searchPattern: list[] - search for nodes with a given nodeName searchPattern
        @setting.hierarchy: bool = lsHierarchy code to return all children from the given nodes      
        @setting.metaRig: bool = use the MetaRig wires to build the initial Object list up
        
        NOTE: with all the search and hierarchy settings OFF the code performs
        a Dumb copy, no matching and no Hierarchy filtering, copies using 
        selected pairs obj[0]>obj[1], obj[2]>obj[3] etc 
        -----------------------------------------------------------------    
        '''
        self.snapCacheData = {} #TO DO - Cache the data and check after first run data is all valid
        skipAttrs = ['translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ']
        
        try:
            checkRunTimeCmds()
        except StandardError, error:
            raise StandardError(error)
            
        log.debug('snapTransform params : nodes=%s : time=%s : step=%s : preCopyKeys=%s : preCopyAttrs=%s : filterSettings=%s' \
                   % (nodes, time, step, preCopyKeys, preCopyAttrs, filterSettings))
        
        #Build up the node pairs to process
        nodeList = r9Core.processMatchedNodes(nodes, filterSettings)
        
        if nodeList.MatchedPairs:    
            nodeList.MatchedPairs.reverse() #reverse order so we're dealing with children before their parents
            
            if preCopyAttrs:
                self.copyAttributes(nodes=nodeList, skipAttrs=skipAttrs, filterSettings=filterSettings)
            
            if time:
                with r9General.AnimationContext(): #Context manager to restore settings
                    
                    cmds.autoKeyframe(state=False)   
                    #run a copyKeys pass to take all non transform data over  
                    #maybe do a channel attr pass to get non-keyed data over too?                   
                    if preCopyKeys: 
                        self.copyKeys(nodes=nodeList, time=time, filterSettings=filterSettings, **kws)
                           
                    for t in timeLineRangeProcess(time[0], time[1]+1, step):
                        dataAligned = False
                        processRepeat = iterations
                       
                        while not dataAligned:
                            for src, dest in nodeList.MatchedPairs:     
                                #we'll use the API MTimeControl in the runtime function 
                                #to update the scene without refreshing the Viewports
                                cmds.currentTime(t, e=True, u=False)
                                #pass to the plug-in SnapCommand
                                cmds.SnapTransforms(source=src, destination=dest, timeEnabled=True)    
                                #fill the snap cache for error checking later
                                #self.snapCacheData[dest]=data
                                cmds.setKeyframe(dest, at='translate')
                                cmds.setKeyframe(dest, at='rotate')
                                log.debug('Snapfrm %s : %s - %s : to : %s' % (str(t), r9Core.nodeNameStrip(src), dest, src))
        
                            processRepeat -= 1   
                            if not processRepeat:
                                dataAligned = True
            else:
                for _ in range(0, iterations):
                    for src, dest in nodeList.MatchedPairs:
                        cmds.SnapTransforms(source=src, destination=dest, timeEnabled=False) 
                        #self.snapCacheData[dest]=data 
                        log.debug('Snapped : %s - %s : to : %s' % (r9Core.nodeNameStrip(src), dest, src))   
        else:
            raise StandardError('Nothing found by the Hierarchy Code to process')
        return True 


    def snapValidateResults(self):
        '''
        Run through the stored snap values to see if, once everything is processed,
        all the nodes still match. ie, you snap the Shoulders and strore the results,
        then at the end of the process you find that the Shoulders aren't in the same
        position due to a driver controller shifting it because of hierarchy issues.
        TO IMPLEMENT
        '''
        raise NotImplemented
    
    @staticmethod
    def snap(nodes=None):
        '''
        This takes 2 given transform nodes and snaps them together. It takes into 
        account offsets in the pivots of the objects. Uses the API MFnTransform nodes
        to calculate the data via a command plugin. This is a stripped down version
        of the snapTransforms cmd
        '''
        try:
            checkRunTimeCmds()
        except StandardError, error:
            raise StandardError(error)
        
        if not nodes:
            nodes = cmds.ls(sl=True, l=True)
        if nodes:
            if not len(nodes) >= 2:
                raise StandardError('Please select at least 2 base objects for the SnapAlignment')
        else:
            raise StandardError('Please select at least 2 base objects for the SnapAlignment')
        
        #pass to the plugin SnapCommand
        for node in nodes[1:]:
            cmds.SnapTransforms(source=nodes[0], destination=node)
 

        
    @staticmethod
    def stabilizer(nodes=None, time=(), step=1):
        '''
        This is designed with 2 specific functionalities:
        If you have a single node selected it will stabilize it regardless 
        of it's inputs or parent hierarchy animations
        If you pass in 2 objects then it will Track B to A (same order as constraints)
        This is primarily designed to aid in MoCap cleanup and character interactions.
        This now also allows for Component based track inputs, ie, track this 
        nodes to this poly's normal

        @param nodes: either single (Stabilize) or twin to track
        @param time: [start,end] for a frameRange 
        @param step: int value for frame advance between process runs         
        '''
        
        #destObj = None  #Main Object being manipulated and keyed
        #snapRef = None  #Tracking ReferenceObject Used to Pass the transforms over
        deleteMe = []
        
        #can't use the anim context manager here as that resets the currentTime
        autokeyState = cmds.autoKeyframe(query=True, state=True)
        cmds.autoKeyframe(state=False)
        
        try:
            checkRunTimeCmds()
        except StandardError, error:
            raise StandardError(error)
        
        if time:
            timeRange = timeLineRangeProcess(time[0], time[1]+1, step)
            cmds.currentTime(timeRange[0], e=True) #ensure that the initial time is updated 
        else:
            timeRange = [cmds.currentTime(q=True) + step]  
        log.debug('timeRange : %s', timeRange)
        
        if not nodes:
            nodes = cmds.ls(sl=True, l=True)
             
        destObj = nodes[-1]  
        snapRef = cmds.spaceLocator()[0]   
        deleteMe.append(snapRef)
        
        #Generate the reference node that we'll use to snap too 
        #==========================================================
        if len(nodes) == 2:  
            # Tracker Mode 2 nodes passed in - Reference taken against the source node position  
            offsetRef = nodes[0]
            
            if cmds.nodeType(nodes[0]) == 'mesh':  #Component level selection method
                if r9Setup.mayaVersion() >= 2011:
                    offsetRef = cmds.spaceLocator()[0]
                    deleteMe.append(offsetRef)
                    cmds.select([nodes[0], offsetRef])
                    pointOnPolyCmd([nodes[0], offsetRef])
                else:
                    raise StandardError('Component Level Tracking is only available in Maya2011 upwards')
            
            cmds.parent(snapRef, offsetRef)
            cmds.SnapTransforms(source=destObj, destination=snapRef)
        else:
            # Stabilizer Mode - take the reference from the node position itself
            cmds.SnapTransforms(source=destObj, destination=snapRef)

        #Now run the snap against the reference node we've just made
        #==========================================================
        for time in timeRange:
            #Switched to using the Commands time query to stop  the viewport updates
            cmds.currentTime(time, e=True, u=False)
            cmds.SnapTransforms(source=snapRef, destination=destObj, timeEnabled=True) 
            try:
                cmds.setKeyframe(destObj, at='translate')
            except:
                pass
            try:
                cmds.setKeyframe(destObj, at='rotate')
            except:
                pass
                      
        cmds.delete(deleteMe)         
        cmds.autoKeyframe(state=autokeyState)               
        cmds.select(nodes)
        
    @staticmethod    
    def inverseAnimChannels(node, channels, time=None):
        '''
        really basic method used in the Mirror calls
        '''
        #for chan in channels:
            #cmds.scaleKey('%s_%s' % (node,chan),vs=-1)
        if time:
            cmds.scaleKey(node,valueScale=-1,attribute=channels,time=time)
        else:
            cmds.scaleKey(node,valueScale=-1,attribute=channels)
            
    @staticmethod
    def inverseAttributes(node, channels):
        '''
        really basic method used in the Mirror calls
        '''
        for chan in channels:
            try:
                cmds.setAttr('%s.%s' % (node,chan), cmds.getAttr('%s.%s' % (node,chan))*-1)
            except:
                log.debug('failed to inverse %s attr' % chan)
  


class RandomizeKeys(object):
    '''
    This is a simple implementation of a Key Randomizer, designed to add
    noise to animations    
    '''
    def __init__(self):
        self.win='KeyRandomizerOptions' 
        
    def noiseFunc(self,initialValue,randomRange,damp):
        '''
        really simple noise func, maybe I'll flesh this out at somepoint
        '''
        return initialValue + (random.uniform(randomRange[0],randomRange[1])*damp)
    
    @classmethod
    def showOptions(cls):
        cls()._showUI()
        
    def _showUI(self):
                 
            if cmds.window(self.win, exists=True): cmds.deleteUI(self.win, window=True)
            window = cmds.window(self.win, title="KeyRandomizer", s=False, widthHeight=(260,300))
            
            cmds.columnLayout(adjustableColumn=True,columnAttach=('both',5))
            cmds.separator(h=15, style='none')

            cmds.floatFieldGrp('ffg_rand_damping', label='strength : value', v1=1, precision=2)
            cmds.floatFieldGrp('ffg_rand_frmStep', label='frameStep', v1=1, en=False, precision=2)
            cmds.separator(h=15, style='in')
            cmds.rowColumnLayout(numberOfColumns=2,columnWidth=[(1,125),(2,125)])
            cmds.checkBox('cb_rand_current',
                          l='Current Keys Only',v=True,
                          cc=lambda x:self.__uicb_currentKeysCallback()) 
            cmds.checkBox('cb_rand_percent',
                          l='Pre-Normalize Curves', v=True,
                          ann='Pre-Normalize: process based on value percentage range auto-calculated from curves',
                          cc=lambda x:self.__uicb_percentageCallback()) 
            cmds.setParent('..')
            cmds.separator(h=15,style='none')  
            cmds.rowColumnLayout(numberOfColumns=2,columnWidth=[(1,125),(2,125)])
            cmds.button(label='Apply', bgc=r9Setup.red9ButtonBGC(1),
                         command=lambda *args:(RandomizeKeys().curveMenuFunc()))   
            cmds.button(label='SavePref', bgc=r9Setup.red9ButtonBGC(1),
                         command=lambda *args:(self.__storePrefs()))
            cmds.setParent('..')
            cmds.separator(h=15,style='none')  
            cmds.iconTextButton( style='iconOnly', bgc=(0.7,0,0),image1='Rocket9_buttonStrap2.bmp',
                                 c=lambda *args:(r9Setup.red9ContactInfo()),h=22,w=200 )
            cmds.showWindow(window)
            self.__loadPrefsToUI()
    
    def __uicb_currentKeysCallback(self):
        if cmds.checkBox('cb_rand_current',q=True,v=True):
            cmds.floatFieldGrp('ffg_rand_frmStep',e=True,en=False)
        else:
            cmds.floatFieldGrp('ffg_rand_frmStep',e=True,en=True)

    def __uicb_percentageCallback(self):
        if not cmds.checkBox('cb_rand_percent',q=True,v=True):
            cmds.floatFieldGrp('ffg_rand_damping',e=True, label='strength : value')
        else: 
            cmds.floatFieldGrp('ffg_rand_damping',e=True, label='strength : normalized %')
            
    def __storePrefs(self):
        if cmds.window(self.win, exists=True):
            cmds.optionVar(floatValue=('red9_randomizer_damp',cmds.floatFieldGrp('ffg_rand_damping',q=True,v1=True)))
            cmds.optionVar(intValue=('red9_randomizer_current',cmds.checkBox('cb_rand_current',q=True,v=True)))
            cmds.optionVar(intValue=('red9_randomizer_percent',cmds.checkBox('cb_rand_percent',q=True,v=True)))
            cmds.optionVar(floatValue=('red9_randomizer_frmStep',cmds.floatFieldGrp('ffg_rand_frmStep',q=True,v1=True)))
            log.debug('stored out ramdomizer prefs')
        
    def __loadPrefsToUI(self):
        if cmds.optionVar(exists='red9_randomizer_damp'):
            cmds.floatFieldGrp('ffg_rand_damping',e=True,v1=cmds.optionVar(q='red9_randomizer_damp'))
        if cmds.optionVar(exists='red9_randomizer_current'):
            cmds.checkBox('cb_rand_current',e=True,v=cmds.optionVar(q='red9_randomizer_current'))
        if cmds.optionVar(exists='red9_randomizer_percent'):
            cmds.checkBox('cb_rand_percent',e=True,v=cmds.optionVar(q='red9_randomizer_percent'))
        if cmds.optionVar(exists='red9_randomizer_frmStep'):
            cmds.floatFieldGrp('ffg_rand_frmStep',e=True,v1=cmds.optionVar(q='red9_randomizer_frmStep'))
        self.__uicb_currentKeysCallback()
        self.__uicb_percentageCallback()
    
    def __calcualteRangeValue(self,keyValues):
        vals=sorted(keyValues)
        rng=abs(vals[0]-vals[-1])/2
        if rng>1.0:
            return [-rng,rng]
        else:
            return [-1,1]
                           
    def addNoise(self, curves, time=(), step=1, currentKeys=True, randomRange=[-1,1], damp=1, percent=False):
        '''
        Simple noise function designed to add noise to keyframed animation data
        @param curves: Maya animCurves to process
        @param time: timeRange to process
        @param step: frame step used in the processor
        @param currentKeys: ONLY randomize keys that already exists 
        @param randomRange: range [upper, lower] bounds passed to teh randomizer
        @param damp: damping passed into the randomizer
        '''
        if percent:
            damp=damp/100
        if currentKeys:
            for curve in curves:
                #if keys/curves are already selected, process those only
                selectedKeys=cmds.keyframe(curve, q=True,vc=True,tc=True,sl=True)
                if selectedKeys:
                    keyData=selectedKeys
                else:   
                    #else process all keys inside the time
                    keyData=cmds.keyframe(curve, q=True,vc=True,tc=True,t=time)
                for t,v in zip(keyData[::2],keyData[1::2]):
                    if percent:
                        #figure the upper and lower value bounds
                        randomRange=self.__calcualteRangeValue(keyData[1::2])
                        log.info('Percent data : randomRange=%f>%f, percentage=%f' % (randomRange[0],randomRange[1],damp))
                    value=self.noiseFunc(v,randomRange,damp)
                    cmds.setKeyframe(curve, v=value,t=t)
        else:
            if not time:
                selectedKeyTimes=sorted(list(set(cmds.keyframe(q=True,tc=True))))
                if selectedKeyTimes:
                    time=(selectedKeyTimes[0],selectedKeyTimes[-1])
            for curve in curves:  
                if percent:    
                    #figure the upper and lower value bounds
                    randomRange=self.__calcualteRangeValue(cmds.keyframe(curve, q=True,vc=True,t=time))
                    log.info('Percent data : randomRange=%f>%f, percentage=%f' % (randomRange[0],randomRange[1],damp))
                connection=cmds.listConnections(curve,source=False,d=True,p=True)[0]
                for t in timeLineRangeProcess(time[0], time[1]+1, step):
                    value=self.noiseFunc(cmds.getAttr(connection,t=t),randomRange,damp)
                    cmds.setKeyframe(connection, v=value,t=t)
                    
    @classmethod
    def curveMenuFunc(cls):
        randomizer=cls()
        randomizer.__storePrefs()
        frmStep=1
        damping=1
        percent=False
        currentKeys=True
        
        if cmds.window(randomizer.win, exists=True):
            currentKeys=cmds.checkBox('cb_rand_current',q=True,v=True)
            damping=cmds.floatFieldGrp('ffg_rand_damping',q=True,v1=True)
            frmStep=cmds.floatFieldGrp('ffg_rand_frmStep',q=True,v1=True)
            percent=cmds.checkBox('cb_rand_percent',q=True,v=True)
        else:
            if cmds.optionVar(exists='red9_randomizer_damp'):
                damping=cmds.optionVar(q='red9_randomizer_damp')
            if cmds.optionVar(exists='red9_randomizer_percent'):
                percent=cmds.optionVar(q='red9_randomizer_percent')
            if cmds.optionVar(exists='red9_randomizer_current'):
                currentKeys=cmds.optionVar(q='red9_randomizer_current')
            if cmds.optionVar(exists='red9_randomizer_frmStep'):
                frmStep=cmds.optionVar(q='red9_randomizer_frmStep')
        
        selectedCurves=cmds.keyframe(q=True, sl=True, n=True)
        if not selectedCurves:
            raise StandardError('No Keys or Anim curves selected!')
        randomizer.addNoise(curves=selectedCurves,step=frmStep,damp=damping,currentKeys=currentKeys,percent=percent)  
                            
        
        
class MirrorHierarchy(object):
    
    '''
    This class is designed to mirror pose and animation data on any given
    hierarchy. The hierarchy is filtered like everything else in the Red9
    pack, using a filterSettings node thats passed into the __init__
    
    mirror=MirrorHierarchy(cmds.ls(sl=True)[0])
    #set the settings object to run metaData
    mirror.settings.metaRig=True
    mirror.settings.printSettings()
    mirror.mirrorData(mode='Anim') 
    
    TODO: We need to do a UI for managing these marker attrs and the Index lists
    '''
    
    def __init__(self, nodes=None, filterSettings=None):
        '''
        @param nodes: initial nodes to process
        @param filterSettings: filterSettings object to process hierarchies
        '''
        
        self.nodes=nodes
        
        #default Attributes used to define the system
        self.defaultMirrorAxis=['translateX','rotateY','rotateZ']
        #self.mirrorSide='MirrorMarker' #switched attr names to unify this and the MetaRig setups
        #self.mirrorIndex='MirrorList'  #switched attr names to unify this and the MetaRig setups
        #self.mirrorAxis='MirrorAxis'   #switched attr names to unify this and the MetaRig setups
        self.mirrorSide='mirrorSide'
        self.mirrorIndex='mirrorIndex'
        self.mirrorAxis='mirrorAxis'
        self.mirrorDict={'Centre':{},'Left':{},'Right':{}}
        
        # make sure we have a settings object
        if filterSettings:
            if issubclass(type(filterSettings), r9Core.FilterNode_Settings):
                self.settings=filterSettings
            else:
                raise StandardError('filterSettings param requires an r9Core.FilterNode_Settings object')
        else:
            self.settings=r9Core.FilterNode_Settings() 
            
        #ensure we use the mirrorSide attr search ensuring all nodes 
        #returned are part of the Mirror system
        self.settings.searchAttrs.append(self.mirrorSide)
    
    def _validateMirrorEnum(self,side):
        '''
        validate the given side to make sure it's formatted correctly before setting the data
        '''
        if not side:
            return False
        if type(side)==int and not side in range(0,3):
            raise ValueError('given mirror side is not a valid int entry: 0, 1 or 2')
        if not self.mirrorDict.has_key(side):
            raise ValueError('given mirror side is not a valid key: Left, Right or Centre')
        else:
            return True
        
    def setMirrorIDs(self, node, side=None, slot=None, axis=None):
        '''
        Add/Set the default attrs required by the MirrorSystems
        @param node: nodes to take the attrs
        @param side: valid values are 'Centre','Left' or 'Right' or 0, 1, 2
        @param slot: bool Mainly used to pair up left and right paired controllers
        @param axis: eg 'translateX','rotateY','rotateZ' simple comma separated string
            If this is set then it overrides the default mirror axis. 
            These are the channels who have their attribute/animCurve values inversed 
            during mirror. NOT we allow axis to have a null string 'None' so it can be
            passed in blank when needed   
        NOTE: slot index can't be ZERO
        '''
        #Note using the MetaClass as all the type checking
        #and attribute handling is done for us
        mClass=r9Meta.MetaClass(node)
        if self._validateMirrorEnum(side):
            mClass.addAttr(self.mirrorSide,attrType='enum',enumName='Centre:Left:Right') 
            mClass.__setattr__(self.mirrorSide,side) 
        if slot:
            mClass.addAttr(self.mirrorIndex ,slot, hidden=True)
            mClass.__setattr__(self.mirrorIndex,slot) 
        if axis:
            if axis=='None':
                mClass.addAttr(self.mirrorAxis, attrType='string')
            else:
                mClass.addAttr(self.mirrorAxis, axis)
                mClass.__setattr__(self.mirrorAxis,axis) 
    
    def deleteMirrorIDs(self,node):
        '''
        Remove the given node from the MirrorSystems
        '''
        mClass=r9Meta.MetaClass(node)
        try: 
            mClass.__delattr__(self.mirrorSide)
        except: 
            pass
        try: 
            mClass.__delattr__(self.mirrorIndex)
        except:
            pass
        try:
            mClass.__delattr__(self.mirrorAxis)
        except:
            pass
             
    def getNodes(self):
        '''
        Get the list of nodes to start processing
        '''
        return r9Core.FilterNode(self.nodes,filterSettings=self.settings).ProcessFilter()
     
    def getMirrorSide(self,node):
        '''
        This is an enum Attr to denote the Side of the controller in the Mirror system
        '''
        return cmds.getAttr('%s.%s' % (node,self.mirrorSide),asString=True)

    def getMirrorIndex(self,node):
        '''
        get the mirrorIndex, these slots are used to denote matching pairs
        such that Left and Right Controllers to switch will have the same index
        '''
        return int(cmds.getAttr('%s.%s' % (node,self.mirrorIndex)))
   
    def getMirrorAxis(self,node):
        '''
        get any custom attributes set at node level to inverse, if none found
        return the default axis setup in the __init__
        NOTE: if mirrorAxis attr has been added to the node but is empty then 
        no axis will be inversed at all. If the attr doesn't exist then the 
        default inverse axis will be used
        '''
        if cmds.attributeQuery(self.mirrorAxis,node=node,exists=True):
            axis=cmds.getAttr('%s.%s' %(node,self.mirrorAxis))
            if not axis:
                return []
            else:
                return axis.split(',')
        else:
            return self.defaultMirrorAxis
        
    def getMirrorSets(self,nodes=None):
        '''
        Filter the given nodes into the mirrorDict
        such that {'Centre':{id:node,},'Left':{id:node,},'Right':{id:node,}}
        '''
        #reset the current Dict prior to rescanning
        self.mirrorDict={'Centre':{},'Left':{},'Right':{}}
        if not nodes:
            nodes=self.getNodes()
        for node in nodes:
            try:
                side=self.getMirrorSide(node)
                index=self.getMirrorIndex(node)
                log.debug('Side : %s Index : %s>> node %s' % \
                          ( side, index, r9Core.nodeNameStrip(node)))
                self.mirrorDict[side][index]=node
            except StandardError,error:
                log.debug(error)
                log.info('Failed to add Node to Mirror System : %s' % r9Core.nodeNameStrip(node))
    
    def printMirrorDict(self,short=True):
        '''
        Pretty print the Mirror Dict 
        '''
        self.getMirrorSets()
        if not short:
            print '\nCenter MirrorLists ====================================================='
            for i,node in self.mirrorDict['Centre'].items(): print '%s > %s' % (i,node)
            print '\nRight MirrorLists ======================================================'
            for i,node in self.mirrorDict['Right'].items(): print '%s > %s' % (i,node)
            print '\nLeft MirrorLists ======================================================='
            for i,node in self.mirrorDict['Left'].items(): print '%s > %s' % (i,node)
        else:
            print '\nCenter MirrorLists ====================================================='
            for i,node in self.mirrorDict['Centre'].items(): print '%s > %s' % (i,r9Core.nodeNameStrip(node))
            print '\nRight MirrorLists ======================================================'
            for i,node in self.mirrorDict['Right'].items(): print '%s > %s' % (i,r9Core.nodeNameStrip(node))
            print '\nLeft MirrorLists ======================================================='
            for i,node in self.mirrorDict['Left'].items(): print '%s > %s' % (i,r9Core.nodeNameStrip(node))
                          
    def mirrorPairData(self,objA,objB,method='Anim'):
        '''
        take the left and right matched pairs and exchange the animData
        across between them
        '''
        objs=cmds.ls(sl=True,l=True)
        if method=='Anim':
            transferCall= AnimFunctions().copyKeys
            inverseCall = AnimFunctions.inverseAnimChannels
        else:
            transferCall= AnimFunctions().copyAttributes
            inverseCall = AnimFunctions.inverseAttributes
        
        #switch the anim data over via temp
        cmds.select(objA)
        cmds.duplicate()
        temp=cmds.ls(sl=True,l=True)[0]
        log.debug('temp %s:' % temp)
        transferCall([objA,temp])
        transferCall([objB,objA])
        transferCall([temp,objB])
        cmds.delete(temp)
        
        #inverse the values
        inverseCall(objA,self.getMirrorAxis(objA))
        inverseCall(objB,self.getMirrorAxis(objB))
        if objs:cmds.select(objs)
        
    def mirrorData(self, nodes=None, mode='Anim'):
        '''
        Using the FilterSettings obj find all nodes in the return that have
        the mirrorSide attr, then process the lists into Side and Index slots
        before Mirroring the animation data. Swapping left for right and
        inversing the required animCurves
        '''
        self.getMirrorSets(nodes)
        
        #Switch Pairs on the Left and Right and inverse the channels
        for index,node in self.mirrorDict['Left'].items():
            if not index in self.mirrorDict['Right'].keys():
                log.warning('No matching Index Key found for Left mirrorIndex : %s >> %s' % (index,r9Core.nodeNameStrip(node)))
            else:
                log.debug('SwitchingPairs : %s >> %s' % (r9Core.nodeNameStrip(node),\
                                     r9Core.nodeNameStrip(self.mirrorDict['Right'][index])))
                self.mirrorPairData(node,self.mirrorDict['Right'][index],method=mode)
                
        #Inverse the Centre Nodes
        for node in self.mirrorDict['Centre'].values():
            if mode=='Anim':
                AnimFunctions.inverseAnimChannels(node, self.getMirrorAxis(node))
            else:
                AnimFunctions.inverseAttributes(node, self.getMirrorAxis(node))
                    
        
class MetaAnimUtil_TestClass(r9Meta.MetaClass):
    '''
    SubClass of the Meta, this is here for me to test the ittersubclass function which
    works out the full inheritance map of r9Meta.MetaClass for all modules
    This class should get added to the RED9_META_REGISTERY
    '''
    def __init__(self,*args,**kws):
        super(MetaAnimUtil_TestClass, self).__init__(*args,**kws) 
        

        