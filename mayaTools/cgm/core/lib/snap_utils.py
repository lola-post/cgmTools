"""
------------------------------------------
snap_utils: cgm.core.lib.snap_Utils
Author: Josh Burton
email: jjburton@cgmonks.com
Website : http://www.cgmonks.com
------------------------------------------

"""
# From Python =============================================================
import copy
import re

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# From Maya =============================================================
import maya.cmds as mc
from maya import mel
# From Red9 =============================================================

# From cgm ==============================================================
from cgm.core import cgm_General as cgmGeneral
from cgm.core.cgmPy import validateArgs as VALID
reload(VALID)
from cgm.core.lib import shared_data as SHARED
reload(SHARED)
from cgm.core.lib import search_utils as SEARCH
from cgm.core.lib import math_utils as MATH
from cgm.core.lib import distance_utils as DIST
from cgm.core.lib import position_utils as POS
from cgm.core.lib import euclid as EUCLID

#>>> Utilities
#===================================================================  
    
def go(obj = None, target = None,
       position = True, rotation = True, rotateAxis = False,rotateOrder = False, scalePivot = False,
       pivot = 'rp', space = 'w', mode = 'xform'):
    """
    Core snap functionality. We're moving an object by it's rp to move it around. The scale pivot may be snapped as well
    
    :parameters:
        obj(str): Object to modify
        sourceObject(str): object to copy from

    :returns
        success(bool)
    """   
    _str_func = 'go'
    
    _obj = VALID.objString(obj, noneValid=False, calledFrom = __name__ + _str_func + ">> validate obj")
    _target = VALID.objString(target, noneValid=False, calledFrom = __name__ + _str_func + ">> validate target")
    
    _pivot = VALID.kw_fromDict(pivot, SHARED._d_pivotArgs, noneValid=False,calledFrom= __name__ + _str_func + ">> validate pivot")
    _space = VALID.kw_fromDict(space,SHARED._d_spaceArgs,noneValid=False,calledFrom= __name__ + _str_func + ">> validate space")  
    #_mode = VALID.kw_fromDict(mode,_d_pos_modes,noneValid=False,calledFrom= __name__ + _str_func + ">> validate mode")
    _mode = mode
    log.debug("|{0}| >> obj: {1} | target:{2} | pivot: {5} | space: {3} | mode: {4}".format(_str_func,_obj,_target,_space,_mode,_pivot))             
    log.debug("|{0}| >> position: {1} | rotation:{2} | rotateAxis: {3} | rotateOrder: {4}".format(_str_func,position,rotation,rotateAxis,rotateOrder))             
    
    kws = {'ws':False,'os':False}
    if _space == 'world':kws['ws']=True
    else:kws['os']=True    
    
    if position:
        if _pivot == 'closestPoint':
            log.debug("|{0}|...closestPoint...".format(_str_func))        
            _targetType = SEARCH.get_mayaType(_target)
                
        else:
            log.debug("|{0}|...postion...".format(_str_func))
            pos = POS.get(target,_pivot,_space,_mode)
            mc.move (pos[0],pos[1],pos[2], _obj, **kws)
        
    if rotateAxis:
        log.debug("|{0}|...rotateAxis...".format(_str_func))        
        mc.xform(obj,ra = mc.xform(_target, q=True, ra=True, **kws), p=True, **kws)    
        
    if rotation:
        log.debug("|{0}|...rotation...".format(_str_func))
        rot = mc.xform (_target, q=True, ro=True, **kws)
        mc.xform(_obj, ro = rot, **kws)
    if rotateOrder:
        log.debug("|{0}|...rotateOrder...".format(_str_func))
        mc.xform(obj,roo = mc.xform(_target, q=True, roo=True), p=True)
    if scalePivot:
        log.debug("|{0}|...scalePivot...".format(_str_func))
        mc.xform(obj,sp = mc.xform(_target, q=True, sp=True,**kws), p=True, **kws)
        

    
    return
    pos = infoDict['position']
    
    mc.move (pos[0],pos[1],pos[2], _target, ws=True)
    mc.xform(_target, roo=infoDict['rotateOrder'],p=True)
    mc.xform(_target, ro=infoDict['rotation'], ws = True)
    mc.xform(_target, ra=infoDict['rotateAxis'],p=True)
    
    #mTarget = r9Meta.getMObject(target)
    mc.xform(_target, rp=infoDict['position'], ws = True, p=True)        
    mc.xform(_target, sp=infoDict['scalePivot'], ws = True, p=True)     
    

def aim(obj = None, target = None, aimAxis = "z+", upAxis = "y+"):
    """
    Aim functionality.
    
    :parameters:
        obj(str): Object to modify
        target(str): object to copy from
        aimAxis(str): axis that is pointing forward
        upAxis(str): axis that is pointing up

    :returns
        success(bool)
    """  
    _str_func = 'aim'
    
    _obj = VALID.objString(obj, noneValid=False, calledFrom = __name__ + _str_func + ">> validate obj")
    _target = VALID.objString(target, noneValid=False, calledFrom = __name__ + _str_func + ">> validate target")

    '''Rotate transform based on look vector'''
    # get source and target vectors
    objPos = MATH.Vector3.Create(POS.get(_obj))
    targetPos = MATH.Vector3.Create(POS.get(_target))

    aim = (targetPos - objPos).normalized()

    upVector = MATH.Vector3.up()
    if upAxis == "y-":
        upVector = MATH.Vector3.down()
    elif upAxis == "z+":
        upVector = MATH.Vector3.forward()
    elif upAxis == "z-":
        upVector = MATH.Vector3.back()
    elif upAxis == "x+":
        upVector = MATH.Vector3.right()
    elif upAxis == "x-":
        upVector = MATH.Vector3.left()
    else:
        upVector = MATH.Vector3.up()
    
    up = MATH.transform_direction( _obj, upVector )
    
    wantedAim, wantedUp = MATH.convert_aim_vectors_to_different_axis(aim, up, aimAxis, upAxis)
    
    xformPos = mc.xform(_obj, q=True, matrix = True, ws=True)
    pos = MATH.Vector3(xformPos[12], xformPos[13], xformPos[14])
    rot_matrix = EUCLID.Matrix4.new_look_at(MATH.Vector3.zero(), -wantedAim, wantedUp)
    
    s = MATH.Vector3.Create( mc.getAttr('%s.scale' % _obj)[0] )

    scale_matrix = EUCLID.Matrix4()
    scale_matrix.a = s.x
    scale_matrix.f = s.y
    scale_matrix.k = s.z
    scale_matrix.p = 1

    result_matrix = scale_matrix * rot_matrix

    transform_matrix = result_matrix[0:12] + [pos.x, pos.y, pos.z, 1.0]

    mc.xform(_obj, matrix = transform_matrix , roo="xyz", ws=True)

    return True