"""
------------------------------------------
cgm.core.rigger: Limb.neckHead
Author: Josh Burton
email: jjburton@cgmonks.com

Website : http://www.cgmonks.com
------------------------------------------

neckHead rig builder
================================================================
"""
__version__ = 0.04242013


# From Python =============================================================
import copy
import re

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# From Maya =============================================================
import maya.cmds as mc

# From Red9 =============================================================
from Red9.core import Red9_Meta as r9Meta
from Red9.core import Red9_General as r9General

# From cgm ==============================================================
from cgm.core import cgm_Meta as cgmMeta
from cgm.core.classes import SnapFactory as Snap
from cgm.core.classes import NodeFactory as NodeF
reload(NodeF)

from cgm.core.rigger import ModuleShapeCaster as mShapeCast
from cgm.core.rigger import ModuleControlFactory as mControlFactory
from cgm.core.lib import nameTools
reload(mShapeCast)
reload(mControlFactory)
from cgm.core.rigger.lib import rig_Utils as rUtils
reload(rUtils)
from cgm.lib import (attributes,
                     joints,
                     skinning,
                     dictionary,
                     distance,
                     modules,
                     search,
                     curves,
                     )

#>>> Skeleton
#===================================================================
__l_jointAttrs__ = ['startAnchor','endAnchor','anchorJoints','rigJoints','influenceJoints','segmentJoints']   

