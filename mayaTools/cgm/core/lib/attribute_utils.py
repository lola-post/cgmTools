"""
attribute_utils
Josh Burton 
www.cgmonks.com

Refactoring attribte calls to core.
"""
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

# From cgm ==============================================================
from cgm.core import cgm_General as cgmGeneral
from cgm.core.cgmPy import validateArgs as cgmValid


#>>> Utilities
#===================================================================
def validate_arg(arg):
    """
    Validate an attr arg to be more useful for the various methods of calling it

    :parameters:
        arg(varied): Object.attribute arg to check. Accepts 'obj.attr', ['obj','attr'] formats.

    :returns
        data{dict} -- {'obj','attr','combined'}
    """
    if type(arg) in [list,tuple] and len(arg) == 2:
        obj = arg[0]
        attr = arg[1]
        combined = "%s.%s"%(arg[0],arg[1])
        if not mc.objExists(combined):
            raise StandardError,"validate_arg>>>obj doesn't exist: %s"%combined
    elif mc.objExists(arg) and '.' in arg:
        obj = arg.split('.')[0]
        attr = '.'.join(arg.split('.')[1:])
        combined = arg
    else:
        raise ValueError,"validate_arg>>>Bad attr arg: %s"%arg

    return {'obj':obj ,'attr':attr ,'combined':combined}

    
def alias_get(arg, attr = None):
    """
    Gets the alias of an object attribute if there is one
    
    :parameters:
        arg(varied): Accepts 'obj.attr', ['obj','attr'] formats.
        attr(str): attribute to get the alias of

    :returns
        data{dict} -- {'obj','attr','combined'}
    """    
    _d = validate_arg(arg)
    if mc.aliasAttr(_d['combined'],q=True):
        return mc.aliasAttr(_d['combined'],q=True) 
    return None

def alias_set(arg, alias = None):
    """   
    :parameters:
        arg(varied): Accepts 'obj.attr', ['obj','attr'] formats.
        alias(str): Value to set as the alias. If none, the alias is cleared

    """        
    _d = validate_arg(arg)    
    alias = cgmValid.stringArg(alias)
    _alias_current = alias_get(arg)
    if alias:
        try:
            if alias != alias_get(_d['combined']):
                return mc.aliasAttr(alias, _d['combined'])
            else:log.info("'{0}' already has that alias!".format(_d['combined']))
        except:
            log.warning("'{0}' failed to set alias of {1}!".format(_d['combined'],alias))

    else:
        if mc.aliasAttr(_d['combined'],q=True):           
            mc.aliasAttr(_d['combined'],remove=True)
            log.warning("'{0}' cleared of alias!".format(_d['combined']))
            

    