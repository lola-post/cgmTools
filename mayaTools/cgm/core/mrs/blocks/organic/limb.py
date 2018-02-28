"""
------------------------------------------
cgm.core.mrs.blocks.organic.limb
Author: Josh Burton
email: jjburton@cgmonks.com

Website : http://www.cgmonks.com
------------------------------------------

================================================================
"""
# From Python =============================================================
import copy
import re
import pprint
import time
import os

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# From Maya =============================================================
import maya.cmds as mc

# From Red9 =============================================================
from Red9.core import Red9_Meta as r9Meta
#r9Meta.cleanCache()#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< TEMP!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

import cgm.core.cgm_General as cgmGEN

from cgm.core.rigger import ModuleShapeCaster as mShapeCast

import cgm.core.cgmPy.os_Utils as cgmOS
import cgm.core.cgmPy.path_Utils as cgmPATH
import cgm.core.mrs.assets as MRSASSETS
path_assets = cgmPATH.Path(MRSASSETS.__file__).up().asFriendly()

import cgm.core.mrs.lib.ModuleControlFactory as MODULECONTROL
reload(MODULECONTROL)
import cgm.core.lib.math_utils as MATH
import cgm.core.lib.transform_utils as TRANS
import cgm.core.lib.distance_utils as DIST
import cgm.core.lib.attribute_utils as ATTR
import cgm.core.tools.lib.snap_calls as SNAPCALLS
import cgm.core.classes.NodeFactory as NODEFACTORY
from cgm.core import cgm_RigMeta as cgmRigMeta
import cgm.core.lib.list_utils as LISTS
import cgm.core.lib.nameTools as NAMETOOLS
reload(NAMETOOLS)
#Prerig handle making. refactor to blockUtils
import cgm.core.lib.snap_utils as SNAP
import cgm.core.lib.rayCaster as RAYS
import cgm.core.lib.rigging_utils as CORERIG
import cgm.core.lib.curve_Utils as CURVES
import cgm.core.rig.constraint_utils as RIGCONSTRAINT
import cgm.core.lib.constraint_utils as CONSTRAINT
import cgm.core.lib.position_utils as POS
import cgm.core.rig.joint_utils as JOINT
import cgm.core.rig.ik_utils as IK
import cgm.core.mrs.lib.block_utils as BLOCKUTILS
import cgm.core.mrs.lib.builder_utils as BUILDUTILS
import cgm.core.lib.shapeCaster as SHAPECASTER

import cgm.core.cgm_RigMeta as cgmRIGMETA
reload(CURVES)

# From cgm ==============================================================
from cgm.core import cgm_Meta as cgmMeta

#=============================================================================================================
#>> Block Settings
#=============================================================================================================
__version__ = 'alpha.02052018'
__autoTemplate__ = False
__dimensions = [15.2, 23.2, 19.7]#...cm
__menuVisible__ = True
__sizeMode__ = 'castNames'

#__baseSize__ = 1,1,10

__l_rigBuildOrder__ = ['rig_prechecks',
                       'rig_skeleton',
                       'rig_shapes',
                       'rig_controls',
                       'rig_frame',
                       'rig_segments',
                       'rig_cleanUp']


d_wiring_skeleton = {'msgLists':['moduleJoints','skinJoints']}
d_wiring_prerig = {'msgLinks':['moduleTarget','prerigNull','noTransPrerigNull'],
                   'msgLists':['prerigHandles']}
d_wiring_template = {'msgLinks':['templateNull','noTransTemplateNull','prerigLoftMesh','orientHelper'],
                     'msgLists':['templateHandles']}

#>>>Profiles =====================================================================================================
d_build_profiles = {
    'unityMobile':{'default':{'numRoll':1,
                              },
                   },
    'unityPC':{'default':{'numRoll':3,
                          },
               'spine':{'numRoll':4,
                       }},
    'feature':{'default':{'numRoll':5,
                          }}}

d_block_profiles = {
    'leg_bi':{'numShapers':5,
               'addCog':False,
               'cgmName':'leg',
               'loftShape':'square',
               'loftSetup':'default',
               'placeSettings':'end',
               'ikSetup':'rp',
               'ikBase':'none',
               'ikEnd':'foot',
               'side':'left',
               'numControls':3,
               'nameList':['hip','knee','ankle','ball','toe'],
               'baseAim':[0,-1,0],
               'baseUp':[0,0,1],
               'baseSize':[2,8,2]},
    
    'arm':{'numShapers':5,
           'addCog':False,
           'cgmName':'leg',
           'side':'left',
           'loftShape':'square',
           'loftSetup':'default',
           'placeSettings':'start',
           'ikSetup':'rp',
           'ikBase':'none',
           'ikEnd':'hand',
           'numControls':3,
           'nameList':['clav','shoulder','elbow','wrist'],
           'baseAim':[-1,0,0],
           'baseUp':[0,0,-1],
           'baseSize':[2,8,2]}    
   }

#>>>Attrs =====================================================================================================
l_attrsStandard = ['side',
                   'position',
                   'baseUp',
                   'baseAim',
                   'addCog',
                   'nameList',
                   #'namesHandles',
                   #'namesJoints',
                   'attachPoint',
                   'loftSides',
                   'loftDegree',
                   'loftSplit',
                   'loftShape',
                   'ikSetup',
                   'numControls',
                   'numShapers',#...with limb this is the sub shaper count as you must have one per handle
                   'buildProfile',
                   'moduleTarget']

d_attrsToMake = {'proxyShape':'cube:sphere:cylinder',
                 'loftSetup':'default:morpheus',
                 'placeSettings':'start:end',
                 'blockProfile':':'.join(d_block_profiles.keys()),
                 'ikEnd':'none:bank:foot:hand',
                 'numRoll':'int',
                 'ikBase':'none:fkRoot',#...fkRoot is our clav like setup
                 'hasBaseJoint':'bool',
                 'hasEndJoint':'bool',
                 'hasBallJoint':'bool',
                 #'nameIter':'string',
                 #'numControls':'int',
                 #'numShapers':'int',
                 #'numJoints':'int'
                 }

d_defaultSettings = {'version':__version__,
                     'baseSize':MATH.get_space_value(__dimensions[1]),
                     'numControls': 3,
                     'loftSetup':0,
                     'loftShape':0,
                     'numShapers':3,
                     'placeSettings':1,
                     'loftSides': 10,
                     'loftSplit':1,
                     'loftDegree':'cubic',
                     'numRoll':1,
                     'nameList':['',''],
                     'blockProfile':'leg_bi',
                     'attachPoint':'base',}


#d_preferredAngles = {'head':[0,-10, 10]}#In terms of aim up out for orientation relative values, stored left, if right, it will invert
#d_rotationOrders = {'head':'yxz'}


#=============================================================================================================
#>> Define
#=============================================================================================================
def define(self):
    _short = self.mNode
    ATTR.set_min(_short, 'numControls', 2)
    ATTR.set_min(_short, 'numRoll', 0)
    ATTR.set_min(_short, 'loftSides', 3)
    ATTR.set_min(_short, 'loftSplit', 1)
    ATTR.set_min(_short, 'numShapers', 1)
    
    
#=============================================================================================================
#>> Template
#=============================================================================================================    
#def templateDelete(self):
    #self.atUtils('delete_msgDat',msgLinks = ['noTemplateNull','templateLoftMesh'])
        