@r9General.Timer
def build_rigSkeleton(self):
    """
    """
    try:
	if not self._cgmClass == 'RigFactory.go':
	    log.error("Not a RigFactory.go instance: '%s'"%self)
	    raise StandardError
    except StandardError,error:
	log.error("neckHead.build_deformationRig>>bad self!")
	raise StandardError,error
    
    #>>>Create joint chains
    #=============================================================    
    try:
	#>>Segment chain    
	"""
	l_segmentJoints = mc.duplicate(self._l_skinJoints,po=True,ic=True,rc=True)
	ml_segmentJoints = []
	for i,j in enumerate(l_segmentJoints):
	    i_j = cgmMeta.cgmObject(j)
	    i_j.addAttr('cgmTypeModifier','segment',attrType='string')
	    i_j.doName()
	    l_segmentJoints[i] = i_j.mNode
	    ml_segmentJoints.append(i_j)
	ml_segmentJoints[0].parent = False#Parent to world
	"""
	#>>Deformation chain  
	#=====================================================================	
	l_rigJoints = mc.duplicate(self._l_skinJoints,po=True,ic=True,rc=True)
	ml_rigJoints = []
	for i,j in enumerate(l_rigJoints):
	    i_j = cgmMeta.cgmObject(j)
	    i_j.addAttr('cgmTypeModifier','rig',attrType='string',lock=True)
	    i_j.doName()
	    l_rigJoints[i] = i_j.mNode
	    ml_rigJoints.append(i_j)
	ml_rigJoints[0].parent = False#Parent to deformGroup
	
	#>>Segment chain  
	#=====================================================================
	l_segmentJoints = mc.duplicate(self._l_skinJoints,po=True,ic=True,rc=True)
	ml_segmentJoints = []
	for i,j in enumerate(l_segmentJoints):
	    i_j = cgmMeta.cgmObject(j)
	    i_j.addAttr('cgmTypeModifier','segment',attrType='string',lock=True)
	    i_j.doName()
	    l_rigJoints[i] = i_j.mNode
	    ml_segmentJoints.append(i_j)
	ml_segmentJoints[0].parent = False#Parent to deformGroup	
	
	#>>Anchor chain
	#=====================================================================	
	ml_anchors = []
	
	#Start
	i_startJnt = cgmMeta.cgmObject(mc.duplicate(self._l_skinJoints[0],po=True,ic=True,rc=True)[0])
	i_startJnt.addAttr('cgmType','anchor',attrType='string',lock=True)
	i_startJnt.doName()
	i_startJnt.parent = False
	ml_anchors.append(i_startJnt)
	
	#End
	l_endJoints = mc.duplicate(self._l_skinJoints[-1],po=True,ic=True,rc=True)
	i_endJnt = cgmMeta.cgmObject(l_endJoints[0])
	for j in l_endJoints:
	    #for i_j in [i_endJnt]:
	    i_j = cgmMeta.cgmObject(j)
	    i_j.addAttr('cgmType','anchor',attrType='string',lock=True)
	    i_j.doName()
	i_endJnt.parent = False
	ml_anchors.append(i_endJnt)
	for i_obj in ml_anchors:
	    i_obj.rotateOrder = 2#<<<<<<<<<<<<<<<<This would have to change for other orientations
	
	#Influence chain for influencing the surface
	ml_influenceJoints = []
	for i_jnt in self._ml_skinJoints:
	    if i_jnt.hasAttr('cgmName') and i_jnt.cgmName in self._l_coreNames:
		i_new = cgmMeta.cgmObject(mc.duplicate(i_jnt.mNode,po=True,ic=True)[0])
		i_new.addAttr('cgmType','influenceJoint',attrType='string',lock=True)
		i_new.parent = False
		i_new.doName()
		if ml_influenceJoints:#if we have data, parent to last
		    i_new.parent = ml_influenceJoints[-1]
		else:i_new.parent = False
		i_new.rotateOrder = 'zxy'#<<<<<<<<<<<<<<<<This would have to change for other orientations
		ml_influenceJoints.append(i_new)
	for i_jnt in ml_influenceJoints:
	    i_jnt.parent = False		
	#>>> Store em all to our instance
	self._i_rigNull.connectChildNode(i_startJnt,'startAnchor','module')
	self._i_rigNull.connectChildNode(i_endJnt,'endAnchor','module')	
	self._i_rigNull.connectChildrenNodes(ml_anchors,'anchorJoints','module')
	self._i_rigNull.connectChildrenNodes(ml_rigJoints,'rigJoints','module')
	self._i_rigNull.connectChildrenNodes(ml_segmentJoints,'segmentJoints','module')	
	self._i_rigNull.connectChildrenNodes(ml_influenceJoints,'influenceJoints','module')
	self._i_rigNull.connectChildrenNodes(self._l_skinJoints,'skinJoints')#Restore our list since duplication extendes message attrs
	
	log.info("startAnchor>> %s"%i_startJnt.getShortName())
	log.info("endAnchor>> %s"%i_endJnt.getShortName())
	log.info("anchorJoints>> %s"%self._i_rigNull.getMessage('anchorJoints',False))
	log.info("rigJoints>> %s"%self._i_rigNull.getMessage('rigJoints',False))
	log.info("segmentJoints>> %s"%self._i_rigNull.getMessage('segmentJoints',False))
	log.info("influenceJoints>> %s"%self._i_rigNull.getMessage('influenceJoints',False))
	log.info("skinJoints>> %s"%self._i_rigNull.getMessage('skinJoints',False))
	
	
    except StandardError,error:
	log.error("build_neckHead>>Build rig joints fail!")
	raise StandardError,error   
    
    ml_jointsToConnect = [i_startJnt,i_endJnt]
    ml_jointsToConnect.extend(ml_rigJoints)
    ml_jointsToConnect.extend(ml_segmentJoints)    
    ml_jointsToConnect.extend(ml_influenceJoints)

    for i_jnt in ml_jointsToConnect:
	i_jnt.overrideEnabled = 1		
	cgmMeta.cgmAttr(self._i_rigNull.mNode,'gutsVis',lock=False).doConnectOut("%s.%s"%(i_jnt.mNode,'overrideVisibility'))
	cgmMeta.cgmAttr(self._i_rigNull.mNode,'gutsLock',lock=False).doConnectOut("%s.%s"%(i_jnt.mNode,'overrideDisplayType'))    
	
#>>> Shapes
#===================================================================
__d_controlShapes__ = {'shape':['segmentFKLoli','segmentIK']}
@r9General.Timer
def build_shapes(self):
    """
    """ 
    try:
	
	if not self._cgmClass == 'RigFactory.go':
	    log.error("Not a RigFactory.go instance: '%s'"%self)
	    raise StandardError
    except StandardError,error:
	log.error("neckHead.build_rig>>bad self!")
	raise StandardError,error
    
    #>>>Build our Shapes
    #=============================================================
    try:
	l_toBuild = ['segmentFK_Loli','segmentIK']
	
	mShapeCast.go(self._i_module,l_toBuild, storageInstance=self)#This will store controls to a dict called    
	log.info(self._md_controlShapes)
	
    except StandardError,error:
	log.error("build_neckHead>>Build shapes fail!")
	raise StandardError,error    
    
def build_controls(self):
    """
    """    
    try:
	if not self._cgmClass == 'RigFactory.go':
	    log.error("Not a RigFactory.go instance: '%s'"%self)
	    raise StandardError
    except StandardError,error:
	log.error("neckHead.build_rig>>bad self!")
	raise StandardError,error
    
    try: self._md_controlShapes['segmentIK']
    except StandardError,error:    
	log.warning("neckHead.build_controls>>>Shapes issue, rebuilding. Error: %s"%error)
	build_shapes(self)
	
    #>>> Get some special pivot xforms
    ml_segmentJoints = self._i_rigNull.rigJoints 
    l_segmentJoints  = [i_jnt.mNode for i_jnt in ml_segmentJoints] 
    tmpCurve = curves.curveFromObjList(l_segmentJoints)
    midPivotPos = distance.returnWorldSpacePosition("%s.u[%f]"%(tmpCurve,.5))
    log.info("midPivotPos : %s"%midPivotPos)   
    mc.delete(tmpCurve)
	    
    l_controlsAll = []#we'll append to this list and connect them all at the end 
    
    #==================================================================
    try:#>>>> FK Segments
	if len( self._md_controlShapes['segmentFK_Loli'] )<2:
	    raise StandardError,"build_controls>> Must have at least two fk controls"
	
	ml_shapes = self._md_controlShapes['segmentFK_Loli']
	ml_segmentsFK = ml_shapes[:-1]
	log.info(ml_segmentsFK)
	
	for i,i_obj in enumerate(ml_segmentsFK[1:]):#parent
	    i_obj.parent = ml_segmentsFK[i].mNode
	    	
	for i,i_obj in enumerate(ml_segmentsFK):
	    d_buffer = mControlFactory.registerControl(i_obj,addExtraGroups=1,setRotateOrder=5,typeModifier='fk',) 	    
	    #if i == 0:
		#i_loc = ml_segmentsFK[i].doLoc()
		#mc.move (hipPivotPos[0],hipPivotPos[1],hipPivotPos[2], i_loc.mNode)		
		#d_buffer = mControlFactory.registerControl(i_obj,addExtraGroups=1,setRotateOrder=5,
		                                           #copyPivot=i_loc.mNode,typeModifier='fk') 
		#i_loc.delete()
		
	    i_obj = d_buffer['instance']
	
	self._i_rigNull.connectChildrenNodes(ml_segmentsFK,'controlsFK','module')
	l_controlsAll.extend(ml_segmentsFK)	
	ml_segmentsFK[0].masterGroup.parent = self._i_deformNull.mNode
    
    except StandardError,error:
	log.error("build_neckHead>>Build fk fail!")
	raise StandardError,error
    
    #==================================================================    
    try:#>>>> IK Segments
	ml_segmentsIK = self._md_controlShapes['segmentIK']
	
	for i_obj in ml_segmentsIK:
	    d_buffer = mControlFactory.registerControl(i_obj,addExtraGroups=1,typeModifier='ik',
		                                       setRotateOrder=2)       
	    i_obj = d_buffer['instance']
	    i_obj.masterGroup.parent = self._i_deformNull.mNode
	self._i_rigNull.connectChildrenNodes(ml_segmentsIK,'segmentHandles','module')
	l_controlsAll.extend(ml_segmentsIK)	
	
	
    except StandardError,error:
	log.error("build_neckHead>>Build ik handle fail!")
	raise StandardError,error
    
    #==================================================================
    try:#>>>> IK Handle
	i_IKEnd = ml_shapes[-1]
	i_IKEnd.parent = False
	"""
	i_loc = i_IKEnd.doLoc()#Make loc for a new transform
	i_loc.rx = i_loc.rx + 90#offset   
	mc.move (shouldersPivotPos[0],shouldersPivotPos[1],shouldersPivotPos[2], i_loc.mNode)
	"""
	d_buffer = mControlFactory.registerControl(i_IKEnd,
	                                           typeModifier='ik',addSpacePivots = 2, addDynParentGroup = True, addConstraintGroup=True,
	                                           makeAimable = True,setRotateOrder=4)
	i_IKEnd = d_buffer['instance']	

	i_IKEnd.masterGroup.parent = self._i_deformNull.mNode
	
	#i_loc.delete()#delete
	self._i_rigNull.connectChildNode(i_IKEnd,'handleIK','module')#connect
	l_controlsAll.append(i_IKEnd)	

	#Set aims
	i_IKEnd.axisAim = 4
	i_IKEnd.axisUp= 2
	
	
    except StandardError,error:
	log.error("build_neckHead>>Build ik handle fail!")
	raise StandardError,error   
      
    
    #Connect all controls
    self._i_rigNull.connectChildrenNodes(l_controlsAll,'controlsAll')
    
    return True