def template(self):
    _str_func = 'template'
    log.debug("|{0}| >>  {1}".format(_str_func,self)+ '-'*80)
    
    ATTR.datList_connect(self.mNode, 'rollCount', [self.numRoll for i in range(self.numControls - 1)])
    l_rollattrs = ATTR.datList_getAttrs(self.mNode,'rollCount')
    for a in l_rollattrs:
        ATTR.set_standardFlags(self.mNode, l_rollattrs, lock=False,visible=True,keyable=True)
    #Initial checks =====================================================================================
    _short = self.p_nameShort
    
    _side = 'center'
    if self.getMayaAttr('side'):
        _side = self.getEnumValueString('side')
        
    _l_basePosRaw = self.datList_get('basePos') or [(0,0,0)]
    _l_basePos = [self.p_position]
    _baseUp = self.baseUp
    _baseSize = self.baseSize
    _baseAim = self.baseAim
    _size_width = _baseSize[0]#...x width
    
    _ikSetup = self.getEnumValueString('ikSetup')
    _ikEnd = self.getEnumValueString('ikEnd')
    
    if self.baseAim == self.baseUp:
        raise ValueError,"baseAim and baseUp cannot be the same. baseAim: {0} | baseUp: {1}".format(self.baseAim,self.baseUp)
    
    _loftSetup = self.getEnumValueString('loftSetup')
            
    if _loftSetup not in ['default']:
        return log.error("|{0}| >> loft setup mode not done: {1}".format(_str_func,_loftSetup))    
    
    _mVectorAim = MATH.get_vector_of_two_points(_l_basePos[0],_l_basePos[-1],asEuclid=True)
    _mVectorUp = _mVectorAim.up()
    _worldUpVector = MATH.EUCLID.Vector3(self.baseUp[0],self.baseUp[1],self.baseUp[2])
    cgmGEN.func_snapShot(vars())
    
    #Create temple Null...
    mTemplateNull = self.atUtils('templateNull_verify')
    mNoTransformNull = self.atUtils('noTransformNull_verify','template')
    
    #Our main rigBlock shape ...
    mHandleFactory = self.asHandleFactory()
    
    #Generate more posData if necessary...
    if not len(_l_basePos)>1:
        log.debug("|{0}| >> Generating more pos dat".format(_str_func))
        _end = DIST.get_pos_by_vec_dist(_l_basePos[0], _baseAim, max(_baseSize))
        _l_basePos.append(_end)    
    
    
    #Root handles ===========================================================================================
    log.debug("|{0}| >> root handles...".format(_str_func)) 
    md_handles = {}
    ml_handles = []
    md_loftHandles = {}
    ml_loftHandles = []
    
    _loftShapeBase = self.getEnumValueString('loftShape')
    _loftShape = 'loft' + _loftShapeBase[0].capitalize() + ''.join(_loftShapeBase[1:])
    
    if _loftSetup == 'default':
        log.debug("|{0}| >> Default loft setup...".format(_str_func))
        
        for i,n in enumerate(['start','end']):
            log.debug("|{0}| >> {1}:{2}...".format(_str_func,i,n)) 
            mHandle = mHandleFactory.buildBaseShape('sphere', _size_width, shapeDirection = 'y+')
            mHandle.p_parent = mTemplateNull
            
            self.copyAttrTo('cgmName',mHandle.mNode,'cgmName',driven='target')
            mHandle.doStore('cgmType','blockHandle')
            mHandle.doStore('cgmNameModifier',n)
            mHandle.doName()
            
            #Convert to loft curve setup ----------------------------------------------------
            mHandleFactory.setHandle(mHandle.mNode)
            #mHandleFactory = self.asHandleFactory(mHandle.mNode)
            
            mLoftCurve = mHandleFactory.rebuildAsLoftTarget(_loftShape, _size_width, shapeDirection = 'z+',rebuildHandle = False)
            mc.makeIdentity(mHandle.mNode,a=True, s = True)#...must freeze scale once we're back parented and positioned
            
            
            mHandleFactory.color(mHandle.mNode)            
            mHandle.p_position = _l_basePos[i]
            
            md_handles[n] = mHandle
            ml_handles.append(mHandle)
            
            md_loftHandles[n] = mLoftCurve                
            ml_loftHandles.append(mLoftCurve)
            
            mBaseAttachGroup = mHandle.doGroup(True, asMeta=True,typeModifier = 'attach')
            
        #>> Base Orient Helper ==================================================================================================
        mHandleFactory = self.asHandleFactory(md_handles['start'].mNode)
    
        mBaseOrientCurve = mHandleFactory.addOrientHelper(baseSize = _size_width,
                                                          shapeDirection = 'y+',
                                                          setAttrs = {'ty':_size_width})
        #'tz':- _size_width})
    
        self.copyAttrTo('cgmName',mBaseOrientCurve.mNode,'cgmName',driven='target')
        mBaseOrientCurve.doName()
        
        mBaseOrientCurve.p_parent =  ml_handles[0]
        mOrientHelperAimGroup = mBaseOrientCurve.doGroup(True,asMeta=True,typeModifier = 'aim')        
    
        _const = mc.aimConstraint(ml_handles[1].mNode, mOrientHelperAimGroup.mNode, maintainOffset = False,
                                  aimVector = [0,0,1], upVector = [0,1,0], worldUpObject = ml_handles[0].mNode, #skip = 'z',
                                  worldUpType = 'vector', worldUpVector = [_worldUpVector.x,_worldUpVector.y,_worldUpVector.z])    
        
        self.connectChildNode(ml_handles[0].mNode,'orientHelper')
        cgmMeta.cgmNode(_const[0]).doConnectIn('worldUpVector','{0}.baseUp'.format(self.mNode))
        #mBaseOrientCurve.p_parent = mStartAimGroup
        
        mBaseOrientCurve.setAttrFlags(['ry','rx','translate','scale','v'])
        mHandleFactory.color(mBaseOrientCurve.mNode,controlType='sub')
        #CORERIG.colorControl(mBaseOrientCurve.mNode,_side,'sub')          
        mc.select(cl=True)
        
        if self.numControls > 2:
            log.debug("|{0}| >> more handles necessary...".format(_str_func)) 
            
            
            #Mid Track curve ============================================================================
            log.debug("|{0}| >> TrackCrv...".format(_str_func)) 
            _midTrackResult = CORERIG.create_at([mObj.mNode for mObj in ml_handles],'linearTrack',
                                                baseName='midTrack')
            
            _midTrackCurve = _midTrackResult[0]
            mMidTrackCurve = cgmMeta.validateObjArg(_midTrackCurve,'cgmObject')
            mMidTrackCurve.rename(self.cgmName + 'midHandlesTrack_crv')
            mMidTrackCurve.parent = mNoTransformNull
        
            #>>> mid main handles =====================================================================
            l_scales = []
            for mHandle in ml_handles:
                l_scales.append(mHandle.scale)
                mHandle.scale = 1,1,1
        
            _l_posMid = CURVES.returnSplitCurveList(mMidTrackCurve.mNode,self.numControls,markPoints = False)
            #_l_pos = [ DIST.get_pos_by_vec_dist(_pos_start, _vec, (_offsetDist * i)) for i in range(self.numControls-1)] + [_pos_end]
        
        
            #Sub handles... ------------------------------------------------------------------------------------
            log.debug("|{0}| >> Mid Handle creation...".format(_str_func))
            ml_aimGroups = []
            ml_midHandles = []
            ml_midLoftHandles = []
            for i,p in enumerate(_l_posMid[1:-1]):
                log.debug("|{0}| >> mid handle cnt: {1} | p: {2}".format(_str_func,i,p))
                crv = CURVES.create_fromName('sphere', _size_width, direction = 'y+')
                mHandle = cgmMeta.validateObjArg(crv, 'cgmObject', setClass=True)
                
                self.copyAttrTo('cgmName',mHandle.mNode,'cgmName',driven='target')
                mHandle.doStore('cgmType','blockHandle')
                mHandle.doStore('cgmNameModifier',"mid_{0}".format(i+1))
                mHandle.doName()                
                
                _short = mHandle.mNode
                ml_midHandles.append(mHandle)
                mHandle.p_position = p

                mHandle.p_parent = mTemplateNull
                
                mHandleFactory.setHandle(mHandle.mNode)
                mLoftCurve = mHandleFactory.rebuildAsLoftTarget(_loftShape,
                                                                _size_width,
                                                                shapeDirection = 'z+',rebuildHandle = False)
                mc.makeIdentity(mHandle.mNode,a=True, s = True)#...must freeze scale once we're back parented and positioned
                ml_midLoftHandles.append(mLoftCurve)
                
                mGroup = mHandle.doGroup(True,True,asMeta=True,typeModifier = 'master')
                
                _vList = DIST.get_normalizedWeightsByDistance(mGroup.mNode,
                                                              [ml_handles[0].mNode,ml_handles[-1].mNode])

                _scale = mc.scaleConstraint([ml_handles[0].mNode,ml_handles[-1].mNode],
                                            mGroup.mNode,maintainOffset = False)
        
                _res_attach = RIGCONSTRAINT.attach_toShape(mGroup.mNode, mMidTrackCurve.mNode, 'conPoint')
                TRANS.parent_set(_res_attach[0], mNoTransformNull.mNode)

                for c in [_scale]:
                    CONSTRAINT.set_weightsByDistance(c[0],_vList)
        
                mHandleFactory = self.asHandleFactory(mHandle.mNode)
        
                #Convert to loft curve setup ----------------------------------------------------
                #ml_jointHandles.append(mHandleFactory.addJointHelper(baseSize = _sizeSub))
        
                CORERIG.colorControl(mHandle.mNode,_side,'sub',transparent = True)
                
            #Push scale back...
            for i,mHandle in enumerate(ml_handles):
                mHandle.scale = l_scales[i]
            
            ml_handles_chain = [ml_handles[0]] + ml_midHandles + [ml_handles[-1]]
            
            #Main Track curve ============================================================================
            log.debug("|{0}| >> Main TrackCrv...".format(_str_func)) 
            _mainTrackResult = CORERIG.create_at([mObj.mNode for mObj in ml_handles_chain],'linearTrack',
                                                baseName='mainTrack')
        
            mMainTrackCurve = cgmMeta.validateObjArg(_mainTrackResult[0],'cgmObject')
            mMainTrackCurve.rename(self.cgmName + 'mainHandlesTrack_crv')
            mMainTrackCurve.parent = mNoTransformNull
            
            
        #>>> Aim Main loft curves ================================================================== 
        log.debug("|{0}| >> Aim main handles...".format(_str_func)) 
        
        
        for i,mHandle in enumerate(ml_handles_chain):
            mLoft = mHandle.loftCurve
            
            _aimBack = None
            _aimForward = None
            
            if mHandle == ml_handles_chain[0]:
                _aimForward = ml_handles_chain[i+1].mNode
            elif mHandle == ml_handles_chain[-1]:
                _aimBack = ml_handles_chain[-2].mNode
            else:
                _aimForward =  ml_handles_chain[i+1].mNode
                _aimBack  =  ml_handles_chain[i-1].mNode
                
            if _aimForward and _aimBack is None:
                mc.aimConstraint(_aimForward, mLoft.mNode, maintainOffset = False,
                                 aimVector = [0,0,1], upVector = [0,1,0], 
                                 worldUpObject = mBaseOrientCurve.mNode,
                                 worldUpType = 'objectrotation', 
                                 worldUpVector = [0,1,0])
            elif _aimBack and _aimForward is None:
                mc.aimConstraint(_aimBack, mLoft.mNode, maintainOffset = False,
                                 aimVector = [0,0,-1], upVector = [0,1,0], 
                                 worldUpObject = mBaseOrientCurve.mNode,
                                 worldUpType = 'objectrotation', 
                                 worldUpVector = [0,1,0])
            else:
                mAimForward = mLoft.doCreateAt()
                mAimForward.p_parent = mLoft.p_parent
                mAimForward.doStore('cgmName',mHandle.mNode)                
                mAimForward.doStore('cgmTypeModifier','forward')
                mAimForward.doStore('cgmType','aimer')
                mAimForward.doName()
                
                mAimBack = mLoft.doCreateAt()
                mAimBack.p_parent = mLoft.p_parent
                mAimBack.doStore('cgmName',mHandle.mNode)                                
                mAimBack.doStore('cgmTypeModifier','back')
                mAimBack.doStore('cgmType','aimer')
                mAimBack.doName()
                
                mc.aimConstraint(_aimForward, mAimForward.mNode, maintainOffset = False,
                                 aimVector = [0,0,1], upVector = [0,1,0], 
                                 worldUpObject = mBaseOrientCurve.mNode,
                                 worldUpType = 'objectrotation', 
                                 worldUpVector = [0,1,0])                
                mc.aimConstraint(_aimBack, mAimBack.mNode, maintainOffset = False,
                                 aimVector = [0,0,-1], upVector = [0,1,0], 
                                 worldUpObject = mBaseOrientCurve.mNode,
                                 worldUpType = 'objectrotation', 
                                 worldUpVector = [0,1,0])                
                
                const = mc.orientConstraint([mAimForward.mNode, mAimBack.mNode], mLoft.mNode, maintainOffset = False)[0]
                
                #...also aim our main handles...
                mHandleAimGroup = mHandle.doGroup(True,asMeta=True,typeModifier = 'aim')
                mc.aimConstraint(_aimForward, mHandleAimGroup.mNode, maintainOffset = False,
                                 aimVector = [0,-1,0], upVector = [0,0,1], 
                                 worldUpObject = mBaseOrientCurve.mNode,
                                 worldUpType = 'objectrotation', 
                                 worldUpVector = [0,1,0])                                
        
        #>>> Connections ==========================================================================================
        self.msgList_connect('templateHandles',[mObj.mNode for mObj in ml_handles_chain])

        #>>Loft Mesh =========================================================================================
        targets = [mObj.loftCurve.mNode for mObj in ml_handles_chain]        
    
        """
            return {'targets':targets,
                    'mPrerigNull' : mTemplateNull,
                    'uAttr':'numControls',
                    'uAttr2':'loftSplit',
                    'polyType':'bezier',
                    'baseName':self.cgmName}"""
    
    
        self.atUtils('create_prerigLoftMesh',
                     targets,
                     mTemplateNull,
                     'numControls',                     
                     'loftSplit',
                     polyType='bezier',
                     baseName = self.cgmName )
        for t in targets:
            ATTR.set(t,'v',0)
        mNoTransformNull.v = False

        #Pivot setup======================================================================================
        if _ikSetup != 'none':
            if _ikEnd == 'bank':
                log.debug("|{0}| >> Bank setup".format(_str_func)) 
                mHandleFactory.setHandle(ml_handles_chain[-1].mNode)
                mHandleFactory.addPivotSetupHelper().p_parent = mTemplateNull
            elif _ikEnd == 'foot':
                log.debug("|{0}| >> foot setup".format(_str_func)) 
                mHandleFactory.setHandle(ml_handles_chain[-1].mNode)
                mFoot,mFootLoftTop = mHandleFactory.addFootHelper()
                
                mFoot.p_parent = mTemplateNull
                
                #Add names...
                #for n in 'ball','toe':
                #    ATTR.datList_append(self.mNode, )
                

        #>>> shaper handles =======================================================================
        return
    
        #>>> Aim loft curves ==========================================================================================        
        mStartLoft = md_loftHandles['start']
        mEndLoft = md_loftHandles['end']
        
        mStartAimGroup = mStartLoft.doGroup(True,asMeta=True,typeModifier = 'aim')
        mEndAimGroup = mEndLoft.doGroup(True,asMeta=True,typeModifier = 'aim')        
        
        #mc.aimConstraint(ml_handles[1].mNode, mStartAimGroup.mNode, maintainOffset = False,
        #                 aimVector = [0,1,0], upVector = [1,0,0], worldUpObject = ml_handles[0].mNode, #skip = 'z',
        #                 worldUpType = 'objectrotation', worldUpVector = [1,0,0])
        #mc.aimConstraint(ml_handles[0].mNode, mEndAimGroup.mNode, maintainOffset = False,
        #                 aimVector = [0,-1,0], upVector = [1,0,0], worldUpObject = ml_handles[-1].mNode,
        #                 worldUpType = 'objectrotation', worldUpVector = [1,0,0])             
        mc.aimConstraint(ml_handles[1].mNode, mStartAimGroup.mNode, maintainOffset = False,
                         aimVector = [0,0,1], upVector = [0,1,0], worldUpObject = mBaseOrientCurve.mNode,
                         worldUpType = 'objectrotation', worldUpVector = [0,1,0])             
        mc.aimConstraint(ml_handles[0].mNode, mEndAimGroup.mNode, maintainOffset = False,
                         aimVector = [0,0,-1], upVector = [0,1,0], worldUpObject = mBaseOrientCurve.mNode,
                         worldUpType = 'objectrotation', worldUpVector = [0,1,0])             
        

        #Sub handles=========================================================================================
        if self.numShapers > 2:
            log.debug("|{0}| >> Sub handles..".format(_str_func))
            
            mNoTransformNull = self.atUtils('noTransformNull_verify')
            
            mStartHandle = ml_handles[0]    
            mEndHandle = ml_handles[-1]    
            mOrientHelper = mStartHandle.orientHelper
        
            ml_handles = [mStartHandle]
            #ml_jointHandles = []        
        
            _size = MATH.average(mHandleFactory.get_axisBox_size(mStartHandle.mNode))
            #DIST.get_bb_size(mStartHandle.loftCurve.mNode,True)[0]
            _sizeSub = _size * .5    
            _vec_root_up = ml_handles[0].orientHelper.getAxisVector('y+')        
    

            _pos_start = mStartHandle.p_position
            _pos_end = mEndHandle.p_position 
            _vec = MATH.get_vector_of_two_points(_pos_start, _pos_end)
            _offsetDist = DIST.get_distance_between_points(_pos_start,_pos_end) / (self.numShapers - 1)
            _l_pos = [ DIST.get_pos_by_vec_dist(_pos_start, _vec, (_offsetDist * i)) for i in range(self.numShapers-1)] + [_pos_end]
        
            _mVectorAim = MATH.get_vector_of_two_points(_pos_start, _pos_end,asEuclid=True)
            _mVectorUp = _mVectorAim.up()
            _worldUpVector = [_mVectorUp.x,_mVectorUp.y,_mVectorUp.z]        
        
        
            #Linear track curve ----------------------------------------------------------------------
            _linearCurve = mc.curve(d=1,p=[_pos_start,_pos_end])
            mLinearCurve = cgmMeta.validateObjArg(_linearCurve,'cgmObject')
        
            l_clusters = []
            _l_clusterParents = [mStartHandle,mEndHandle]
            for i,cv in enumerate(mLinearCurve.getComponents('cv')):
                _res = mc.cluster(cv, n = 'test_{0}_{1}_cluster'.format(_l_clusterParents[i].p_nameBase,i))
                #_res = mc.cluster(cv)            
                #TRANS.parent_set( _res[1], _l_clusterParents[i].getMessage('loftCurve')[0])
                TRANS.parent_set(_res[1], mTemplateNull)
                mc.pointConstraint(_l_clusterParents[i].getMessage('loftCurve')[0],
                                   _res[1],maintainOffset=True)
                ATTR.set(_res[1],'v',False)                
                l_clusters.append(_res)
        
            pprint.pprint(l_clusters)
            
            mLinearCurve.parent = mNoTransformNull
            mLinearCurve.rename('template_trackCrv')
            
            #mLinearCurve.inheritsTransform = False      
        
        
            #Tmp loft mesh -------------------------------------------------------------------
            _l_targets = [mObj.loftCurve.mNode for mObj in [mStartHandle,mEndHandle]]
        
            _res_body = mc.loft(_l_targets, o = True, d = 3, po = 0 )
            _str_tmpMesh =_res_body[0]
        
            l_scales = []
        
            for mHandle in mStartHandle, mEndHandle:
                #ml_jointHandles.append(self.asHandleFactory(mHandle.mNode).addJointHelper(baseSize = _sizeSub,shapeDirection='z+'))
                l_scales.append(mHandle.scale)
                mHandle.scale = 1,1,1

            #Sub handles... ------------------------------------------------------------------------------------
            for i,p in enumerate(_l_pos[1:-1]):
                #mHandle = mHandleFactory.buildBaseShape('circle', _size, shapeDirection = 'y+')
                mHandle = cgmMeta.cgmObject(name = 'handle_{0}'.format(i))
                _short = mHandle.mNode
                ml_handles.append(mHandle)
                mHandle.p_position = p
                SNAP.aim_atPoint(_short,_l_pos[i+2],'z+', 'y+', mode='vector', vectorUp = _vec_root_up)
        
                #...Make our curve
                _d = RAYS.cast(_str_tmpMesh, _short, 'y+')
                pprint.pprint(_d)
                log.debug("|{0}| >> Casting {1} ...".format(_str_func,_short))
                #cgmGEN.log_info_dict(_d,j)
                _v = _d['uvs'][_str_tmpMesh][0][0]
                log.debug("|{0}| >> v: {1} ...".format(_str_func,_v))
        
                #>>For each v value, make a new curve -----------------------------------------------------------------        
                #duplicateCurve -ch 1 -rn 0 -local 0  "loftedSurface2.u[0.724977270271534]"
                _crv = mc.duplicateCurve("{0}.u[{1}]".format(_str_tmpMesh,_v), ch = 0, rn = 0, local = 0)
                log.debug("|{0}| >> created: {1} ...".format(_str_func,_crv))  
        
                CORERIG.shapeParent_in_place(_short, _crv, False)
        
                #self.copyAttrTo(_baseNameAttrs[1],mHandle.mNode,'cgmName',driven='target')
                self.copyAttrTo('cgmName',mHandle.mNode,'cgmName',driven='target')
        
                mHandle.doStore('cgmType','blockHandle')
                mHandle.doStore('cgmIterator',i+1)
                mHandle.doName()
        
                mHandle.p_parent = mTemplateNull
        
                mGroup = mHandle.doGroup(True,True,asMeta=True,typeModifier = 'master')
                mGroup.p_parent = mTemplateNull
                
                _vList = DIST.get_normalizedWeightsByDistance(mGroup.mNode,[mStartHandle.mNode,mEndHandle.mNode])
                #_point = mc.pointConstraint([mStartHandle.mNode,mEndHandle.mNode],mGroup.mNode,maintainOffset = True)#Point contraint loc to the object
                _scale = mc.scaleConstraint([mStartHandle.mNode,mEndHandle.mNode],mGroup.mNode,maintainOffset = False)#Point contraint loc to the object
                #reload(CURVES)
                #mLoc = mGroup.doLoc()
                #mLoc.parent = mNoTransformNull
                #mLoc.inheritsTransform = False
        
                #CURVES.attachObjToCurve(mLoc.mNode, mLinearCurve.mNode)
                reload(RIGCONSTRAINT)
                _res_attach = RIGCONSTRAINT.attach_toShape(mGroup.mNode, 
                                                           mLinearCurve.mNode,
                                                           'conPoint')
                TRANS.parent_set(_res_attach[0], mNoTransformNull.mNode)
                
                #print cgmGEN._str_hardBreak
                #pprint.pprint(_res_attach)
                #print cgmGEN._str_hardBreak
                
                
                #_point = mc.pointConstraint([mLoc.mNode],mGroup.mNode,maintainOffset = True)#Point contraint loc to the object
        
                for c in [_scale]:
                    CONSTRAINT.set_weightsByDistance(c[0],_vList)
        
                #Convert to loft curve setup ----------------------------------------------------
                mHandleFactory = self.asHandleFactory(mHandle.mNode)
        
                #mc.makeIdentity(mHandle.mNode,a=True, s = True)#...must freeze scale once we're back parented and positioned
        
                mHandleFactory.rebuildAsLoftTarget('self', _size, shapeDirection = 'z+')
                #ml_jointHandles.append(mHandleFactory.addJointHelper(baseSize = _sizeSub))
                #mRootCurve.setAttrFlags(['rotate','tx','tz'])
                #mc.transformLimits(mRootCurve.mNode,  tz = [-.25,.25], etz = [1,1], ty = [.1,1], ety = [1,0])
                #mTopLoftCurve = mRootCurve.loftCurve
        
                CORERIG.colorControl(mHandle.mNode,_side,'sub',transparent = True)        
                #LOC.create(position = p)
        
            ml_handles.append(mEndHandle)
            mc.delete(_res_body)
        
            #Push scale back...
            for i,mHandle in enumerate([mStartHandle, mEndHandle]):
                mHandle.scale = l_scales[i]
        
            #Template Loft Mesh -------------------------------------
            #mTemplateLoft = self.getMessage('templateLoftMesh',asMeta=True)[0]        
            #for s in mTemplateLoft.getShapes(asMeta=True):
                #s.overrideDisplayType = 1       
            
            
            #Aim the segment
            for i,mHandle in enumerate(ml_handles):
                if mHandle != ml_handles[0] and mHandle != ml_handles[-1]:
                #if i > 0 and i < len(ml_handles) - 1:
                    mAimGroup = mHandle.doGroup(True,asMeta=True,typeModifier = 'aim')

                    mc.aimConstraint(ml_handles[-1].mNode, mAimGroup.mNode, maintainOffset = True, #skip = 'z',
                                     aimVector = [0,0,1], upVector = [0,1,0], worldUpObject = mBaseOrientCurve.mNode,
                                     worldUpType = 'objectrotation', worldUpVector = [0,1,0])             
        
                                     
            mLoftCurve = mHandle.loftCurve
        
        
            #>>Loft Mesh ==================================================================================================
            targets = [mObj.loftCurve.mNode for mObj in ml_handles]        
        
            self.atUtils('create_prerigLoftMesh',
                         targets,
                         mTemplateNull,
                         'numControls',                     
                         'loftSplit',
                         polyType='bezier',
                         baseName = self.cgmName )
        
            """
                BLOCKUTILS.create_prerigLoftMesh(self,targets,
                                                 mPrerigNull,
                                                 'loftSplit',
                                                 'neckControls',
                                                 polyType='nurbs',
                                                 baseName = _l_baseNames[1] )     
                """
            for t in targets:
                ATTR.set(t,'v',0)
            mNoTransformNull.v = False

        else:
            self.atUtils('create_templateLoftMesh',targets,self,
                         mTemplateNull,'numControls',
                         baseName = self.cgmName)            
        #>>> Connections ==========================================================================================
        self.msgList_connect('templateHandles',[mObj.mNode for mObj in ml_handles])

    #>>Loft Mesh ==================================================================================================
    targets = [mObj.mNode for mObj in ml_loftHandles]
    
    

    
    
    """
    BLOCKUTILS.create_templateLoftMesh(self,targets,mBaseLoftCurve,
                                       mTemplateNull,'numControls',
                                       baseName = _l_baseNames[1])"""

    

    return True