def build_deformation(self):
    """
    Rotate orders
    hips = 3
    """     
    try:
	if not self._cgmClass == 'RigFactory.go':
	    log.error("Not a RigFactory.go instance: '%s'"%self)
	    raise StandardError
    except StandardError,error:
	log.error("neckHead.build_deformationRig>>bad self!")
	raise StandardError,error
    
    #>>>Get data
    ml_influenceJoints = self._i_rigNull.influenceJoints
    ml_controlsFK =  self._i_rigNull.controlsFK    
    ml_rigJoints = self._i_rigNull.rigJoints
    ml_segmentJoints = self._i_rigNull.segmentJoints    
    ml_anchorJoints = self._i_rigNull.anchorJoints
    ml_segmentHandles = self._i_rigNull.segmentHandles
    aimVector = dictionary.stringToVectorDict.get("%s+"%self._jointOrientation[0])
    upVector = dictionary.stringToVectorDict.get("%s+"%self._jointOrientation[1])
    mi_handleIK = self._i_rigNull.handleIK
    

    #Control Segment
    #====================================================================================
    try:#Control Segment
	log.info(self._jointOrientation)
	capAim = self._jointOrientation[0].capitalize()
	log.info("capAim: %s"%capAim)
	i_startControl = ml_segmentHandles[0]
	i_endControl = ml_segmentHandles[-1]
	#Create segment
	curveSegmentReturn = rUtils.createCGMSegment([i_jnt.mNode for i_jnt in ml_segmentJoints],
	                                             addSquashStretch=True,
	                                             addTwist=True,
	                                             influenceJoints=[ml_influenceJoints[0],ml_influenceJoints[-1]],
	                                             startControl=ml_segmentHandles[0],
	                                             endControl=ml_segmentHandles[-1],
	                                             orientation=self._jointOrientation,
	                                             baseName=self._partName,
	                                             moduleInstance=self._i_module)
	
	i_curve = curveSegmentReturn['mi_segmentCurve']
	i_curve.parent = self._i_rigNull.mNode
	self._i_rigNull.connectChildrenNodes([i_curve],'segmentCurves','module')
	self._i_rigNull.connectChildrenNodes(ml_segmentJoints,'segmentJoints','module')	#Reconnect to reset. Duplication from createCGMSegment causes issues	
	i_curve.segmentGroup.parent = self._i_rigNull.mNode
	
	"""
	midReturn = rUtils.addCGMSegmentSubControl(ml_influenceJoints[1].mNode,
	                                           segmentCurve = i_curve,
	                                           baseParent=ml_influenceJoints[0],
	                                           endParent=ml_influenceJoints[-1],
	                                           midControls=ml_segmentHandles[1],
	                                           baseName=self._partName,
	                                           orientation=self._jointOrientation)
	
	for i_grp in midReturn['ml_followGroups']:#parent our follow Groups
	    i_grp.parent = self._i_deformNull.mNode"""
	    
    except StandardError,error:
	log.error("build_neckHead>>Control Segment build fail")
	raise StandardError,error
    
    
    try:#Setup top twist driver
	#Create an fk additive attributes
	str_curve = curveSegmentReturn['mi_segmentCurve'].getShortName()
	#fk_drivers = ["%s.r%s"%(i_obj.mNode,self._jointOrientation[0]) for i_obj in ml_controlsFK]
	"""fk_drivers = ["%s.r%s"%(i_obj.mNode,self._jointOrientation[0]) for i_obj in ml_controlsFK]	
	NodeF.createAverageNode(fk_drivers,
	                        [curveSegmentReturn['mi_segmentCurve'].mNode,"fkTwistSum"],1)#Raw fk twist
	
	try:NodeF.argsToNodes("%s.fkTwistResult = %s.fkTwistSum * %s.fkTwistInfluence"%(str_curve,str_curve,str_curve)).doBuild()
	except StandardError,error:
	    raise StandardError,"verify_moduleRigToggles>> fkwistResult node arg fail: %s"%error"""	
	
	drivers = ["%s.r%s"%(ml_segmentHandles[-1].mNode,self._jointOrientation[0])]
	drivers.append("%s.r%s"%(mi_handleIK.mNode,self._jointOrientation[0]))

	NodeF.createAverageNode(drivers,
	                        [curveSegmentReturn['mi_segmentCurve'].mNode,"twistEnd"],1)
	
    except StandardError,error:
	log.error("build_neckHead>>Top Twist driver fail")
	raise StandardError,error
    
    try:#Setup bottom twist driver
	log.info("%s.r%s"%(ml_segmentHandles[0].getShortName(),self._jointOrientation[0]))
	drivers = ["%s.r%s"%(ml_segmentHandles[0].mNode,self._jointOrientation[0])]
	drivers.append("%s.r%s"%(ml_controlsFK[0].mNode,self._jointOrientation[0]))

	NodeF.createAverageNode(drivers,
	                        [curveSegmentReturn['mi_segmentCurve'].mNode,"twistStart"],1)
    
    except StandardError,error:
	log.error("build_neckHead>>Bottom Twist driver fail")
	raise StandardError,error
    
        
    #Push squash and stretch multipliers to head
    i_buffer = i_curve.scaleBuffer
    
    for k in i_buffer.d_indexToAttr.keys():
	attrName = 'neckHead_%s'%k
	cgmMeta.cgmAttr(i_buffer.mNode,'scaleMult_%s'%k).doCopyTo(mi_handleIK.mNode,attrName,connectSourceToTarget = True)
	cgmMeta.cgmAttr(mi_handleIK.mNode,attrName,defaultValue = 1,keyable=True)
    
    return True

def build_rig(self):
    """
    Rotate orders
    hips = 3
    """    
    try:
	if not self._cgmClass == 'RigFactory.go':
	    log.error("Not a RigFactory.go instance: '%s'"%self)
	    raise StandardError
    except StandardError,error:
	log.error("neckHead.build_deformationRig>>bad self!")
	raise StandardError,error
    
    try:#>>>Get data
	orientation = modules.returnSettingsData('jointOrientation')
	mi_segmentCurve = self._i_rigNull.segmentCurves[0]
	mi_segmentAnchorStart = mi_segmentCurve.anchorStart
	mi_segmentAnchorEnd = mi_segmentCurve.anchorEnd
	mi_segmentAttachStart = mi_segmentCurve.attachStart
	mi_segmentAttachEnd = mi_segmentCurve.attachEnd 
	mi_distanceBuffer = mi_segmentCurve.scaleBuffer
	mi_moduleParent = False
	if self._i_module.getMessage('moduleParent'):
	    mi_moduleParent = self._i_module.moduleParent
    
	log.info("mi_segmentAnchorStart: %s"%mi_segmentAnchorStart.mNode)
	log.info("mi_segmentAnchorEnd: %s"%mi_segmentAnchorEnd.mNode)
	log.info("mi_segmentAttachStart: %s"%mi_segmentAttachStart.mNode)
	log.info("mi_segmentAttachEnd: %s"%mi_segmentAttachEnd.mNode)
	log.info("mi_distanceBuffer: %s"%mi_distanceBuffer.mNode)
	
	ml_influenceJoints = self._i_rigNull.influenceJoints
	#ml_segmentJoints = mi_segmentCurve.drivenJoints
	ml_segmentSplineJoints = mi_segmentCurve.driverJoints
	
	ml_anchorJoints = self._i_rigNull.anchorJoints
	ml_rigJoints = self._i_rigNull.rigJoints
	ml_segmentJoints = self._i_rigNull.segmentJoints	
	ml_segmentHandles = self._i_rigNull.segmentHandles
	aimVector = dictionary.stringToVectorDict.get("%s+"%self._jointOrientation[0])
	upVector = dictionary.stringToVectorDict.get("%s+"%self._jointOrientation[1])
	mi_handleIK = self._i_rigNull.handleIK
	ml_controlsFK =  self._i_rigNull.controlsFK    
	
    except StandardError,error:
	log.error("neckHead.build_rig>> Gather data fail!")
	raise StandardError,error
    
    #Dynamic parent groups
    #====================================================================================
    try:#>>>> Head dynamicParent
	#Build our dynamic groups
	ml_headDynParents = [ml_controlsFK[0]]
	if mi_moduleParent:
	    mi_parentRigNull = mi_moduleParent.rigNull
	    if mi_parentRigNull.getMessage('handleIK'):
		ml_headDynParents.append( mi_parentRigNull.handleIK )	    
	    if mi_parentRigNull.getMessage('cog'):
		ml_headDynParents.append( mi_parentRigNull.cog )
	ml_headDynParents.extend(mi_handleIK.spacePivots)
	ml_headDynParents.append(self._i_masterControl)
	log.info(ml_headDynParents)
	log.info([i_obj.getShortName() for i_obj in ml_headDynParents])
	
	#Add our parents
	i_dynGroup = mi_handleIK.dynParentGroup
	log.info("Dyn group at setup: %s"%i_dynGroup)
	i_dynGroup.dynMode = 2
	
	for o in ml_headDynParents:
	    i_dynGroup.addDynParent(o)
	i_dynGroup.rebuild()
	
	i_dynGroup.dynFollow.parent = self._i_masterDeformGroup.mNode
    except StandardError,error:
	log.error("neckHead.build_rig>> head dynamic parent setup fail!")
	raise StandardError,error

	
    #Parent and constrain joints
    #====================================================================================
    parentAttach = self._i_module.moduleParent.rigNull.skinJoints[-1].mNode
    mc.parentConstraint(parentAttach,self._i_deformNull.mNode,maintainOffset=True)#constrain
    mc.scaleConstraint(parentAttach,self._i_deformNull.mNode,maintainOffset=True)#Constrain
    
    ml_segmentJoints[0].parent = self._i_deformNull.mNode
    ml_segmentSplineJoints[0].parent = self._i_deformNull.mNode
    
    #Put the start and end controls in the heirarchy
    mc.parent(ml_segmentHandles[0].masterGroup.mNode,mi_segmentAttachStart.mNode)
    mc.parent(ml_segmentHandles[-1].masterGroup.mNode,mi_segmentAttachEnd.mNode)
    
    mi_segmentAnchorStart.parent = self._i_deformNull.mNode
    mc.parentConstraint(ml_anchorJoints[0].mNode,mi_segmentAnchorStart.mNode,maintainOffset=True)#constrain
    mc.scaleConstraint(ml_anchorJoints[0].mNode,mi_segmentAnchorStart.mNode,maintainOffset=True)#Constrain
    
    mi_segmentAnchorEnd.parent = self._i_deformNull.mNode
    mc.parentConstraint(ml_anchorJoints[-1].mNode,mi_segmentAnchorEnd.mNode,maintainOffset=True)
    mc.scaleConstraint(ml_anchorJoints[-1].mNode,mi_segmentAnchorEnd.mNode,maintainOffset=True)
    
    #method 1
    ml_rigJoints[0].parent = self._i_deformNull.mNode
    
    ml_rigJoints[-1].parent = ml_anchorJoints[-1].mNode
    
    ml_influenceJoints[0].parent = ml_segmentHandles[0].mNode
    ml_influenceJoints[-1].parent = ml_segmentHandles[-1].mNode
    
    #Parent anchors to controls
    ml_anchorJoints[0].parent = self._i_deformNull.mNode   
    #ml_anchorJoints[0].parent = ml_controlsFK[0].mNode
    ml_anchorJoints[-1].parent = mi_handleIK.mNode
        
    #Connect rig pelvis to anchor pelvis
    #mc.pointConstraint(ml_anchorJoints[0].mNode,ml_rigJoints[0].mNode,maintainOffset=False)
    #mc.orientConstraint(ml_anchorJoints[0].mNode,ml_rigJoints[0].mNode,maintainOffset=False)
    #mc.scaleConstraint(ml_anchorJoints[0].mNode,ml_rigJoints[0].mNode,maintainOffset=False)#Maybe hips    
    
    l_rigJoints = [i_jnt.mNode for i_jnt in ml_rigJoints]
    for i,i_jnt in enumerate(ml_segmentJoints[:-1]):
	#Don't try scale constraints in here, they're not viable
	attachJoint = distance.returnClosestObject(i_jnt.mNode,l_rigJoints)
	log.info("'%s'>>drives>>'%s'"%(i_jnt.getShortName(),attachJoint))
	pntConstBuffer = mc.pointConstraint(i_jnt.mNode,attachJoint,maintainOffset=False,weight=1)
	orConstBuffer = mc.orientConstraint(i_jnt.mNode,attachJoint,maintainOffset=False,weight=1)
	mc.connectAttr((i_jnt.mNode+'.s'),(attachJoint+'.s'))
    
    mc.pointConstraint(ml_anchorJoints[-1].mNode,ml_rigJoints[-1].mNode,maintainOffset=False)
    mc.orientConstraint(ml_anchorJoints[-1].mNode,ml_rigJoints[-1].mNode,maintainOffset=False)
    #mc.scaleConstraint(ml_anchorJoints[-1].mNode,ml_rigJoints[-2].mNode,maintainOffset=True)
    mc.connectAttr((ml_anchorJoints[-1].mNode+'.s'),(ml_rigJoints[-1].mNode+'.s'))
    
    #Set up heirarchy, connect master scale
    #====================================================================================
    #>>>Connect master scale
    cgmMeta.cgmAttr(mi_distanceBuffer,'masterScale',lock=True).doConnectIn("%s.%s"%(self._i_masterControl.mNode,'scaleY'))    
    
    #Vis Network, lock and hide
    #====================================================================================
    #Segment handles need to lock
    for i_obj in ml_segmentHandles:
	attributes.doSetLockHideKeyableAttr(i_obj.mNode,lock=True, visible=False, keyable=False, channels=['s%s'%orientation[1],'s%s'%orientation[2]])
    
    #Lock and hide hips and shoulders
    #attributes.doSetLockHideKeyableAttr(mi_handleIK.mNode,lock=True, visible=False, keyable=False, channels=['sx','sy','sz'])
     

    #Final stuff
    self._i_rigNull.version = str(__version__)
    
    return True 


@r9General.Timer
def __build__(self, buildTo='',*args,**kws): 
    try:
	if not self._cgmClass == 'RigFactory.go':
	    log.error("Not a RigFactory.go instance: '%s'"%self)
	    raise StandardError
    except StandardError,error:
	log.error("spine.build_deformationRig>>bad self!")
	raise StandardError,error
    
    if not self.isShaped():
	build_shapes(self)
    if buildTo.lower() == 'shapes':return True
    if not self.isRigSkeletonized():
	build_rigSkeleton(self)  
    if buildTo.lower() == 'skeleton':return True
    build_controls(self)    
    build_deformation(self)
    build_rig(self)    
    
    return True