#=============================================================================================================
#>> Prerig
#=============================================================================================================
def prerig(self):
    try:
        _str_func = 'prerig'
        _short = self.p_nameShort
        _side = self.atUtils('get_side')
        log.debug("|{0}| >>  {1}".format(_str_func,self)+ '-'*80)
        
        self.atUtils('module_verify')
        
        log.debug("|{0}| >> [{1}] | side: {2}".format(_str_func,_short, _side))   
        
        #Create some nulls Null  ==================================================================================
        mPrerigNull = self.atUtils('prerigNull_verify')
        mNoTransformNull = self.atUtils('noTransformNull_verify','prerig')
        
        #mNoTransformNull = BLOCKUTILS.noTransformNull_verify(self)
    
        #> Get our stored dat ==================================================================================================
        mHandleFactory = self.asHandleFactory()
        
        _ikSetup = self.getEnumValueString('ikSetup')
        _ikEnd = self.getEnumValueString('ikEnd')

        
        ml_templateHandles = self.msgList_get('templateHandles')
        
        #...cog -----------------------------------------------------------------------------
        if self.addCog:
            self.asHandleFactory(ml_templateHandles[0]).addCogHelper().p_parent = mPrerigNull
        
        mStartHandle = ml_templateHandles[0]    
        mEndHandle = ml_templateHandles[-1]    
        mOrientHelper = mStartHandle.orientHelper
        
        ml_handles = []
        ml_jointHandles = []        
    
        _size = MATH.average(mHandleFactory.get_axisBox_size(mStartHandle.mNode))
        #DIST.get_bb_size(mStartHandle.loftCurve.mNode,True)[0]
        _sizeSub = _size * .33    
        _vec_root_up = ml_templateHandles[0].orientHelper.getAxisVector('y+')
        
        
        #Initial logic=========================================================================================
        log.debug("|{0}| >> Initial Logic...".format(_str_func)) 
        
        _pos_start = mStartHandle.p_position
        _pos_end = mEndHandle.p_position 
        _vec = MATH.get_vector_of_two_points(_pos_start, _pos_end)
        
        _mVectorAim = MATH.get_vector_of_two_points(_pos_start, _pos_end,asEuclid=True)
        _mVectorUp = _mVectorAim.up()
        _worldUpVector = [_mVectorUp.x,_mVectorUp.y,_mVectorUp.z]
        
        #Foot helper ============================================================================
        mFootHelper = False
        if ml_templateHandles[-1].getMessage('pivotHelper'):
            log.debug("|{0}| >> footHelper".format(_str_func))
            mFootHelper = ml_templateHandles[-1].pivotHelper
    
        if self.hasBallJoint and mFootHelper:
            ml_templateHandles.append(mFootHelper.pivotCenter)
        if self.hasEndJoint and mFootHelper:
            ml_templateHandles.append(mFootHelper.pivotFront)

        #Sub handles... ------------------------------------------------------------------------------------
        log.debug("|{0}| >> PreRig Handle creation...".format(_str_func))
        ml_aimGroups = []
        for i,mTemplateHandle in enumerate(ml_templateHandles):
            log.debug("|{0}| >> prerig handle cnt: {1}".format(_str_func,i))
            _sizeUse = MATH.average(mHandleFactory.get_axisBox_size(mTemplateHandle.mNode)) * .33
            
            try: _HandleSnapTo = mTemplateHandle.loftCurve.mNode
            except: _HandleSnapTo = mTemplateHandle.mNode
            
            crv = CURVES.create_fromName('cubeOpen', size = _sizeUse)
            mHandle = cgmMeta.validateObjArg(crv, 'cgmObject', setClass=True)
            _short = mHandle.mNode
            ml_handles.append(mHandle)
            
            mHandle.doSnapTo(_HandleSnapTo)
            mHandle.p_parent = mPrerigNull
            mGroup = mHandle.doGroup(True,True,asMeta=True,typeModifier = 'master')
            ml_aimGroups.append(mGroup)
            
            mc.parentConstraint(_HandleSnapTo, mGroup.mNode, maintainOffset=True)
            
            mHandleFactory = self.asHandleFactory(mHandle.mNode)
            
            #Convert to loft curve setup ----------------------------------------------------
            ml_jointHandles.append(mHandleFactory.addJointHelper(baseSize = _sizeSub))
            CORERIG.colorControl(mHandle.mNode,_side,'sub',transparent = True)
        
        
        
        self.msgList_connect('prerigHandles', ml_handles)
        
        ml_handles[0].connectChildNode(mOrientHelper.mNode,'orientHelper')      
        
        self.atUtils('prerigHandles_getNameDat',True)
        
                                 
        #Joint placer loft....
        targets = [mObj.jointHelper.loftCurve.mNode for mObj in ml_handles]
        
        
        self.msgList_connect('jointHelpers',targets)
        
        self.atUtils('create_jointLoft',
                     targets,
                     mPrerigNull,
                     baseCount = self.numRoll * self.numControls,
                     baseName = self.cgmName,
                     simpleMode = True)        
        
        """
        BLOCKUTILS.create_jointLoft(self,targets,
                                    mPrerigNull,'neckJoints',
                                    baseName = _l_baseNames[1] )
        """
        for t in targets:
            ATTR.set(t,'v',0)
            #ATTR.set_standardFlags(t,[v])
            
            
    
        
        #if self.addScalePivot:
            #mHandleFactory.addScalePivotHelper().p_parent = mPrerigNull        
        
        
        #Close out ==================================================================================================
        mNoTransformNull.v = False
        #cgmGEN.func_snapShot(vars())
        

            
        return True
    
    except Exception,err:cgmGEN.cgmException(Exception,err)
    
def prerigDelete(self):
    if self.getMessage('templateLoftMesh'):
        mTemplateLoft = self.getMessage('templateLoftMesh',asMeta=True)[0]
        for s in mTemplateLoft.getShapes(asMeta=True):
            s.overrideDisplayType = 2
        mTemplateLoft.v = True
        
def skeleton_build(self, forceNew = True):
    _short = self.mNode
    _str_func = 'skeleton_build'
    log.debug("|{0}| >>  {1}".format(_str_func,self)+ '-'*80)
    
    ml_joints = []
    
    mPrerigNull = self.prerigNull
    
    mModule = self.moduleTarget
    if not mModule:
        raise ValueError,"No moduleTarget connected"
    mRigNull = mModule.rigNull
    if not mRigNull:
        raise ValueError,"No rigNull connected"
    
    ml_templateHandles = self.msgList_get('templateHandles',asMeta = True)
    if not ml_templateHandles:
        raise ValueError,"No templateHandles connected"
    
    ml_jointHelpers = self.msgList_get('jointHelpers',asMeta = True)
    if not ml_jointHelpers:
        raise ValueError,"No jointHelpers connected"
    
    #>> If skeletons there, delete ------------------------------------------------------------------- 
    _bfr = mRigNull.msgList_get('moduleJoints',asMeta=True)
    if _bfr:
        log.debug("|{0}| >> Joints detected...".format(_str_func))            
        if forceNew:
            log.debug("|{0}| >> force new...".format(_str_func))                            
            mc.delete([mObj.mNode for mObj in _bfr])
        else:
            return _bfr
    
    #_baseNameAttrs = ATTR.datList_getAttrs(self.mNode,'baseNames')
    
    
    _d_base = self.atBlockUtils('skeleton_getNameDictBase')
    _l_names = ATTR.datList_get(self.mNode,'nameList')
    
    _rollCounts = ATTR.datList_get(self.mNode,'rollCount')
    log.debug("|{0}| >> rollCount: {1}".format(_str_func,_rollCounts))
    _d_rollCounts = {i:v for i,v in enumerate(_rollCounts)}
    
    if len(_l_names) != len(ml_jointHelpers):
        return log.error("Namelist lengths and handle lengths doesn't match | len {0} != {1}".format(_l_names,
                                                                                                     len(
                                                                                                                  ml_jointHelpers)))
    
    _d_base['cgmType'] = 'skinJoint'
    
    #Build our handle chain ======================================================
    l_pos = []
    
    for mObj in ml_jointHelpers:
        l_pos.append(mObj.p_position)
            
    mOrientHelper = ml_templateHandles[0].orientHelper
    ml_handleJoints = JOINT.build_chain(l_pos, parent=True, worldUpAxis= mOrientHelper.getAxisVector('y+'))
    ml_joints = []
    d_rolls = {}
    

    for i,mJnt in enumerate(ml_handleJoints):
        d=copy.copy(_d_base)
        d['cgmName'] = _l_names[i]
        mJnt.rename(NAMETOOLS.returnCombinedNameFromDict(d))
        for t,v in d.iteritems():
            mJnt.doStore(t,v)
        ml_joints.append(mJnt)
        if mJnt != ml_handleJoints[-1]:
            if _d_rollCounts.get(i):
                log.debug("|{0}| >> {1} Rolljoints: {2}".format(_str_func,mJnt.mNode,_d_rollCounts.get(i)))
                _roll = _d_rollCounts.get(i)
                _p_start = l_pos[i]
                _p_end = l_pos[i+1]
                
                if _roll != 1:
                    _l_pos = BUILDUTILS.get_posList_fromStartEnd(_p_start,_p_end,_roll+2)[1:-1]
                else:
                    _l_pos = BUILDUTILS.get_posList_fromStartEnd(_p_start,_p_end,_roll)
                    
                log.debug("|{0}| >> {1}".format(_str_func,_l_pos))
                ml_rolls = []
                
                ml_handleJoints[i].select()
                
                for ii,p in enumerate(_l_pos):
                    mRoll = cgmMeta.validateObjArg( mc.joint (p=(p[0],p[1],p[2])))
                    dRoll=copy.copy(d)
                    
                    dRoll['cgmNameModifier'] = 'roll'
                    dRoll['cgmIterator'] = ii
                    
                    mRoll.rename(NAMETOOLS.returnCombinedNameFromDict(dRoll))
                    for t,v in dRoll.iteritems():
                        mRoll.doStore(t,v)                    
                    #mRoll.jointOrient = mJnt.jointOrient
                    mRoll.rotate = mJnt.rotate
                    ml_rolls.append(mRoll)
                    ml_joints.append(mRoll)
                d_rolls[i] = ml_rolls

    ml_joints[0].parent = False
    
    _radius = DIST.get_distance_between_points(ml_joints[0].p_position, ml_joints[-1].p_position)/ 10
    #MATH.get_space_value(5)
    
    for mJoint in ml_joints:
        mJoint.displayLocalAxis = 1
        mJoint.radius = _radius

    mRigNull.msgList_connect('moduleJoints', ml_joints)
    mPrerigNull.msgList_connect('handleJoints', ml_handleJoints)
    for i,l in d_rolls.iteritems():
        mPrerigNull.msgList_connect('rollJoints_{0}'.format(i), l)
        for mJnt in l:
            mJnt.radius = _radius / 2
    self.atBlockUtils('skeleton_connectToParent')
    
    if len(ml_handleJoints) > self.numControls:
        log.debug("|{0}| >> Extra joints, checking last handle".format(_str_func))
        mEnd = ml_handleJoints[self.numControls - 1]
        ml_children = mEnd.getChildren(asMeta=True)
        for mChild in ml_children:
            mChild.parent = False
            
            JOINT.orientChain(ml_handleJoints[self.numControls - 1:], worldUpAxis= ml_templateHandles[-1].pivotHelper.getAxisVector('y+') )
            
        mEnd.jointOrient = 0,0,0
        
        for mChild in ml_children:
            mChild.parent = mEnd
    
    return ml_joints


#=============================================================================================================
#>> rig
#=============================================================================================================
#NOTE - self here is a rig Factory....

#d_preferredAngles = {'default':[0,-10, 10]}#In terms of aim up out for orientation relative values, stored left, if right, it will invert
d_preferredAngles = {'out':10}
d_rotateOrders = {'default':'yxz'}

#Rig build stuff goes through the rig build factory ------------------------------------------------------
@cgmGEN.Timer
def rig_prechecks(self):
    _short = self.d_block['shortName']
    _str_func = 'rig_prechecks'
    log.debug("|{0}| >>  {1}".format(_str_func,self)+ '-'*80)
        
    mBlock = self.mBlock
    mRigNull = self.mRigNull
    mPrerigNull = mBlock.prerigNull
    ml_templateHandles = mBlock.msgList_get('templateHandles')
    ml_handleJoints = mPrerigNull.msgList_get('handleJoints')
    
    #Pivot checks ============================================================================
    mPivotHolderHandle = ml_templateHandles[-1]
    self.b_pivotSetup = False
    if mPivotHolderHandle.getMessage('pivotHelper'):
        log.debug("|{0}| >> Pivot setup needed".format(_str_func))
        self.b_pivotSetup = True
        
    #Roll joints =============================================================================
    #Look for roll chains...
    _check = 0
    self.md_roll = {}
    self.ml_roll = []
    self.b_segmentSetup = False
    self.b_rollSetup = False
    
    while _check <= len(ml_handleJoints):
        mBuffer = mPrerigNull.msgList_get('rollJoints_{0}'.format(_check))
        _len = len(mBuffer)
        if mBuffer:
            log.debug("|{0}| >> Roll joints found on seg: {1} | len: {2}".format(_str_func,_check,_len ))
            self.ml_roll.append(mBuffer)
            self.md_roll[_check] = mBuffer
            self.b_singleRoll = True
            if _len > 1:
                self.b_segmentSetup = True
            
        _check +=1
    log.debug("|{0}| >> Segment setup: {1}".format(_str_func,self.b_segmentSetup))            
    log.debug("|{0}| >> Roll setup: {1}".format(_str_func,self.b_rollSetup))
    
    #Frame Handles =============================================================================
    self.ml_handleTargets = mPrerigNull.msgList_get('handleJoints')
    self.mToe = False
    self.mBall = False
    self.int_handleEndIdx = -1
    l= []
    
    if mBlock.hasEndJoint:
        self.mToe = self.ml_handleTargets.pop(-1)
        log.debug("|{0}| >> mToe: {1}".format(_str_func,self.mToe))
        self.int_handleEndIdx -=1
    if mBlock.hasBallJoint:
        self.mBall = self.ml_handleTargets.pop(-1)
        log.debug("|{0}| >> mBall: {1}".format(_str_func,self.mBall))        
        self.int_handleEndIdx -=1
    
    log.debug("|{0}| >> Handles Targets: {1}".format(_str_func,self.ml_handleTargets))            
    log.debug("|{0}| >> End idx: {1} | {2}".format(_str_func,self.int_handleEndIdx,
                                                   ml_handleJoints[self.int_handleEndIdx]))            
    
    



@cgmGEN.Timer
def rig_skeleton(self):
    _short = self.d_block['shortName']
    _str_func = 'rig_skeleton'
    log.debug("|{0}| >>  {1}".format(_str_func,self)+ '-'*80)
        
    mBlock = self.mBlock
    mRigNull = self.mRigNull
    mPrerigNull = mBlock.prerigNull
    ml_jointsToConnect = []
    ml_jointsToHide = []
    ml_blendJoints = []
    ml_joints = mRigNull.msgList_get('moduleJoints')
    ml_handleJoints = mPrerigNull.msgList_get('handleJoints')
    self.d_joints['ml_moduleJoints'] = ml_joints
    str_ikBase = ATTR.get_enumValueString(mBlock.mNode,'ikBase')        
    
    reload(BLOCKUTILS)
    BLOCKUTILS.skeleton_pushSettings(ml_joints,self.d_orientation['str'],
                                     self.d_module['mirrorDirection'],
                                     d_rotateOrders, d_preferredAngles)
    
    
    log.info("|{0}| >> rig chain...".format(_str_func))              
    ml_rigJoints = BLOCKUTILS.skeleton_buildDuplicateChain(mBlock, ml_joints, None , self.mRigNull,'rigJoints',blockNames=False, cgmType = 'rigJoint', connectToSource = 'rig')
    #pprint.pprint(ml_rigJoints)
    
    
    #...fk chain -----------------------------------------------------------------------------------------------
    log.info("|{0}| >> fk_chain".format(_str_func))
    #ml_fkJoints = BLOCKUTILS.skeleton_buildHandleChain(mBlock,'fk','fkJoints')
    
    
    ml_fkJoints = BLOCKUTILS.skeleton_buildDuplicateChain(mBlock, ml_handleJoints, 'fk', self.mRigNull,'fkJoints',blockNames=False,cgmType = 'frame')
    
    #l_baseNameAttrs = ATTR.datList_getAttrs(mBlock.mNode,'baseNames')
    #We then need to name our core joints to pass forward:
    #mBlock.copyAttrTo(l_baseNameAttrs[0],ml_fkJoints[-1].mNode,'cgmName',driven='target')
    #mBlock.copyAttrTo(l_baseNameAttrs[1],ml_fkJoints[0].mNode,'cgmName',driven='target')
    

    #mBlock.copyAttrTo('cgmName',ml_fkJoints[0].mNode,'cgmName',driven='target')
    """
    if len(ml_fkJoints) > 2:
        for i,mJnt in enumerate(ml_fkJoints):
            mJnt.doStore('cgmIterator',i+1)
        #ml_fkJoints[0].doStore('cgmIterator','base')
    
    for mJnt in ml_fkJoints:
        mJnt.doName()
        """
    ml_jointsToHide.extend(ml_fkJoints)

    
    #...fk chain -----------------------------------------------------------------------------------------------
    if mBlock.ikSetup:
        log.info("|{0}| >> ikSetup on. Building blend and IK chains...".format(_str_func))  
        ml_blendJoints = BLOCKUTILS.skeleton_buildHandleChain(self.mBlock,'blend','blendJoints')
        ml_ikJoints = BLOCKUTILS.skeleton_buildHandleChain(self.mBlock,'ik','ikJoints')
        ml_jointsToConnect.extend(ml_ikJoints)
        ml_jointsToHide.extend(ml_blendJoints)
        
        BLOCKUTILS.skeleton_pushSettings(ml_ikJoints,self.d_orientation['str'],
                                         self.d_module['mirrorDirection'],
                                         d_rotateOrders, d_preferredAngles)        
        
    #cgmGEN.func_snapShot(vars())        
    """
    if mBlock.numControls > 1:
        log.info("|{0}| >> Handles...".format(_str_func))            
        ml_segmentHandles = BLOCKUTILS.skeleton_buildHandleChain(self.mBlock,'handle','handleJoints',clearType=True)
        if mBlock.ikSetup:
            for i,mJnt in enumerate(ml_segmentHandles):
                mJnt.parent = ml_blendJoints[i]
        else:
            for i,mJnt in enumerate(ml_segmentHandles):
                mJnt.parent = ml_fkJoints[i]
                """
    
    if mBlock.ikSetup in [2,3]:#...ribbon/spline
        log.info("|{0}| >> IK Drivers...".format(_str_func))            
        ml_ribbonIKDrivers = BLOCKUTILS.skeleton_buildDuplicateChain(mBlock,ml_ikJoints, None, mRigNull,'ribbonIKDrivers', cgmType = 'ribbonIKDriver', indices=[0,-1])
        for i,mJnt in enumerate(ml_ribbonIKDrivers):
            mJnt.parent = False
            
            mTar = ml_blendJoints[0]
            if i == 0:
                mTar = ml_blendJoints[0]
            else:
                mTar = ml_blendJoints[-1]
                
            mJnt.doCopyNameTagsFromObject(mTar.mNode,ignore=['cgmType'])
            mJnt.doName()
        
        ml_jointsToConnect.extend(ml_ribbonIKDrivers)
        
    
    if self.b_segmentSetup or self.b_singleRoll:
        log.info("|{0}| >> Handles...".format(_str_func))            
        ml_segmentHandles = BLOCKUTILS.skeleton_buildHandleChain(self.mBlock,'handle','handleJoints',clearType=True)
        if mBlock.ikSetup:
            for i,mJnt in enumerate(ml_segmentHandles):
                mJnt.parent = ml_blendJoints[i]
        else:
            for i,mJnt in enumerate(ml_segmentHandles):
                mJnt.parent = ml_fkJoints[i]        
        
        if self.b_segmentSetup:
            log.info("|{0}| >> segment necessary...".format(_str_func))
                
            ml_segmentChain = BLOCKUTILS.skeleton_buildDuplicateChain(mBlock,
                                                                      ml_joints, None, 
                                                                      mRigNull,'segmentJoints',
                                                                      connectToSource = 'seg',
                                                                      cgmType = 'segJnt')
            for i,mJnt in enumerate(ml_rigJoints):
                mJnt.parent = ml_segmentChain[i]
                mJnt.connectChildNode(ml_segmentChain[i],'driverJoint','sourceJoint')#Connect
                
            ml_jointsToHide.extend(ml_segmentChain)
            
        else:
            log.info("|{0}| >> rollSetup joints...".format(_str_func))
            
             
            for i,mBlend in enumerate(ml_blendJoints):
                ml_rolls = self.md_roll.get(i)
                
                if ml_rolls:
                    ml_segmentChain = BLOCKUTILS.skeleton_buildDuplicateChain(mBlock,
                                                                              ml_rolls,
                                                                              None, 
                                                                              False,
                                                                              connectToSource = 'seg',
                                                                              cgmType = 'segJnt')
                
                    ml_jointsToHide.extend(ml_segmentChain)
                    ml_segmentChain[0].p_parent = mBlend
                    
                    
                
                
            
            
        
    else:
        log.info("|{0}| >> Simple setup. Parenting rigJoints to blend...".format(_str_func))
        ml_rigParents = ml_fkJoints
        if ml_blendJoints:
            ml_rigParents = ml_blendJoints
        for i,mJnt in enumerate(ml_rigJoints):
            mJnt.parent = ml_blendJoints[i]
            
        """
        if str_ikBase == 'hips':
            log.info("|{0}| >> Simple setup. Need single handle.".format(_str_func))
            ml_segmentHandles = BLOCKUTILS.skeleton_buildDuplicateChain(mBlock,ml_fkJoints, 'handle', mRigNull,'handleJoints', cgmType = 'handle', indices=[1])"""
    
        
    #...joint hide -----------------------------------------------------------------------------------
    for mJnt in ml_jointsToHide:
        try:
            mJnt.drawStyle =2
        except:
            mJnt.radius = .00001
            
    #...connect... 
    self.fnc_connect_toRigGutsVis( ml_jointsToConnect )        
    
    cgmGEN.func_snapShot(vars())     
    return

@cgmGEN.Timer
def rig_shapes(self):
    try:
        _short = self.d_block['shortName']
        _str_func = 'rig_shapes'
        log.debug("|{0}| >>  {1}".format(_str_func,self)+ '-'*80)
        
        #_str_func = '[{0}] > rig_shapes'.format(_short)
        log.info("|{0}| >> ...".format(_str_func))  
        
        mBlock = self.mBlock
        mRigNull = self.mRigNull
        
        ml_templateHandles = mBlock.msgList_get('templateHandles')
        ml_prerigHandleTargets = self.mBlock.atBlockUtils('prerig_getHandleTargets')
        ml_fkJoints = self.mRigNull.msgList_get('fkJoints')
        ml_ikJoints = mRigNull.msgList_get('ikJoints',asMeta=True)
        ml_blendJoints = self.mRigNull.msgList_get('blendJoints')
        
        mIKEnd = ml_prerigHandleTargets[-1]
        ml_prerigHandles = mBlock.msgList_get('prerigHandles')
        
        _side = mBlock.atUtils('get_side')
        _short_module = self.mModule.mNode
        str_ikBase = ATTR.get_enumValueString(mBlock.mNode,'ikBase')
        
        mHandleFactory = mBlock.asHandleFactory()
        mOrientHelper = ml_prerigHandles[0].orientHelper
        
        #_size = 5
        #_size = MATH.average(mHandleFactory.get_axisBox_size(ml_prerigHandles[0].mNode))
        _jointOrientation = self.d_orientation['str']
        
        ml_joints = self.d_joints['ml_moduleJoints']
        
        #Our base size will be the average of the bounding box sans the largest
        _bbSize = TRANS.bbSize_get(mBlock.getMessage('prerigLoftMesh')[0],shapes=True)
        _bbSize.remove(max(_bbSize))
        _size = MATH.average(_bbSize)
        _offset = self.mPuppet.atUtils('get_shapeOffset')

        #Pivots =======================================================================================
        mPivotHolderHandle = ml_templateHandles[-1]
        mPivotHelper = False
        if mPivotHolderHandle.getMessage('pivotHelper'):
            mPivotHelper = mPivotHolderHandle.pivotHelper
            log.debug("|{0}| >> Pivot shapes...".format(_str_func))            
            mBlock.atBlockUtils('pivots_buildShapes', mPivotHolderHandle.pivotHelper, mRigNull)
        
        
        #Cog =============================================================================
        if mBlock.getMessage('cogHelper') and mBlock.getMayaAttr('addCog'):
            log.debug("|{0}| >> Cog...".format(_str_func))
            mCogHelper = mBlock.cogHelper
            
            mCog = mCogHelper.doCreateAt(setClass=True)
            CORERIG.shapeParent_in_place(mCog.mNode, mCogHelper.shapeHelper.mNode)
            
            mCog.doStore('cgmName','cog')
            mCog.doStore('cgmAlias','cog')            
            mCog.doName()
            
            self.mRigNull.connectChildNode(mCog,'rigRoot','rigNull')#Connect
            self.mRigNull.connectChildNode(mCog,'settings','rigNull')#Connect        
            
        
        else:#Root =============================================================================
            log.debug("|{0}| >> Root...".format(_str_func))
            
            mRootHandle = ml_prerigHandles[0]
            #mRoot = ml_joints[0].doCreateAt()
            mRoot = ml_joints[0].doCreateAt()
            
            _size_root =  MATH.average(mHandleFactory.get_axisBox_size(ml_templateHandles[0].mNode))
            mRootCrv = cgmMeta.validateObjArg(CURVES.create_fromName('sphere', _size_root * 1.5),'cgmObject',setClass=True)
            mRootCrv.doSnapTo(mRootHandle)
        
            #SNAP.go(mRootCrv.mNode, ml_joints[0].mNode,position=False)
        
            CORERIG.shapeParent_in_place(mRoot.mNode,mRootCrv.mNode, False)
        
            ATTR.copy_to(_short_module,'cgmName',mRoot.mNode,driven='target')
            mRoot.doStore('cgmTypeModifier','root')
            mRoot.doName()
            
            mHandleFactory.color(mRoot.mNode, controlType = 'sub')
            
            self.mRigNull.connectChildNode(mRoot,'rigRoot','rigNull')#Connect
        
        
            #Settings =============================================================================
            _placeSettings = mBlock.getEnumValueString('placeSettings')
            if _placeSettings == 'cog':
                log.warning("|{0}| >> Settings. Cog option but no cog found...".format(_str_func))
                _placeSettings = 'start'
            
            if _placeSettings is not 'cog':
                log.debug("|{0}| >> settings: {1}...".format(_str_func,_placeSettings))
                
                
                if ml_blendJoints:
                    ml_targets = ml_blendJoints
                else:
                    ml_targets = ml_fkJoints
                    
                if _placeSettings == 'start':
                    _mTar = ml_targets[0]                
                else:
                    _mTar = ml_targets[self.int_handleEndIdx]
                    
                
                mSettingsShape = cgmMeta.validateObjArg(CURVES.create_fromName('gear',_size * .4,'{0}+'.format(_jointOrientation[2])))
    
                mSettingsShape.doSnapTo(_mTar.mNode)
                
                mSettingsShape.p_position = _mTar.getPositionByAxisDistance(_jointOrientation[1]+'-', _size * .8)
                #SNAP.aim_atPoint(mSettingsShape,_mTar.p_position,aimAxis=_jointOrientation[1]+'-',
                #                 mode = 'vector',
                #                 vectorUp= _mTar.getAxisVector(_jointOrientation[1]+'+'))
                
                mSettings = _mTar.doCreateAt(setClass=True)
                mSettings.parent = _mTar
                CORERIG.shapeParent_in_place(mSettings.mNode,mSettingsShape.mNode,False)            
                
                ATTR.copy_to(_short_module,'cgmName',mSettings.mNode,driven='target')
    
                mSettings.doStore('cgmTypeModifier','settings')
                mSettings.doName()
                #CORERIG.colorControl(mSettings.mNode,_side,'sub')
                mHandleFactory.color(mSettings.mNode, controlType = 'sub')
            
                self.mRigNull.connectChildNode(mSettings,'settings','rigNull')#Connect        
            
        
        
        #Direct Controls =============================================================================
        log.debug("|{0}| >> direct...".format(_str_func))                
        ml_rigJoints = self.mRigNull.msgList_get('rigJoints')
        _size_direct = DIST.get_distance_between_targets([mObj.mNode for mObj in ml_rigJoints], average=True)        

        d_direct = {'size':_size_direct/4}
            
        ml_directShapes = self.atBuilderUtils('shapes_fromCast',
                                              ml_rigJoints,
                                              mode ='direct',**d_direct)
                                                                                                                                                                #offset = 3
    
        for i,mCrv in enumerate(ml_directShapes):
            mHandleFactory.color(mCrv.mNode, controlType = 'sub')
            CORERIG.shapeParent_in_place(ml_rigJoints[i].mNode,mCrv.mNode, False, replaceShapes=True)
    
        for mJnt in ml_rigJoints:
            try:
                mJnt.drawStyle =2
            except:
                mJnt.radius = .00001

        
        #Handles =============================================================================================    
        ml_handleJoints = self.mRigNull.msgList_get('handleJoints')
        if ml_handleJoints:
            log.debug("|{0}| >> Found Handle joints...".format(_str_func))
            
            ml_handleShapes = self.atBuilderUtils('shapes_fromCast',
                                                  targets = [mObj.mNode for mObj in self.ml_handleTargets],
                                                  mode = 'limbSegmentHandle')
            
            for i,mCrv in enumerate(ml_handleShapes):
                log.debug("|{0}| >> Shape: {1} | Handle: {2}".format(_str_func,mCrv.mNode,ml_handleJoints[i].mNode ))                
                mHandleFactory.color(mCrv.mNode, controlType = 'sub')            
                CORERIG.shapeParent_in_place(ml_handleJoints[i].mNode, 
                                             mCrv.mNode, False,
                                             replaceShapes=True)            
            
            
            """
            #l_uValues = MATH.get_splitValueList(.01,.99, len(ml_handleJoints))
            ml_handleShapes = self.atBuilderUtils('shapes_fromCast',
                                                  targets = [mObj.mNode for mObj in self.ml_handleTargets],
                                                  mode ='segmentHandle')
            
            #offset = 3
            if str_ikBase == 'hips':
                mHandleFactory.color(ml_handleShapes[1].mNode, controlType = 'sub')            
                CORERIG.shapeParent_in_place(ml_handleJoints[0].mNode, 
                                             ml_handleShapes[1].mNode, False,
                                             replaceShapes=True)
                for mObj in ml_handleShapes:
                    try:mObj.delete()
                    except:pass
            else:
                for i,mCrv in enumerate(ml_handleShapes):
                    log.debug("|{0}| >> Shape: {1} | Handle: {2}".format(_str_func,mCrv.mNode,ml_handleJoints[i].mNode ))                
                    mHandleFactory.color(mCrv.mNode, controlType = 'sub')            
                    CORERIG.shapeParent_in_place(ml_handleJoints[i].mNode, 
                                                 mCrv.mNode, False,
                                                 replaceShapes=True)
                #for mShape in ml_handleJoints[i].getShapes(asMeta=True):
                    #mShape.doName()"""
        
        #FK/Ik =============================================================================================    
        log.debug("|{0}| >> Frame shape cast...".format(_str_func))        
        ml_fkShapes = self.atBuilderUtils('shapes_fromCast',
                                          targets = [mObj.mNode for mObj in self.ml_handleTargets],
                                          mode = 'limbHandle')
        
        
        if self.mBall:
            _size_ball = DIST.get_distance_between_targets([self.mBall.mNode,
                                                            self.mBall.p_parent])
        
            crv = CURVES.create_controlCurve(self.mBall.mNode, shape='circle',
                                             direction = _jointOrientation[0]+'+',
                                             sizeMode = 'fixed',
                                             size = _size_ball * 1.25)
            ml_fkShapes.append(cgmMeta.validateObjArg(crv,'cgmObject'))
            
        if self.mToe:
            _size_ball = DIST.get_distance_between_targets([self.mToe.mNode,
                                                            self.mToe.p_parent])
    
            crv = CURVES.create_controlCurve(self.mToe.mNode, shape='circle',
                                             direction = _jointOrientation[0]+'+',
                                             sizeMode = 'fixed',
                                             size = _size_ball * 1.25)        
            ml_fkShapes.append(cgmMeta.validateObjArg(crv,'cgmObject'))
        
        

        log.debug("|{0}| >> FK...".format(_str_func))    
        for i,mCrv in enumerate(ml_fkShapes):
            mJnt = ml_fkJoints[i]
            #CORERIG.match_orientation(mCrv.mNode,mJnt.mNode)

            mHandleFactory.color(mCrv.mNode, controlType = 'main')        
            CORERIG.shapeParent_in_place(mJnt.mNode,mCrv.mNode, False, replaceShapes=True)

        #IK base ================================================================================
        if mBlock.ikSetup:
            
            log.debug("|{0}| >> ikHandle...".format(_str_func))
            
            if mPivotHelper:
                mIKCrv = mPivotHelper.doDuplicate(po=False)
                mIKCrv.parent = False
                mShape2 = False
                for mChild in mIKCrv.getChildren(asMeta=True):
                    if mChild.cgmName == 'topLoft':
                        mShape2 = mChild.doDuplicate(po=False)
                        DIST.offsetShape_byVector(mShape2.mNode,_offset,component='cv')
                        
                    mChild.delete()
                
                DIST.offsetShape_byVector(mIKCrv.mNode,_offset,component='cv')
                
                if mShape2:
                    CORERIG.shapeParent_in_place(mIKCrv.mNode, mShape2.mNode, False)
                
                
                TRANS.rotatePivot_set(mIKCrv.mNode,
                                      ml_fkJoints[self.int_handleEndIdx].p_position )                
                
            mHandleFactory.color(mIKCrv.mNode, controlType = 'main',transparent=True)
            mIKCrv.doCopyNameTagsFromObject(ml_fkJoints[self.int_handleEndIdx].mNode,ignore=['cgmType','cgmTypeModifier'])
            mIKCrv.doStore('cgmTypeModifier','ik')
            mIKCrv.doStore('cgmType','handle')
            mIKCrv.doName()
        
            #CORERIG.match_transform(mIKCrv.mNode,ml_ikJoints[-1].mNode)
            mHandleFactory.color(mIKCrv.mNode, controlType = 'main')        
        
            self.mRigNull.connectChildNode(mIKCrv,'controlIK','rigNull')#Connect            
            
            """
           #mIKCrvShape = ml_fkShapes[-1].doDuplicate(po=False)
            mIKCrv = ml_ikJoints[-1].doCreateAt(setClass=True)
            
            CORERIG.shapeParent_in_place(mIKCrv.mNode,ml_fkShapes[-1].mNode,False)
            
            mHandleFactory.color(mIKCrv.mNode, controlType = 'main',transparent=True)
            mIKCrv.doCopyNameTagsFromObject(ml_fkJoints[-1].mNode,ignore=['cgmType','cgmTypeModifier'])
            mIKCrv.doStore('cgmTypeModifier','ik')
            mIKCrv.doName()
            
            #CORERIG.match_transform(mIKCrv.mNode,ml_ikJoints[-1].mNode)
            mHandleFactory.color(mIKCrv.mNode, controlType = 'main')        
            
            self.mRigNull.connectChildNode(mIKCrv,'controlIK','rigNull')#Connect
            """
            
            #Knee...---------------------------------------------------------------------------------
            log.debug("|{0}| >> knee...".format(_str_func))
            mKnee = ml_templateHandles[1].doCreateAt(setClass=True)
            CORERIG.shapeParent_in_place(mKnee.mNode, ml_templateHandles[1].mNode)
            
            mKnee.doSnapTo(ml_ikJoints[1].mNode)
        
            mKnee.doCopyNameTagsFromObject(ml_fkJoints[1].mNode,ignore=['cgmType','cgmTypeModifier'])
            mKnee.doStore('cgmAlias','midIK')            
            mKnee.doName()
        
            self.mRigNull.connectChildNode(mKnee,'controlIKMid','rigNull')#Connect
        
        return
    except Exception,err:cgmGEN.cgmException(Exception,err)
    



@cgmGEN.Timer
def rig_controls(self):
    _short = self.d_block['shortName']
    _str_func = 'rig_controls'
    log.debug("|{0}| >>  {1}".format(_str_func,self)+ '-'*80)
    
    mBlock = self.mBlock
    mRigNull = self.mRigNull
    ml_controlsAll = []#we'll append to this list and connect them all at the end
    mRootParent = self.mDeformNull
    mSettings = mRigNull.settings
    
    b_cog = False
    if mBlock.getMessage('cogHelper'):
        b_cog = True
    str_ikBase = ATTR.get_enumValueString(mBlock.mNode,'ikBase')
        
    # Drivers ==============================================================================================
    log.debug("|{0}| >> Attr drivers...".format(_str_func))    
    if mBlock.ikSetup:
        log.debug("|{0}| >> Build IK drivers...".format(_str_func))
        mPlug_FKIK = cgmMeta.cgmAttr(mSettings.mNode,'FKIK',attrType='float',minValue=0,maxValue=1,lock=False,keyable=True)
    
    #>> vis Drivers ================================================================================================	
    mPlug_visSub = self.atBuilderUtils('build_visSub')
    
    if not b_cog:
        mPlug_visRoot = cgmMeta.cgmAttr(mSettings,'visRoot', value = True, attrType='bool', defaultValue = False,keyable = False,hidden = False)
    mPlug_visDirect = cgmMeta.cgmAttr(mSettings,'visDirect', value = True, attrType='bool', defaultValue = False,keyable = False,hidden = False)
    

    #Root ==============================================================================================
    log.debug("|{0}| >> Root...".format(_str_func))
    
    if not mRigNull.getMessage('rigRoot'):
        raise ValueError,"No rigRoot found"
    
    mRoot = mRigNull.rigRoot
    log.debug("|{0}| >> Found rigRoot : {1}".format(_str_func, mRoot))
    
    _d = MODULECONTROL.register(mRoot,
                                addDynParentGroup = True,
                                mirrorSide= self.d_module['mirrorDirection'],
                                mirrorAxis="translateX,rotateY,rotateZ",
                                makeAimable = True)
    
    mRoot = _d['mObj']
    mRoot.masterGroup.parent = mRootParent
    mRootParent = mRoot#Change parent going forward...
    ml_controlsAll.append(mRoot)
    
    if not b_cog:
        for mShape in mRoot.getShapes(asMeta=True):
            ATTR.connect(mPlug_visRoot.p_combinedShortName, "{0}.overrideVisibility".format(mShape.mNode))

    # Pivots ================================================================================================
    #if mMainHandle.getMessage('pivotHelper'):
        #log.info("|{0}| >> Pivot helper found".format(_str_func))
    for a in 'center','front','back','left','right':#This order matters
        str_a = 'pivot' + a.capitalize()
        if mRigNull.getMessage(str_a):
            log.info("|{0}| >> Found: {1}".format(_str_func,str_a))
            
            mPivot = mRigNull.getMessage(str_a,asMeta=True)[0]
            
            d_buffer = MODULECONTROL.register(mPivot,
                                              typeModifier='pivot',
                                              mirrorSide= self.d_module['mirrorDirection'],
                                              mirrorAxis="translateX,rotateY,rotateZ",
                                              makeAimable = False)
            
            mPivot = d_buffer['instance']
            for mShape in mPivot.getShapes(asMeta=True):
                ATTR.connect(mPlug_visSub.p_combinedShortName, "{0}.overrideVisibility".format(mShape.mNode))                
            ml_controlsAll.append(mPivot)

    #FK controls ==============================================================================================
    log.debug("|{0}| >> FK Controls...".format(_str_func))
    ml_fkJoints = self.mRigNull.msgList_get('fkJoints')
    
    if str_ikBase == 'hips':
        ml_fkJoints = ml_fkJoints[1:]
    
    ml_fkJoints[0].parent = mRoot
    ml_controlsAll.extend(ml_fkJoints)
    
    for i,mObj in enumerate(ml_fkJoints):
        d_buffer = MODULECONTROL.register(mObj,
                                          mirrorSide= self.d_module['mirrorDirection'],
                                          mirrorAxis="translateX,rotateY,rotateZ",
                                          makeAimable = True)

        mObj = d_buffer['instance']
        ATTR.set_hidden(mObj.mNode,'radius',True)
            
    
    #ControlIK ========================================================================================
    mControlIK = False
    if mRigNull.getMessage('controlIK'):
        mControlIK = mRigNull.controlIK
        log.debug("|{0}| >> Found controlIK : {1}".format(_str_func, mControlIK))
        
        _d = MODULECONTROL.register(mControlIK,
                                    addSpacePivots = 2,
                                    addDynParentGroup = True, addConstraintGroup=False,
                                    mirrorSide= self.d_module['mirrorDirection'],
                                    mirrorAxis="translateX,rotateY,rotateZ",
                                    makeAimable = True)
        
        mControlIK = _d['mObj']
        mControlIK.masterGroup.parent = mRootParent
        ml_controlsAll.append(mControlIK)
        
    mControlBaseIK = False
    if mRigNull.getMessage('controlIKBase'):
        mControlBaseIK = mRigNull.controlIKBase
        log.debug("|{0}| >> Found controlBaseIK : {1}".format(_str_func, mControlBaseIK))
        
        _d = MODULECONTROL.register(mControlBaseIK,
                                    addSpacePivots = 2,
                                    addDynParentGroup = True, addConstraintGroup=False,
                                    mirrorSide= self.d_module['mirrorDirection'],
                                    mirrorAxis="translateX,rotateY,rotateZ",
                                    makeAimable = True)
        
        mControlBaseIK = _d['mObj']
        mControlBaseIK.masterGroup.parent = mRootParent
        ml_controlsAll.append(mControlBaseIK)
        
        
    mControlMidIK = False
    if mRigNull.getMessage('controlIKMid'):
        mControlMidIK = mRigNull.controlIKMid
        log.debug("|{0}| >> Found controlIKMid : {1}".format(_str_func, mControlMidIK))
        
        _d = MODULECONTROL.register(mControlMidIK,
                                    addSpacePivots = 2,
                                    addDynParentGroup = True, addConstraintGroup=False,
                                    mirrorSide= self.d_module['mirrorDirection'],
                                    mirrorAxis="translateX,rotateY,rotateZ",
                                    makeAimable = True)
        
        mControlMidIK = _d['mObj']
        mControlMidIK.masterGroup.parent = mRootParent
        ml_controlsAll.append(mControlMidIK)    

    if not b_cog:#>> settings ========================================================================================
        log.info("|{0}| >> Settings : {1}".format(_str_func, mSettings))
        
        MODULECONTROL.register(mSettings)
    
        #ml_blendJoints = self.mRigNull.msgList_get('blendJoints')
        #if ml_blendJoints:
        #    mSettings.masterGroup.parent = ml_blendJoints[-1]
        #else:
        #    mSettings.masterGroup.parent = ml_fkJoints[-1]
    
    #>> handleJoints ========================================================================================
    ml_handleJoints = self.mRigNull.msgList_get('handleJoints')
    if ml_handleJoints:
        log.debug("|{0}| >> Found Handle Joints...".format(_str_func))
        
        ml_controlsAll.extend(ml_handleJoints)
        

        for i,mObj in enumerate(ml_handleJoints):
            d_buffer = MODULECONTROL.register(mObj,
                                              mirrorSide= self.d_module['mirrorDirection'],
                                              mirrorAxis="translateX,rotateY,rotateZ",
                                              makeAimable = False)
    
            mObj = d_buffer['instance']
            ATTR.set_hidden(mObj.mNode,'radius',True)
            
            for mShape in mObj.getShapes(asMeta=True):
                ATTR.connect(mPlug_visSub.p_combinedShortName, "{0}.overrideVisibility".format(mShape.mNode))
        
            
    #>> Direct Controls ========================================================================================
    log.debug("|{0}| >> Direct controls...".format(_str_func))
    
    ml_rigJoints = self.mRigNull.msgList_get('rigJoints')
    ml_controlsAll.extend(ml_rigJoints)
    
    for i,mObj in enumerate(ml_rigJoints):
        d_buffer = MODULECONTROL.register(mObj,
                                          typeModifier='direct',
                                          mirrorSide= self.d_module['mirrorDirection'],
                                          mirrorAxis="translateX,rotateY,rotateZ",
                                          makeAimable = False)

        mObj = d_buffer['instance']
        ATTR.set_hidden(mObj.mNode,'radius',True)        
        if mObj.hasAttr('cgmIterator'):
            ATTR.set_hidden(mObj.mNode,'cgmIterator',True)        
            
        for mShape in mObj.getShapes(asMeta=True):
            ATTR.connect(mPlug_visDirect.p_combinedShortName, "{0}.overrideVisibility".format(mShape.mNode))
                

    ml_controlsAll = self.atBuilderUtils('register_mirrorIndices', ml_controlsAll)
    mRigNull.msgList_connect('controlsAll',ml_controlsAll)
    mRigNull.moduleSet.extend(ml_controlsAll)
    
    return 


@cgmGEN.Timer
def rig_segments(self):
    _short = self.d_block['shortName']
    _str_func = 'rig_neckSegment'
    log.debug("|{0}| >>  {1}".format(_str_func,self)+ '-'*80)
    

    
    mBlock = self.mBlock
    mRigNull = self.mRigNull
    ml_rigJoints = mRigNull.msgList_get('rigJoints')
    ml_segJoints = mRigNull.msgList_get('segmentJoints')
    mModule = self.mModule
    mRoot = mRigNull.rigRoot
    mPrerigNull = mBlock.prerigNull

    mRootParent = self.mDeformNull
    ml_handleJoints = mRigNull.msgList_get('handleJoints')
    ml_prerigHandleJoints = mPrerigNull.msgList_get('handleJoints')
    _jointOrientation = self.d_orientation['str']
    
    if self.b_segmentSetup:
        raise NotImplementedError,'Not done here Josh'
    else:#Roll setup
        log.info("|{0}| >> Roll setup".format(_str_func))
        
        for i,mHandle in enumerate(ml_prerigHandleJoints):
            mHandle.rigJoint.masterGroup.parent = ml_handleJoints[i]
            
            ml_rolls = self.md_roll.get(i)
            if ml_rolls:
                mSeg = ml_rolls[0].getMessageAsMeta('segJoint')
                
                mc.pointConstraint([ml_handleJoints[i].mNode,ml_handleJoints[i+1].mNode], mSeg.mNode)
                mc.orientConstraint([ml_handleJoints[i].mNode,ml_handleJoints[i+1].mNode], 
                                    mSeg.mNode, skip = [_jointOrientation[1],_jointOrientation[2]])
                mc.scaleConstraint([ml_handleJoints[i].mNode,ml_handleJoints[i+1].mNode], mSeg.mNode)
                
                
                ml_rolls[0].rigJoint.masterGroup.parent = mSeg.mNode
    return
                
        
    
    
    
    
    
    if not ml_segJoints:
        log.info("|{0}| >> No segment joints. No segment setup necessary.".format(_str_func))
        return True
    
    
    #>> Ribbon setup ========================================================================================
    log.debug("|{0}| >> Ribbon setup...".format(_str_func))
    reload(IK)
    #mSurf = IK.ribbon([mObj.mNode for mObj in ml_rigJoints], baseName = mBlock.cgmName, connectBy='constraint', msgDriver='masterGroup', moduleInstance = mModule)
    mSurf = IK.ribbon([mObj.mNode for mObj in ml_segJoints],
                      baseName = mBlock.cgmName,
                      driverSetup='stable',
                      connectBy='constraint',
                      moduleInstance = mModule)
    """
    #Setup the aim along the chain -----------------------------------------------------------------------------
    for i,mJnt in enumerate(ml_rigJoints):
        mAimGroup = mJnt.doGroup(True,asMeta=True,typeModifier = 'aim')
        v_aim = [0,0,1]
        if mJnt == ml_rigJoints[-1]:
            s_aim = ml_rigJoints[-2].masterGroup.mNode
            v_aim = [0,0,-1]
        else:
            s_aim = ml_rigJoints[i+1].masterGroup.mNode
    
        mc.aimConstraint(s_aim, mAimGroup.mNode, maintainOffset = True, #skip = 'z',
                         aimVector = v_aim, upVector = [1,0,0], worldUpObject = mJnt.masterGroup.mNode,
                         worldUpType = 'objectrotation', worldUpVector = [1,0,0])    
    """
    mSkinCluster = cgmMeta.validateObjArg(mc.skinCluster ([mHandle.mNode for mHandle in ml_handleJoints],
                                                          mSurf.mNode,
                                                          tsb=True,
                                                          maximumInfluences = 2,
                                                          normalizeWeights = 1,dropoffRate=2.5),
                                          'cgmNode',
                                          setClass=True)

    mSkinCluster.doStore('cgmName', mSurf.mNode)
    mSkinCluster.doName()    
    
    cgmGEN.func_snapShot(vars())

    ml_segJoints[0].parent = mRoot

    
@cgmGEN.Timer
def rig_frame(self):
    try:
        _short = self.d_block['shortName']
        _str_func = 'rig_rigFrame'.format(_short)
        log.info("|{0}| >> ...".format(_str_func))  
        
        mBlock = self.mBlock
        mRigNull = self.mRigNull
        mRootParent = self.mDeformNull
        
        ml_rigJoints = mRigNull.msgList_get('rigJoints')
        ml_fkJoints = mRigNull.msgList_get('fkJoints')
        ml_handleJoints = mRigNull.msgList_get('handleJoints')
        ml_baseIKDrivers = mRigNull.msgList_get('baseIKDrivers')
        ml_blendJoints = mRigNull.msgList_get('blendJoints')
        ml_templateHandles = mBlock.msgList_get('templateHandles')
        mPlug_globalScale = self.d_module['mPlug_globalScale']
        mRoot = mRigNull.rigRoot
        
        b_cog = False
        if mBlock.getMessage('cogHelper'):
            b_cog = True
        str_ikBase = ATTR.get_enumValueString(mBlock.mNode,'ikBase')
        
        
        
        #Changing targets - these change based on how the setup rolls through
        #mIKHandleDriver = mIKControl#...this will change with pivot
        mIKControl = mRigNull.controlIK                
        mIKHandleDriver = mIKControl
        
        #Pivot Driver ========================================================================================
        mPivotHolderHandle = ml_templateHandles[-1]
        if mPivotHolderHandle.getMessage('pivotHelper'):
            log.info("|{0}| >> Pivot setup...".format(_str_func))
            
            mPivotResultDriver = mPivotHolderHandle.doCreateAt()
            mPivotResultDriver.addAttr('cgmName','pivotResult')
            mPivotResultDriver.addAttr('cgmType','driver')
            mPivotResultDriver.doName()
            
            mPivotResultDriver.addAttr('cgmAlias', 'PivotResult')
            mIKHandleDriver = mPivotResultDriver
            
            mRigNull.connectChildNode(mPivotResultDriver,'pivotResultDriver','rigNull')#Connect    
     
            mBlock.atBlockUtils('pivots_setup', mControl = mIKControl, 
                                mRigNull = mRigNull, 
                                pivotResult = mPivotResultDriver,
                                rollSetup = 'default',
                                front = 'front', back = 'back')#front, back to clear the toe, heel defaults
        

        
        """
        #>> handleJoints ========================================================================================
        if ml_handleJoints:
            log.debug("|{0}| >> Handles setup...".format(_str_func))
            
            ml_handleParents = ml_fkJoints
            if ml_blendJoints:
                log.debug("|{0}| >> Handles parent: blend".format(_str_func))
                ml_handleParents = ml_blendJoints            
            
            if str_ikBase == 'hips':
                log.debug("|{0}| >> hips setup...".format(_str_func))
                
                ml_ribbonIkHandles = mRigNull.msgList_get('ribbonIKDrivers')
                if not ml_ribbonIkHandles:
                    raise ValueError,"No ribbon IKDriversFound"
                
                reload(RIGCONSTRAINT)
                RIGCONSTRAINT.build_aimSequence(ml_handleJoints,
                                                ml_ribbonIkHandles,
                                                [mRigNull.controlIKBase.mNode],#ml_handleParents,
                                                mode = 'singleBlend',
                                                upMode = 'objectRotation')
                
                mHipHandle = ml_handleJoints[0]
                mHipHandle.masterGroup.p_parent = mRoot
                mc.pointConstraint(mRigNull.controlIKBase.mNode,
                                   mHipHandle.masterGroup.mNode,
                                   maintainOffset = True)
                
            else:

                for i,mHandle in enumerate(ml_handleJoints):
                    mHandle.masterGroup.parent = ml_handleParents[i]
                    s_rootTarget = False
                    s_targetForward = False
                    s_targetBack = False
                    mMasterGroup = mHandle.masterGroup
                    b_first = False
                    if mHandle == ml_handleJoints[0]:
                        log.debug("|{0}| >> First handle: {1}".format(_str_func,mHandle))
                        if len(ml_handleJoints) <=2:
                            s_targetForward = ml_handleParents[-1].mNode
                        else:
                            s_targetForward = ml_handleJoints[i+1].getMessage('masterGroup')[0]
                        s_rootTarget = mRoot.mNode
                        b_first = True
                        
                    elif mHandle == ml_handleJoints[-1]:
                        log.debug("|{0}| >> Last handle: {1}".format(_str_func,mHandle))
                        s_rootTarget = ml_handleParents[i].mNode                
                        s_targetBack = ml_handleJoints[i-1].getMessage('masterGroup')[0]
                    else:
                        log.debug("|{0}| >> Reg handle: {1}".format(_str_func,mHandle))            
                        s_targetForward = ml_handleJoints[i+1].getMessage('masterGroup')[0]
                        s_targetBack = ml_handleJoints[i-1].getMessage('masterGroup')[0]
                        
                    #Decompose matrix for parent...
                    mUpDecomp = cgmMeta.cgmNode(nodeType = 'decomposeMatrix')
                    mUpDecomp.doStore('cgmName',ml_handleParents[i].mNode)                
                    mUpDecomp.addAttr('cgmType','aimMatrix',attrType='string',lock=True)
                    mUpDecomp.doName()
                    
                    ATTR.connect("%s.worldMatrix"%(ml_handleParents[i].mNode),"%s.%s"%(mUpDecomp.mNode,'inputMatrix'))
                    
                    if s_targetForward:
                        mAimForward = mHandle.doCreateAt()
                        mAimForward.parent = mMasterGroup            
                        mAimForward.doStore('cgmTypeModifier','forward')
                        mAimForward.doStore('cgmType','aimer')
                        mAimForward.doName()
                        
                        _const=mc.aimConstraint(s_targetForward, mAimForward.mNode, maintainOffset = True, #skip = 'z',
                                                aimVector = [0,0,1], upVector = [1,0,0], worldUpObject = ml_handleParents[i].mNode,
                                                worldUpType = 'vector', worldUpVector = [0,0,0])            
                        s_targetForward = mAimForward.mNode
                        ATTR.connect("%s.%s"%(mUpDecomp.mNode,"outputRotate"),"%s.%s"%(_const[0],"upVector"))                 
                        
                    else:
                        s_targetForward = ml_handleParents[i].mNode
                        
                    if s_targetBack:
                        mAimBack = mHandle.doCreateAt()
                        mAimBack.parent = mMasterGroup                        
                        mAimBack.doStore('cgmTypeModifier','back')
                        mAimBack.doStore('cgmType','aimer')
                        mAimBack.doName()
                        
                        _const = mc.aimConstraint(s_targetBack, mAimBack.mNode, maintainOffset = True, #skip = 'z',
                                                  aimVector = [0,0,-1], upVector = [1,0,0], worldUpObject = ml_handleParents[i].mNode,
                                                  worldUpType = 'vector', worldUpVector = [0,0,0])  
                        s_targetBack = mAimBack.mNode
                        ATTR.connect("%s.%s"%(mUpDecomp.mNode,"outputRotate"),"%s.%s"%(_const[0],"upVector"))                                     
                    else:
                        s_targetBack = s_rootTarget
                        #ml_handleParents[i].mNode
                    
                    pprint.pprint([s_targetForward,s_targetBack])
                    mAimGroup = mHandle.doGroup(True,asMeta=True,typeModifier = 'aim')
                    
                    mHandle.parent = False
                    
                    if b_first:
                        const = mc.orientConstraint([s_targetBack, s_targetForward], mAimGroup.mNode, maintainOffset = True)[0]
                    else:
                        const = mc.orientConstraint([s_targetForward, s_targetBack], mAimGroup.mNode, maintainOffset = True)[0]
                        
        
                    d_blendReturn = NODEFACTORY.createSingleBlendNetwork([mHandle.mNode,'followRoot'],
                                                                         [mHandle.mNode,'resultRootFollow'],
                                                                         [mHandle.mNode,'resultAimFollow'],
                                                                         keyable=True)
                    targetWeights = mc.orientConstraint(const,q=True, weightAliasList=True,maintainOffset=True)
                    
                    #Connect                                  
                    d_blendReturn['d_result1']['mi_plug'].doConnectOut('%s.%s' % (const,targetWeights[0]))
                    d_blendReturn['d_result2']['mi_plug'].doConnectOut('%s.%s' % (const,targetWeights[1]))
                    d_blendReturn['d_result1']['mi_plug'].p_hidden = True
                    d_blendReturn['d_result2']['mi_plug'].p_hidden = True
                    
                    mHandle.parent = mAimGroup#...parent back
                    
                    if mHandle in [ml_handleJoints[0],ml_handleJoints[-1]]:
                        mHandle.followRoot = 1
                    else:
                        mHandle.followRoot = .5"""
                        

        #>> Build IK ======================================================================================
        if mBlock.ikSetup:
            _ikSetup = mBlock.getEnumValueString('ikSetup')
            log.debug("|{0}| >> IK Type: {1}".format(_str_func,_ikSetup))    
        
            if not mRigNull.getMessage('rigRoot'):
                raise ValueError,"No rigRoot found"
            if not mRigNull.getMessage('controlIK'):
                raise ValueError,"No controlIK found"            
            
            mIKControl = mRigNull.controlIK
            mSettings = mRigNull.settings
            ml_ikJoints = mRigNull.msgList_get('ikJoints')
            mPlug_FKIK = cgmMeta.cgmAttr(mSettings.mNode,'FKIK',attrType='float',lock=False,keyable=True)
            _jointOrientation = self.d_orientation['str']
            
            mStart = ml_ikJoints[0]
            mEnd = ml_ikJoints[self.int_handleEndIdx]
            _start = ml_ikJoints[0].mNode
            _end = ml_ikJoints[self.int_handleEndIdx].mNode            
            
            #>>> Setup a vis blend result
            mPlug_FKon = cgmMeta.cgmAttr(mSettings,'result_FKon',attrType='float',defaultValue = 0,keyable = False,lock=True,hidden=True)	
            mPlug_IKon = cgmMeta.cgmAttr(mSettings,'result_IKon',attrType='float',defaultValue = 0,keyable = False,lock=True,hidden=True)	
        
            NODEFACTORY.createSingleBlendNetwork(mPlug_FKIK.p_combinedName,
                                                 mPlug_IKon.p_combinedName,
                                                 mPlug_FKon.p_combinedName)
            
            #IK...
            mIKGroup = mRoot.doCreateAt()
            mIKGroup.doStore('cgmTypeModifier','ik')
            mIKGroup.doName()
            
            mPlug_IKon.doConnectOut("{0}.visibility".format(mIKGroup.mNode))
            
            mIKGroup.parent = mRoot
            mIKControl.masterGroup.parent = mIKGroup
            
            """
            mIKBaseControl = False
            if mRigNull.getMessage('controlIKBase'):
                mIKBaseControl = mRigNull.controlIKBase
                
                if str_ikBase == 'hips':
                    mIKBaseControl.masterGroup.parent = mRoot
                else:
                    mIKBaseControl.masterGroup.parent = mIKGroup
                    
            else:#Spin Group
                #=========================================================================================
                log.debug("|{0}| >> spin setup...".format(_str_func))
            
                #Make a spin group
                mSpinGroup = mStart.doGroup(False,False,asMeta=True)
                mSpinGroup.doCopyNameTagsFromObject(self.mModule.mNode, ignore = ['cgmName','cgmType'])	
                mSpinGroup.addAttr('cgmName','{0}NoFlipSpin'.format(self.d_module['partName']))
                mSpinGroup.doName()
            
                mSpinGroup.parent = mRoot
            
                mSpinGroup.doGroup(True,True,typeModifier='zero')
            
                #Setup arg
                mPlug_spin = cgmMeta.cgmAttr(mIKControl,'spin',attrType='float',keyable=True, defaultValue = 0, hidden = False)
                mPlug_spin.doConnectOut("%s.r%s"%(mSpinGroup.mNode,_jointOrientation[0]))
                """
            
            if _ikSetup == 'rp':
                log.debug("|{0}| >> rp setup...".format(_str_func,_ikSetup))
                mIKMid = mRigNull.controlIKMid
                
                #Build the IK ---------------------------------------------------------------------
                _d_ik= {'globalScaleAttr':mPlug_globalScale.p_combinedName,
                        'stretch':'translate',
                        'lockMid':True,
                        'rpHandle':mIKMid.mNode,
                        'nameSuffix':'ik',
                        'controlObject':mIKControl.mNode,
                        'moduleInstance':self.mModule.mNode}
                
                d_ikReturn = IK.handle(_start,_end,**_d_ik)
                mIKHandle = d_ikReturn['mHandle']
                ml_distHandlesNF = d_ikReturn['ml_distHandles']
                mRPHandleNF = d_ikReturn['mRPHandle']
                
                """
                #Get our no flip position-------------------------------------------------------------------------
                log.debug("|{0}| >> no flip dat...".format(_str_func))
                
                _side = mBlock.atUtils('get_side')
                _dist_ik_noFlip = DIST.get_distance_between_points(mStart.p_position,
                                                                   mEnd.p_position)
                if _side == 'left':#if right, rotate the pivots
                    pos_noFlipOffset = mStart.getPositionByAxisDistance(_jointOrientation[2]+'-',_dist_ik_noFlip)
                else:
                    pos_noFlipOffset = mStart.getPositionByAxisDistance(_jointOrientation[2]+'+',_dist_ik_noFlip)
                
                #No flip -------------------------------------------------------------------------
                log.debug("|{0}| >> no flip setup...".format(_str_func))
                
                mIKHandle = d_ikReturn['mHandle']
                ml_distHandlesNF = d_ikReturn['ml_distHandles']
                mRPHandleNF = d_ikReturn['mRPHandle']
            
                #No Flip RP handle -------------------------------------------------------------------
                mRPHandleNF.p_position = pos_noFlipOffset
            
                mRPHandleNF.doCopyNameTagsFromObject(self.mModule.mNode, ignore = ['cgmName','cgmType'])
                mRPHandleNF.addAttr('cgmName','{0}PoleVector'.format(self.d_module['partName']), attrType = 'string')
                mRPHandleNF.addAttr('cgmTypeModifier','noFlip')
                mRPHandleNF.doName()
            
                if mIKBaseControl:
                    mRPHandleNF.parent = mIKBaseControl.mNode
                else:
                    mRPHandleNF.parent = mSpinGroup.mNode
                    """

                #>>>Parent IK handles -----------------------------------------------------------------
                log.debug("|{0}| >> parent ik dat...".format(_str_func,_ikSetup))
                
                mIKHandle.parent = mIKHandleDriver.mNode#handle to control	
                for mObj in ml_distHandlesNF[:-1]:
                    mObj.parent = mRoot
                ml_distHandlesNF[-1].parent = mIKHandleDriver.mNode#handle to control
                ml_distHandlesNF[1].parent = mIKMid
                
                #>>> Fix our ik_handle twist at the end of all of the parenting
                IK.handle_fixTwist(mIKHandle,_jointOrientation[0])#Fix the twist
                
                mc.orientConstraint([mIKControl.mNode], ml_ikJoints[-1].mNode, maintainOffset = True)
                
                #if mIKBaseControl:
                    #ml_ikJoints[0].parent = mRigNull.controlIKBase
                
                #if mIKBaseControl:
                    #mc.pointConstraint(mIKBaseControl.mNode, ml_ikJoints[0].mNode,maintainOffset=True)
                    
                    
                #Mid IK driver -----------------------------------------------------------------------
                log.info("|{0}| >> mid IK driver.".format(_str_func))
                mMidControlDriver = mIKMid.doCreateAt()
                mMidControlDriver.addAttr('cgmName','midIK')
                mMidControlDriver.addAttr('cgmType','driver')
                mMidControlDriver.doName()
            
                mMidControlDriver.addAttr('cgmAlias', 'midDriver')
                
                mc.pointConstraint([mRoot.mNode, mIKHandleDriver.mNode], mMidControlDriver.mNode)
                mMidControlDriver.parent = mRoot
                mIKMid.masterGroup.parent = mMidControlDriver
                    
            elif _ikSetup == 'spline':
                log.debug("|{0}| >> spline setup...".format(_str_func))
                ml_ribbonIkHandles = mRigNull.msgList_get('ribbonIKDrivers')
                if not ml_ribbonIkHandles:
                    raise ValueError,"No ribbon IKDriversFound"
            
                log.debug("|{0}| >> ribbon ik handles...".format(_str_func))
                
                if mIKBaseControl:
                    ml_ribbonIkHandles[0].parent = mIKBaseControl
                else:
                    ml_ribbonIkHandles[0].parent = mSpinGroup
                    
                ml_ribbonIkHandles[-1].parent = mIKControl
            
                mc.aimConstraint(mIKControl.mNode,
                                 ml_ribbonIkHandles[0].mNode,
                                 maintainOffset = True, weight = 1,
                                 aimVector = self.d_orientation['vectorAim'],
                                 upVector = self.d_orientation['vectorUp'],
                                 worldUpVector = self.d_orientation['vectorOut'],
                                 worldUpObject = mSpinGroup.mNode,
                                 worldUpType = 'objectRotation' )
            
                
                res_spline = IK.spline([mObj.mNode for mObj in ml_ikJoints],
                                       orientation = _jointOrientation,
                                       moduleInstance = self.mModule)
                mSplineCurve = res_spline['mSplineCurve']
                log.debug("|{0}| >> spline curve...".format(_str_func))
                

                #...ribbon skinCluster ---------------------------------------------------------------------
                log.debug("|{0}| >> ribbon skinCluster...".format(_str_func))                
                mSkinCluster = cgmMeta.validateObjArg(mc.skinCluster ([mHandle.mNode for mHandle in ml_ribbonIkHandles],
                                                                      mSplineCurve.mNode,
                                                                      tsb=True,
                                                                      maximumInfluences = 2,
                                                                      normalizeWeights = 1,dropoffRate=2.5),
                                                      'cgmNode',
                                                      setClass=True)
            
                mSkinCluster.doStore('cgmName', mSplineCurve.mNode)
                mSkinCluster.doName()    
                cgmGEN.func_snapShot(vars())
                
            elif _ikSetup == 'ribbon':
                log.debug("|{0}| >> ribbon setup...".format(_str_func))
                ml_ribbonIkHandles = mRigNull.msgList_get('ribbonIKDrivers')
                if not ml_ribbonIkHandles:
                    raise ValueError,"No ribbon IKDriversFound"
                
                
                
                log.debug("|{0}| >> ribbon ik handles...".format(_str_func))
                if mIKBaseControl:
                    ml_ribbonIkHandles[0].parent = mIKBaseControl
                else:
                    ml_ribbonIkHandles[0].parent = mSpinGroup
                    mc.aimConstraint(mIKControl.mNode,
                                     ml_ribbonIkHandles[0].mNode,
                                     maintainOffset = True, weight = 1,
                                     aimVector = self.d_orientation['vectorAim'],
                                     upVector = self.d_orientation['vectorUp'],
                                     worldUpVector = self.d_orientation['vectorOut'],
                                     worldUpObject = mSpinGroup.mNode,
                                     worldUpType = 'objectRotation' )                    
                
                ml_ribbonIkHandles[-1].parent = mIKControl
                
                reload(IK)
                mSurf = IK.ribbon([mObj.mNode for mObj in ml_ikJoints],
                                  baseName = self.d_module['partName'] + '_ikRibbon',
                                  driverSetup='stable',
                                  connectBy='constraint',
                                  moduleInstance = self.mModule)
                
                log.debug("|{0}| >> ribbon surface...".format(_str_func))
                """
                #Setup the aim along the chain -----------------------------------------------------------------------------
                for i,mJnt in enumerate(ml_ikJoints):
                    mAimGroup = mJnt.doGroup(True,asMeta=True,typeModifier = 'aim')
                    v_aim = [0,0,1]
                    if mJnt == ml_ikJoints[-1]:
                        s_aim = ml_ikJoints[-2].masterGroup.mNode
                        v_aim = [0,0,-1]
                    else:
                        s_aim = ml_ikJoints[i+1].masterGroup.mNode
            
                    mc.aimConstraint(s_aim, mAimGroup.mNode, maintainOffset = True, #skip = 'z',
                                     aimVector = v_aim, upVector = [1,0,0], worldUpObject = mJnt.masterGroup.mNode,
                                     worldUpType = 'objectrotation', worldUpVector = [1,0,0])    
                """
                #...ribbon skinCluster ---------------------------------------------------------------------
                log.debug("|{0}| >> ribbon skinCluster...".format(_str_func))
                ml_skinDrivers = ml_ribbonIkHandles
                max_influences = 2
                if str_ikBase == 'hips':
                    ml_skinDrivers.append(mHipHandle)
                    max_influences = 3
                mSkinCluster = cgmMeta.validateObjArg(mc.skinCluster ([mHandle.mNode for mHandle in ml_skinDrivers],
                                                                      mSurf.mNode,
                                                                      tsb=True,
                                                                      maximumInfluences = max_influences,
                                                                      normalizeWeights = 1,dropoffRate=10),
                                                      'cgmNode',
                                                      setClass=True)
            
                mSkinCluster.doStore('cgmName', mSurf.mNode)
                mSkinCluster.doName()    
                cgmGEN.func_snapShot(vars())
                
                
                
            else:
                raise ValueError,"Not implemented {0} ik setup".format(_ikSetup)
            
            
            
            #Parent --------------------------------------------------
            #Fk...
            #if str_ikBase == 'hips':
            #    mPlug_FKon.doConnectOut("{0}.visibility".format(ml_fkJoints[1].masterGroup.mNode))
            #    ml_fkJoints[0].p_parent = mIKBaseControl
            #else:
            mPlug_FKon.doConnectOut("{0}.visibility".format(ml_fkJoints[0].masterGroup.mNode))            
            ml_blendJoints[0].parent = mRoot
            ml_ikJoints[0].parent = mIKGroup


            
            #Setup blend ----------------------------------------------------------------------------------
            RIGCONSTRAINT.blendChainsBy(ml_fkJoints,ml_ikJoints,ml_blendJoints,
                                        driver = mPlug_FKIK.p_combinedName,l_constraints=['point','orient'])            
            
        
        
        
        cgmGEN.func_snapShot(vars())
        return    
    except Exception,err:cgmGEN.cgmException(Exception,err)

#@cgmGEN.Timer
def rig_matchSetup(self):
    try:
        _short = self.d_block['shortName']
        _str_func = 'rig_matchSetup'.format(_short)
        log.debug("|{0}| >> ...".format(_str_func))  
        
        mBlock = self.mBlock
        mRigNull = self.mRigNull
        mRootParent = self.mDeformNull
        mControlIK = mRigNull.controlIK
        mSettings = mRigNull.settings
        
        ml_rigJoints = mRigNull.msgList_get('rigJoints')
        ml_fkJoints = mRigNull.msgList_get('fkJoints')
        ml_blendJoints = mRigNull.msgList_get('blendJoints')
        ml_ikJoints = mRigNull.msgList_get('ikJoints')
        
        if not ml_ikJoints:
            return log.warning("|{0}| >> No Ik joints. Can't setup match".format(_str_func))
        
        len_fk = len(ml_fkJoints)
        len_ik = len(ml_ikJoints)
        len_blend = len(ml_blendJoints)
        
        if len_blend != len_ik and len_blend != len_fk:
            raise ValueError,"|{0}| >> All chains must equal length. fk:{1} | ik:{2} | blend:{2}".format(_str_func,len_fk,len_ik,len_blend)
        
        cgmGEN.func_snapShot(vars())
        
        mDynSwitch = mBlock.atRigModule('get_dynSwitch')
        _jointOrientation = self.d_orientation['str']
        
        
        
        #>>> FK to IK ==================================================================
        log.debug("|{0}| >> fk to ik...".format(_str_func))
        mMatch_FKtoIK = cgmRIGMETA.cgmDynamicMatch(dynObject=mControlIK,
                                                   dynPrefix = "FKtoIK",
                                                   dynMatchTargets = ml_blendJoints[-1])
        mMatch_FKtoIK.addPrematchData({'spin':0})
        
        
        
        
        
        #>>> IK to FK ==================================================================
        log.debug("|{0}| >> ik to fk...".format(_str_func))
        ml_fkMatchers = []
        for i,mObj in enumerate(ml_fkJoints):
            mMatcher = cgmRIGMETA.cgmDynamicMatch(dynObject=mObj,
                                                 dynPrefix = "IKtoFK",
                                                 dynMatchTargets = ml_blendJoints[i])        
            ml_fkMatchers.append(mMatcher)
            
        #>>> IK to FK ==================================================================
        log.debug("|{0}| >> Registration...".format(_str_func))
        
        mDynSwitch.addSwitch('snapToFK',"{0}.FKIK".format(mSettings.mNode),#[mSettings.mNode,'FKIK'],
                             0,
                             ml_fkMatchers)
        
        mDynSwitch.addSwitch('snapToIK',"{0}.FKIK".format(mSettings.mNode),#[mSettings.mNode,'FKIK'],
                             1,
                             [mMatch_FKtoIK])        
        
    except Exception,err:cgmGEN.cgmException(Exception,err)
    



def rig_cleanUp(self):
    _short = self.d_block['shortName']
    _str_func = 'rig_neckSegment'
    log.debug("|{0}| >>  {1}".format(_str_func,self)+ '-'*80)
    
    
    mRigNull = self.mRigNull
    mSettings = mRigNull.settings
    mRoot = mRigNull.rigRoot
    if not mRoot.hasAttr('cgmAlias'):
        mRoot.addAttr('cgmAlias','root')
        
    mRootParent = self.mDeformNull
    mMasterControl= self.d_module['mMasterControl']
    mMasterDeformGroup= self.d_module['mMasterDeformGroup']    
    mMasterNull = self.d_module['mMasterNull']
    mModuleParent = self.d_module['mModuleParent']
    mPlug_globalScale = self.d_module['mPlug_globalScale']
    
    ml_controlsToSetup = []
    for msgLink in ['rigJoints','controlIK']:
        ml_buffer = mRigNull.msgList_get(msgLink)
        if ml_buffer:
            log.debug("|{0}| >>  Found: {1}".format(_str_func,msgLink))            
            ml_controlsToSetup.extend(ml_buffer)
    
    #>>  DynParentGroups - Register parents for various controls ============================================
    ml_baseDynParents = []
    ml_endDynParents = [mRoot,mMasterNull.puppetSpaceObjectsGroup, mMasterNull.worldSpaceObjectsGroup]
    
    if mModuleParent:
        mi_parentRigNull = mModuleParent.rigNull
        if mi_parentRigNull.getMessage('rigRoot'):
            ml_baseDynParents.append( mi_parentRigNull.rigRoot )        
        if mi_parentRigNull.getMessage('controlIK'):
            ml_baseDynParents.append( mi_parentRigNull.controlIK )	    
        if mi_parentRigNull.getMessage('controlIKBase'):
            ml_baseDynParents.append( mi_parentRigNull.controlIKBase )
        ml_parentRigJoints =  mi_parentRigNull.msgList_get('rigJoints')
        if ml_parentRigJoints:
            ml_used = []
            for mJnt in ml_parentRigJoints:
                if mJnt in ml_used:continue
                if mJnt in [ml_parentRigJoints[0],ml_parentRigJoints[-1]]:
                    ml_baseDynParents.append( mJnt.masterGroup)
                    ml_used.append(mJnt)    
    #...Root controls =================================================================================================
    log.debug("|{0}| >>  Root: {1}".format(_str_func,mRoot))                
    mParent = mRoot.getParent(asMeta=True)
    ml_targetDynParents = []

    if not mParent.hasAttr('cgmAlias'):
        mParent.addAttr('cgmAlias',self.d_module['partName'] + 'base')
    ml_targetDynParents.append(mParent)    
    
    ml_targetDynParents.extend(ml_baseDynParents + ml_endDynParents)

    mDynGroup = cgmRigMeta.cgmDynParentGroup(dynChild=mRoot.mNode,dynMode=2)
    #mDynGroup.dynMode = 2

    for mTar in ml_targetDynParents:
        mDynGroup.addDynParent(mTar)
    mDynGroup.rebuild()
    mDynGroup.dynFollow.p_parent = self.mDeformNull
    
    #...ik controls =================================================================================================
    ml_ikControls = []
    mControlIK = mRigNull.getMessage('controlIK')
    
    if mControlIK:
        ml_ikControls.append(mRigNull.controlIK)
    if mRigNull.getMessage('controlIKBase'):
        ml_ikControls.append(mRigNull.controlIKBase)
        
    for mHandle in ml_ikControls:
        log.debug("|{0}| >>  IK Handle: {1}".format(_str_func,mHandle))                
        
        mParent = mHandle.getParent(asMeta=True)
        ml_targetDynParents = []
    
        if not mParent.hasAttr('cgmAlias'):
            mParent.addAttr('cgmAlias','conIK_base')
        ml_targetDynParents.append(mParent)    
        
        ml_targetDynParents.extend(ml_baseDynParents + ml_endDynParents)
        ml_targetDynParents.extend(mHandle.msgList_get('spacePivots',asMeta = True))
    
        mDynGroup = cgmRigMeta.cgmDynParentGroup(dynChild=mHandle,dynMode=2)
        #mDynGroup.dynMode = 2
    
        for mTar in ml_targetDynParents:
            mDynGroup.addDynParent(mTar)
        mDynGroup.rebuild()
        mDynGroup.dynFollow.p_parent = self.mDeformNull
    
    
    #...rigjoints =================================================================================================
    log.debug("|{0}| >>  Direct...".format(_str_func))                
    for i,mObj in enumerate(mRigNull.msgList_get('rigJoints')):
        log.debug("|{0}| >>  Direct: {1}".format(_str_func,mObj))                        
        ml_targetDynParents = copy.copy(ml_baseDynParents)
        ml_targetDynParents.extend(mObj.msgList_get('spacePivots',asMeta=True) or [])
        
        mParent = mObj.masterGroup.getParent(asMeta=True)
        if not mParent.hasAttr('cgmAlias'):
            mParent.addAttr('cgmAlias','{0}_rig{1}_base'.format(mObj.cgmName,i))
        ml_targetDynParents.insert(0,mParent)
        
        ml_targetDynParents.extend(ml_endDynParents)
        
        mDynGroup = cgmRigMeta.cgmDynParentGroup(dynChild=mObj.mNode)
        mDynGroup.dynMode = 2
        
        for mTar in ml_targetDynParents:
            mDynGroup.addDynParent(mTar)
        
        mDynGroup.rebuild()
        
        mDynGroup.dynFollow.p_parent = mRoot
    
    #...fk controls =================================================================================================
    log.debug("|{0}| >>  FK...".format(_str_func))                
    ml_fkJoints = self.mRigNull.msgList_get('fkJoints')
    
    for mObj in ml_fkJoints:
        log.debug("|{0}| >>  FK: {1}".format(_str_func,mObj))                        
        ml_targetDynParents = copy.copy(ml_baseDynParents)
        
        mParent = mObj.masterGroup.getParent(asMeta=True)
        if not mParent.hasAttr('cgmAlias'):
            mParent.addAttr('cgmAlias','{0}_base'.format(mObj.p_nameBase))
        ml_targetDynParents.insert(0,mParent)
        
        ml_targetDynParents.extend(ml_endDynParents)
        ml_targetDynParents.extend(mObj.msgList_get('spacePivots',asMeta = True))
    
        mDynGroup = cgmRigMeta.cgmDynParentGroup(dynChild=mObj.mNode, dynMode=2)# dynParents=ml_targetDynParents)
        #mDynGroup.dynMode = 2
    
        for mTar in ml_targetDynParents:
            mDynGroup.addDynParent(mTar)
        mDynGroup.rebuild()
        mDynGroup.dynFollow.p_parent = mRoot    
    
    
    #Close out ====================================================================================================
    mRigNull.version = self.d_block['buildVersion']
    cgmGEN.func_snapShot(vars())
    return



    

def build_proxyMesh(self, forceNew = True):
    """
    Build our proxyMesh
    """
    _short = self.d_block['shortName']
    _str_func = '[{0}] > build_proxyMesh'.format(_short)
    log.debug("|{0}| >> ...".format(_str_func))  
    _start = time.clock()
    mBlock = self.mBlock
    mRigNull = self.mRigNull
    mSettings = mRigNull.settings
    mPuppetSettings = self.d_module['mMasterControl'].controlSettings
    
    _side = BLOCKUTILS.get_side(self.mBlock)
    ml_proxy = []
    
    ml_rigJoints = mRigNull.msgList_get('rigJoints',asMeta = True)
    ml_templateHandles = mBlock.msgList_get('templateHandles',asMeta = True)
    
    if not ml_rigJoints:
        raise ValueError,"No rigJoints connected"
    
    #>> If proxyMesh there, delete ----------------------------------------------------------------------------------- 
    _bfr = mRigNull.msgList_get('proxyMesh',asMeta=True)
    if _bfr:
        log.debug("|{0}| >> proxyMesh detected...".format(_str_func))            
        if forceNew:
            log.debug("|{0}| >> force new...".format(_str_func))                            
            mc.delete([mObj.mNode for mObj in _bfr])
        else:
            return _bfr
        
    #Figure out our rig joints --------------------------------------------------------
    mToe = False
    mBall = False
    int_handleEndIdx = -1
    l= []
    
    if mBlock.hasEndJoint:
        mToe = ml_rigJoints.pop(-1)
        log.debug("|{0}| >> mToe: {1}".format(_str_func,mToe))
        int_handleEndIdx -=1
    if mBlock.hasBallJoint:
        mBall = ml_rigJoints.pop(-1)
        log.debug("|{0}| >> mBall: {1}".format(_str_func,mBall))        
        int_handleEndIdx -=1
    
    if mBall or mToe:
        mEnd = ml_rigJoints.pop(-1)
        log.debug("|{0}| >> mEnd: {1}".format(_str_func,mEnd))        
        int_handleEndIdx -=1
    
    log.debug("|{0}| >> Handles Targets: {1}".format(_str_func,ml_rigJoints))            
    log.debug("|{0}| >> End idx: {1} | {2}".format(_str_func,int_handleEndIdx,
                                                   ml_rigJoints[int_handleEndIdx]))                
        
    # Create ---------------------------------------------------------------------------
    ml_segProxy = cgmMeta.validateObjListArg(self.atBuilderUtils('mesh_proxyCreate',
                                                                 ml_rigJoints),
                                             'cgmObject')    
    
    # Foot --------------------------------------------------------------------------
    if ml_templateHandles[-1].getMessage('pivotHelper'):
        
        ml_rigJoints.append(mEnd)#...add this back
        mPivotHelper = ml_templateHandles[-1].pivotHelper
        log.debug("|{0}| >> foot ".format(_str_func))
        
        #make the foot geo....
        l_targets = [ml_templateHandles[-1].loftCurve.mNode]
        
        mBaseCrv = mPivotHelper.doDuplicate(po=False)
        mBaseCrv.parent = False
        mShape2 = False
        
        for mChild in mBaseCrv.getChildren(asMeta=True):
            if mChild.cgmName == 'topLoft':
                mShape2 = mChild.doDuplicate(po=False)
                mShape2.parent = False
                l_targets.append(mShape2.mNode)
            mChild.delete()
                
        l_targets.append(mBaseCrv.mNode)
        reload(BUILDUTILS)
        _mesh = BUILDUTILS.create_loftMesh(l_targets, name="{0}".format('foot'), divisions=1, degree=1)
        
        _l_combine = []
        for i,crv in enumerate([l_targets[0],l_targets[-1]]):
            _res = mc.planarSrf(crv,po=1,ch=True,d=3,ko=0, tol=.01,rn=0)
            log.info(_res)
            _inputs = mc.listHistory(_res[0],pruneDagObjects=True)
            _tessellate = _inputs[0]        
            _d = {'format':1,#Fit
                  'polygonType':1,#'quads',
                  #'vNumber':1,
                  #'uNumber':1
                  }
            for a,v in _d.iteritems():
                ATTR.set(_tessellate,a,v)
            _l_combine.append(_res[0])
            _mesh = mc.polyUnite([_mesh,_res[0]],ch=False,mergeUVSets=1,n = "{0}_proxy_geo".format('foot'))[0]
            #_mesh = mc.polyMergeVertex(_res[0], d= .0001, ch = 0, am = 1 )
        
        
        mBaseCrv.delete()
        if mShape2:mShape2.delete()
        
        mMesh = cgmMeta.validateObjArg(_mesh)
        
        #...cut it up
        if mBall:
            #Heel....
            plane = mc.polyPlane(axis =  MATH.get_obj_vector(mBall.mNode, 'z+'), width = 50, height = 50, ch=0)
            mPlane = cgmMeta.validateObjArg(plane[0])
            mPlane.doSnapTo(mBall.mNode)
            
            mMeshHeel = mMesh.doDuplicate(po=False)
            
            #heel = mc.polyCBoolOp(plane[0], mMeshHeel.mNode, op=3,ch=0, classification = 1)
            import maya.mel as mel
            heel = mel.eval('polyCBoolOp -op 3-ch 0 -classification 1 {0} {1};'.format(mPlane.mNode, mMeshHeel.mNode))
            
            mMeshHeel = cgmMeta.validateObjArg(heel[0])
            
            #ball...
            plane = mc.polyPlane(axis =  MATH.get_obj_vector(mBall.mNode, 'z-'), width = 50, height = 50, ch=0)
            mPlane = cgmMeta.validateObjArg(plane[0])
            mPlane.doSnapTo(mBall.mNode)
            mMeshBall = mMesh.doDuplicate(po=False)
        
            #ball = mc.polyCBoolOp(plane[0], mMeshBall.mNode, op=3,ch=0, classification = 1)
            ball = mel.eval('polyCBoolOp -op 3-ch 0 -classification 1 {0} {1};'.format(mPlane.mNode, mMeshBall.mNode))
            mMeshBall = cgmMeta.validateObjArg(ball[0])
            
            
            ml_segProxy.append(mMeshHeel)
            
            ml_segProxy.append(mMeshBall)
            ml_rigJoints.append(mBall)

    for i,mGeo in enumerate(ml_segProxy):
        log.info("{0} : {1}".format(mGeo, ml_rigJoints[i]))
        mGeo.parent = ml_rigJoints[i]
        ATTR.copy_to(ml_rigJoints[0].mNode,'cgmName',mGeo.mNode,driven = 'target')
        mGeo.addAttr('cgmIterator',i+1)
        mGeo.addAttr('cgmType','proxyGeo')
        mGeo.doName()            
    
    for mProxy in ml_segProxy:
        CORERIG.colorControl(mProxy.mNode,_side,'main',transparent=False)
        
        mc.makeIdentity(mProxy.mNode, apply = True, t=1, r=1,s=1,n=0,pn=1)

        #Vis connect -----------------------------------------------------------------------
        mProxy.overrideEnabled = 1
        ATTR.connect("{0}.proxyVis".format(mPuppetSettings.mNode),"{0}.visibility".format(mProxy.mNode) )
        ATTR.connect("{0}.proxyLock".format(mPuppetSettings.mNode),"{0}.overrideDisplayType".format(mProxy.mNode) )        
        for mShape in mProxy.getShapes(asMeta=1):
            str_shape = mShape.mNode
            mShape.overrideEnabled = 0
            ATTR.connect("{0}.proxyLock".format(mPuppetSettings.mNode),"{0}.overrideDisplayTypes".format(str_shape) )
        
    mRigNull.msgList_connect('proxyMesh', ml_segProxy)




















