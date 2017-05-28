"""
------------------------------------------
cgmMMPuppet: cgm.core.tools.markingMenus.cgmMMPuppet
Author: Josh Burton
email: jjburton@cgmonks.com

Website : http://www.cgmonks.com
------------------------------------------

================================================================
"""
__version__ = '2.0.02162017'
__int_maxObjects = 8


# From Python =============================================================
import copy
import re
import sys
import time
import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# From Maya =============================================================
import maya.cmds as mc
import maya.mel as mel

from cgm.core import cgm_Meta as cgmMeta
from cgm.core import cgm_RigMeta as cgmRigMeta
from cgm.core import cgm_PuppetMeta as cgmPM
from cgm.core.cgmPy import validateArgs as VALID
from cgm.core import cgm_General as cgmGen
from cgm.core.lib import snap_utils as SNAP
from cgm.core.lib import locator_utils as LOC
from cgm.core.lib import attribute_utils as ATTR
from cgm.core.lib import name_utils as NAMES
from cgm.core.lib import search_utils as SEARCH
from cgm.core.lib import rigging_utils as RIGGING
import cgm.core.classes.GuiFactory as cgmUI
from cgm.core.lib import list_utils as LISTS

from cgm.core.tools.markingMenus.lib import contextual_utils as MMCONTEXT

import cgm.core.classes.GuiFactory as cgmUI
mUI = cgmUI.mUI


def uiSetupOptionVars(self):
    self.create_guiOptionVar('PuppetMMBuildModule', defaultValue = 1)
    self.create_guiOptionVar('PuppetMMBuildPuppet', defaultValue = 1)
    
@cgmGen.Timer    
def bUI_radial(self,parent):
    _str_func = "bUI_radial" 
    
    #====================================================================		
    #mc.menu(parent,e = True, deleteAllItems = True)
    
    
    self._ml_objList = cgmMeta.validateObjListArg(self._l_sel,'cgmObject',True)
    #log.debug("|{0}| >> mObjs: {1}".format(_str_func, self._ml_objList))                

    self._ml_modules = []
    self._l_modules = []
    self._l_puppets = []	
    self._ml_puppets = []
    _optionVar_val_moduleOn = self.var_PuppetMMBuildModule.value
    _optionVar_val_puppetOn = self.var_PuppetMMBuildPuppet.value
       
    
    

    #>>Radial --------------------------------------------------------------------------------------------
    mc.menuItem(parent = parent,
                en = self._b_sel,
                l = 'Mirror Selected',
                c = cgmGen.Callback(MMCONTEXT.func_process, RIGGING.mirror, self._l_sel,'each','mirror',True,**{}),                                                                                      
                rp = 'SW',
                ) 
    
    

def uiOptionMenu_build(self, parent):
    _optionVar_val_moduleOn = self.var_PuppetMMBuildModule.value
    _optionVar_val_puppetOn = self.var_PuppetMMBuildPuppet.value    
    
    uiBuildMenus = mc.menuItem(parent = parent, subMenu = True,
                               l = 'Build Menus')
    
    mc.menuItem(parent = uiBuildMenus,
                l = 'Module',
                c = cgmGen.Callback(self.var_PuppetMMBuildModule.setValue, not _optionVar_val_moduleOn),
                cb = _optionVar_val_moduleOn)
    mc.menuItem(parent = uiBuildMenus,
                l = 'Puppet',
                c = cgmGen.Callback(self.var_PuppetMMBuildPuppet.setValue, not _optionVar_val_puppetOn),
                cb = _optionVar_val_puppetOn)    
    
        
def bUI_lower(self,parent):
    """
    Create the UI
    """	
    _str_func = 'bUI_lower'
    _optionVar_val_moduleOn = self.var_PuppetMMBuildModule.value
    _optionVar_val_puppetOn = self.var_PuppetMMBuildPuppet.value  
    
    
    timeStart_objectList = time.clock()    
    #>>  Individual objects....  ============================================================================
    if self._ml_objList:
        self._d_mObjInfo = {}
        #first we validate
        #First we're gonna gather all of the data
        #------------------------------------------------------
        for i,mObj in enumerate(self._ml_objList):
            _short = mObj.mNode
            if i >= __int_maxObjects:
                log.warning("|{0}| >> More than {0} objects select, only loading first  for speed".format(_str_func, __int_maxObjects))                                
                break
            d_buffer = {}
            
            #>>> Space switching ------------------------------------------------------------------	
            _dynParentGroup = ATTR.get_message(mObj.mNode,'dynParentGroup')
            if _dynParentGroup:
                i_dynParent = cgmMeta.validateObjArg(_dynParentGroup[0],'cgmDynParentGroup',True)
                d_buffer['dynParent'] = {'mi_dynParent':i_dynParent,'attrs':[],'attrOptions':{}}#Build our data gatherer					    
                if i_dynParent:
                    for a in cgmRigMeta.d_DynParentGroupModeAttrs[i_dynParent.dynMode]:
                        if mObj.hasAttr(a):
                            d_buffer['dynParent']['attrs'].append(a)
                            lBuffer_attrOptions = []
                            #for i,o in enumerate(cgmMeta.cgmAttr(mObj.mNode,a).p_enum):
                            for i,o in enumerate(ATTR.get_enumList(_short,a)):
                                lBuffer_attrOptions.append(o)
                            d_buffer['dynParent']['attrOptions'][a] = lBuffer_attrOptions
            self._d_mObjInfo[mObj] = d_buffer

            #>>> Module --------------------------------------------------------------------------
            if _optionVar_val_moduleOn or _optionVar_val_puppetOn:
                if mObj.getMessage('rigNull'):
                    _mi_rigNull = mObj.rigNull		
                    
                    try:_mi_module = _mi_rigNull.module
                    except Exception:_mi_module = False

                    if _optionVar_val_moduleOn:
                        try:
                            self._ml_modules.append(_mi_module)
                        except Exception,err:
                            log.debug("|{0}| >> obj: {1} | err: {2}".format(_str_func, _short, err))                

                if _optionVar_val_puppetOn:
                    try:
                        if _mi_module:
                            buffer = _mi_module.getMessage('modulePuppet')
                            if buffer:
                                self._l_puppets.append(buffer[0])
                    except Exception,err:
                        log.debug("|{0}| >> No module puppet. obj: {1} | err: {2}".format(_str_func, _short, err))                
                    
                    try:
                        buffer = mObj.getMessage('puppet')
                        if buffer:
                            self._l_puppets.append(buffer[0])
                    except Exception,err:
                        log.debug("|{0}| >> No puppet. obj: {1} | err: {2}".format(_str_func, _short, err))                
        #for k in self._d_mObjInfo.keys():
            #log.debug("%s: %s"%(k.getShortName(),self._d_mObjInfo.get(k)))
        #cgmGen.print_dict(self._d_mObjInfo)
        #Build the menu
        
        #=========================================================================================
        #>> Find Common options ------------------------------------------------------------------
        timeStart_commonOptions = time.clock()    
        l_commonAttrs = []
        d_commonOptions = {}
        bool_firstFound = False
        for mObj in self._d_mObjInfo.keys():
            if 'dynParent' in self._d_mObjInfo[mObj].keys():
                attrs = self._d_mObjInfo[mObj]['dynParent'].get('attrs') or []
                attrOptions = self._d_mObjInfo[mObj]['dynParent'].get('attrOptions') or {}
                if self._d_mObjInfo[mObj].get('dynParent'):
                    if not l_commonAttrs and not bool_firstFound:
                        log.debug('first found')
                        l_commonAttrs = attrs
                        state_firstFound = True
                        d_commonOptions = attrOptions
                    elif attrs:
                        log.debug(attrs)
                        for a in attrs:
                            if a in l_commonAttrs:
                                for option in d_commonOptions[a]:			
                                    if option not in attrOptions[a]:
                                        d_commonOptions[a].remove(option)

        log.debug("|{0}| >> Common Attrs: {1}".format(_str_func, l_commonAttrs))                
        log.debug("|{0}| >> Common Options: {1}".format(_str_func, d_commonOptions))    
        log.debug("|{0}| >> Common options build: {1}".format(_str_func,  '%0.3f seconds  ' % (time.clock()-timeStart_commonOptions)))    
        


        #>> Build ------------------------------------------------------------------
        int_lenObjects = len(self._d_mObjInfo.keys())
        # Mutli
        if int_lenObjects == 1:
            #MelMenuItem(parent,l="-- Object --",en = False)	    					
            use_parent = parent
            state_multiObject = False
        else:
            #MelMenuItem(parent,l="-- Objects --",en = False)	    			
            #iSubM_objects = mUI.MelMenuItem(parent,l="Objects(%s)"%(int_lenObjects),subMenu = True)
            iSubM_objects = mc.menuItem(p=parent,l="Objects(%s)"%(int_lenObjects),subMenu = True)
            
            use_parent = iSubM_objects
            state_multiObject = True		
            if l_commonAttrs and [d_commonOptions.get(a) for a in l_commonAttrs]:
                for atr in d_commonOptions.keys():
                    #tmpMenu = mUI.MelMenuItem( parent, l="multi Change %s"%atr, subMenu=True)
                    tmpMenu = mc.menuItem( p=parent, l="multi Change %s"%atr, subMenu=True)                    
                    for i,o in enumerate(d_commonOptions.get(atr)):
                        mc.menuItem(p=tmpMenu,l = "%s"%o,
                                    c = cgmUI.Callback(func_multiChangeDynParent,atr,o))
        # Individual ----------------------------------------------------------------------------
        #log.debug("%s"%[k.getShortName() for k in self._d_mObjInfo.keys()])
        for mObj in self._d_mObjInfo.keys():
            _short = mObj.p_nameShort
            d_buffer = self._d_mObjInfo.get(mObj) or False
            if d_buffer:
                if state_multiObject:
                    #iTmpObjectSub = mUI.MelMenuItem(use_parent,l=" %s  "%mObj.getBaseName(),subMenu = True)
                    iTmpObjectSub = mc.menuItem(p=use_parent,l=" %s  "%mObj.getBaseName(),subMenu = True)                    
                else:
                    mc.menuItem(p=parent,l="-- %s --"%_short,en = False)
                    iTmpObjectSub = use_parent
                if d_buffer.get('dynParent'):
                    mi_dynParent = d_buffer['dynParent'].get('mi_dynParent')
                    d_attrOptions = d_buffer['dynParent'].get('attrOptions') or {}			
                    for a in d_attrOptions.keys():
                        if mObj.hasAttr(a):
                            lBuffer_attrOptions = []
                            tmpMenu = mc.menuItem( p=iTmpObjectSub, l="Change %s"%a, subMenu=True)
                            v = ATTR.get("%s.%s"%(_short,a))
                            for i,o in enumerate(ATTR.get_enumList(_short,a)):#enumerate(cgmMeta.cgmAttr(mObj.mNode,a).p_enum)
                                if i == v:b_enable = False
                                else:b_enable = True
                                mc.menuItem(p=tmpMenu,l = "%s"%o,en = b_enable,
                                            c = cgmUI.Callback(mi_dynParent.doSwitchSpace,a,i))
                else:
                    log.debug("|{0}| >> lacks dynParent: {1}".format(_str_func, _short))                
                    
    log.debug("|{0}| >> Object list build: {1}".format(_str_func,  '%0.3f seconds  ' % (time.clock()-timeStart_objectList)))    

    
    
    #>>> Module =====================================================================================================
    timeStart_ModuleStuff = time.clock() 
    
    if _optionVar_val_moduleOn and self._ml_modules:
        #MelMenuItem(parent,l="-- Modules --",en = False)	    
        self._ml_modules = LISTS.get_noDuplicates(self._ml_modules)
        int_lenModules = len(self._ml_modules)
        if int_lenModules == 1:
            use_parent = parent
            state_multiModule = False
        else:
            #iSubM_modules = mUI.MelMenuItem(parent,l="Modules(%s)"%(int_lenModules),subMenu = True)
            iSubM_modules = mc.menuItem(p=parent,l="Modules(%s)"%(int_lenModules),subMenu = True)
            
            use_parent = iSubM_modules
            state_multiModule = True
            mc.menuItem(p = parent, l="Select",
                        c = cgmGen.Callback(func_multiModuleSelect))
            mc.menuItem(p = parent, l="Key",
                        c = cgmGen.Callback(func_multiModuleKey))		
            mc.menuItem(p = parent, l="toFK",
                        c = cgmGen.Callback(func_multiDynSwitch,0))	
            mc.menuItem(p = parent, l="toIK",
                        c = cgmGen.Callback(func_multiDynSwitch,1))
            mc.menuItem(p = parent, l="Reset",
                        c = cgmGen.Callback(func_multiReset))			

        for mModule in self._ml_modules:
            _short = mModule.p_nameShort
            _side = cgmGen.verify_mirrorSideArg(mModule.getMayaAttr('cgmDirection') or 'center')
            if state_multiModule:
                iTmpModuleSub = mc.menuItem(p=iSubM_modules,l=" %s  "%mModule.getBaseName(),subMenu = True)
                use_parent = iTmpModuleSub

            else:
                mc.menuItem(p=parent,l="-- %s --"%mModule.getBaseName(),en = False)
            try:#To build dynswitch
                i_switch = mModule.rigNull.dynSwitch
                for a in i_switch.l_dynSwitchAlias:
                    mc.menuItem(p = use_parent, l="%s"%a,
                                c = cgmGen.Callback(i_switch.go,a))						
            except Exception,err:
                log.error("|{0}| >> dynSwitch FAILURE: {1} | {2}".format(_str_func, _short,err))                
                
            try:#module basic menu
                mc.menuItem(p = use_parent, l="Key",
                            c = cgmGen.Callback(mModule.animKey))							
                mc.menuItem(p = use_parent, l="Select",
                            c = cgmGen.Callback(mModule.animSelect))	
                mc.menuItem(p = use_parent, l="Reset",
                            c = cgmGen.Callback(mModule.animReset,self.var_resetMode.value))
                mc.menuItem(p = use_parent, l="Mirror",
                            c = cgmGen.Callback(mModule.mirrorMe))

                if mModule.moduleType not in cgmPM.__l_faceModuleTypes__:
                    _enable = True
                    if _side == 'Centre':_enable = False
                    mc.menuItem(p = use_parent, l="Mirror Push",en = _enable,
                                c = cgmGen.Callback(mModule.mirrorPush))	
                    mc.menuItem(p = use_parent, l="Mirror Pull",en = _enable,
                                c = cgmGen.Callback(mModule.mirrorPull))
                else:#Face module....
                    mc.menuItem(p = use_parent, l="Mirror Left",
                                c = cgmGen.Callback(mModule.mirrorLeft))	
                    mc.menuItem(p = use_parent, l="Mirror Right",
                                c = cgmGen.Callback(mModule.mirrorRight))

                mUI.MelMenuItem( use_parent, l="Toggle Sub",
                                 c = cgmGen.Callback(mModule.toggle_subVis))			    
            except Exception,err:
                log.error("|{0}| >> Basic module menu FAILURE: {1} | {2}".format(_str_func, _short,err))                
                
            try:#module children
                if mModule.getMessage('moduleChildren'):
                    iSubM_Children = mc.menuItem(p = use_parent, l="Children:",
                                                 subMenu = True)
                    mc.menuItem(p = iSubM_Children, l="toFK",
                                c = cgmGen.Callback(mModule.dynSwitch_children,0))	
                    mc.menuItem(p = iSubM_Children, l="toIK",
                                c = cgmGen.Callback(mModule.dynSwitch_children,1))				
                    mc.menuItem(p = iSubM_Children, l="Key",
                                c = cgmGen.Callback(mModule.animKey_children))							
                    mc.menuItem(p = iSubM_Children, l="Select",
                                c = cgmGen.Callback(mModule.animSelect_children))
                    mc.menuItem(p = iSubM_Children, l="Reset",
                                c = cgmGen.Callback(mModule.animReset_children,self.var_resetMode.value))			
                    mc.menuItem(p = iSubM_Children, l="Mirror",
                                c = cgmGen.Callback(children_mirror,self,mModule))
                    if mModule.moduleType not in cgmPM.__l_faceModuleTypes__:
                        mc.menuItem(p = iSubM_Children, l="Mirror Push",
                                    c = cgmGen.Callback(children_mirrorPush,self,mModule))
                        mc.menuItem(p = iSubM_Children, l="Mirror Pull",
                                    c = cgmGen.Callback(children_mirrorPull,self,mModule))
                    mc.menuItem(p = iSubM_Children, l="visSub Show",
                                c = cgmGen.Callback(mModule.animSetAttr_children,'visSub',1,True,False))				
                    mc.menuItem(p = iSubM_Children, l="visSub Hide",
                                c = cgmGen.Callback(mModule.animSetAttr_children,'visSub',0,True,False))			
            except Exception,err:
                log.error("|{0}| >> module children menu FAILURE: {1} | {2}".format(_str_func, _short,err))                
                
            try:#module siblings
                if mModule.getModuleSiblings():
                    iSubM_Siblings = mc.menuItem(p = use_parent, l="Siblings:",
                                                 subMenu = True)
                    mc.menuItem(p = iSubM_Siblings, l="toFK",
                                c = cgmGen.Callback(mModule.dynSwitch_siblings,0,False))	
                    mc.menuItem(p = iSubM_Siblings, l="toIK",
                                c = cgmGen.Callback(mModule.dynSwitch_siblings,1,False))				
                    mc.menuItem(p = iSubM_Siblings, l="Key",
                                c = cgmGen.Callback(mModule.animKey_siblings,False))							
                    mc.menuItem(p = iSubM_Siblings, l="Select",
                                c = cgmGen.Callback(mModule.animSelect_siblings,False))
                    mc.menuItem(p = iSubM_Siblings, l="Reset",
                                c = cgmGen.Callback(mModule.animReset_siblings,False))			
                    mc.menuItem(p = iSubM_Siblings, l="Push pose",
                                c = cgmGen.Callback(mModule.animPushPose_siblings))			
                    mc.menuItem(p = iSubM_Siblings, l="Mirror",
                                c = cgmGen.Callback(mModule.mirrorMe_siblings,False))

                    if mModule.moduleType not in cgmPM.__l_faceModuleTypes__:
                        mc.menuItem(p = iSubM_Siblings, l="Mirror Push",
                                    c = cgmGen.Callback(mModule.mirrorPush_siblings,False))
                        mc.menuItem(p = iSubM_Siblings, l="Mirror Pull",
                                    c = cgmGen.Callback(mModule.mirrorPull_siblings,False))
            except Exception,err:
                log.error("|{0}| >> module sibling menu FAILURE: {1} | {2}".format(_str_func, _short,err))                
                
            mc.menuItem(p=parent,l = "-"*25,en = False)
    log.debug("|{0}| >> Module options build: {1}".format(_str_func,  '%0.3f seconds  ' % (time.clock()-timeStart_ModuleStuff)))    
    
    
    
    #>>> Puppet =====================================================================================================
    timeStart_PuppetStuff = time.clock()  	    
    if _optionVar_val_puppetOn and self._l_puppets:
        #MelMenuItem(parent,l="-- Puppets --",en = False)	    
        self._l_puppets = LISTS.get_noDuplicates(self._l_puppets)
        self._ml_puppets = cgmMeta.validateObjListArg(self._l_puppets)
        
        log.debug("|{0}| >> Puppets: ".format(_str_func))
        for p in self._l_puppets:
            log.debug("|{0}| >> ---- {1} ".format(_str_func,p))
            
        int_lenPuppets = len(self._ml_puppets)
        if int_lenPuppets == 1:
            use_parent = parent
            state_multiPuppet = False
        else:
            iSubM_puppets = mUI.MelMenuItem(parent,l="Puppets(%s)"%(int_lenPuppets),subMenu = True)
            use_parent = iSubM_puppets
            state_multiPuppet = True
            mc.menuItem(p = parent, l="Select",
                        c = cgmGen.Callback(func_multiPuppetSelect))
            mc.menuItem(p = parent, l="Key",
                        c = cgmGen.Callback(func_multiPuppetKey))	
            """
    mc.menuItem(p = parent, l="toFK",
                     c = cgmGen.Callback(func_multiDynSwitch,0))	
    mc.menuItem(p = parent, l="toIK",
                     c = cgmGen.Callback(func_multiDynSwitch,1))	
    """
        for mPuppet in self._ml_puppets:
            _name = mPuppet.cgmName
            _short = mPuppet.p_nameShort
            try:
                if state_multiPuppet:
                    iTmpPuppetSub = mc.menuItem(p = iSubM_puppets,l=" %s  "%_name,subMenu = True)
                    use_parent = iTmpPuppetSub    
                else:
                    mc.menuItem(p = parent,l="-- %s --"%_name,en = False)
                '''
        try:#To build dynswitch
        i_switch = mPuppet.rigNull.dynSwitch
        for a in i_switch.l_dynSwitchAlias:
            mc.menuItem(p = use_parent, l="%s"%a,
                 c = cgmGen.Callback(i_switch.go,a))						
        except Exception,error:
        log.info("Failed to build dynSwitch for: %s | %s"%(mPuppet.getShortName(),error))	
        '''
                try:#puppet basic menu
                    mc.menuItem(p = use_parent, l="Key",c = cgmGen.Callback(mPuppet.anim_key))							
                    mc.menuItem(p = use_parent, l="Select",c = cgmGen.Callback(mPuppet.anim_select))	
                    mc.menuItem(p = use_parent, l="Reset",c = cgmGen.Callback(mPuppet.anim_reset,self.var_resetMode.value))
                    mc.menuItem(p = use_parent, l="Mirror",c = cgmGen.Callback(mPuppet.mirrorMe))
                    mc.menuItem(p = use_parent, l="PushRight",c = cgmGen.Callback(mPuppet.mirror_do,'anim','symLeft'))
                    mc.menuItem(p = use_parent, l="PushLeft",c = cgmGen.Callback(mPuppet.mirror_do,'anim','symRight'))		    
                except Exception,err:
                    log.error("|{0}| >> Puppet basic menu FAILURE: {1} | {2}".format(_str_func, _short,err))                

                try:#puppet settings ===========================================================================
                    mmPuppetSettingsMenu = mc.menuItem(p = parent, l='Settings', subMenu=True)
                    mmPuppetControlSettings = mPuppet.masterControl.controlSettings 
                    l_settingsUserAttrs = mmPuppetControlSettings.getUserAttrs()

                    mc.menuItem(p = mmPuppetSettingsMenu, l="visSub Show",
                                     c = cgmGen.Callback(mPuppet.animSetAttr,'visSub',1,True))				
                    mc.menuItem(p = mmPuppetSettingsMenu, l="visSub Hide",
                                     c = cgmGen.Callback(mPuppet.animSetAttr,'visSub',0,True))		    

                    for attr in ['skeleton','geo','geoType']:
                        try:#Skeleton
                            if mmPuppetControlSettings.hasAttr(attr):
                                mi_tmpMenu = mc.menuItem(p = mmPuppetSettingsMenu, l=attr, subMenu=True)			    
                                mi_collectionMenu = mUI.MelRadioMenuCollection()#build our collection instance			    
                                mi_attr = cgmMeta.cgmAttr(mmPuppetControlSettings,attr)
                                l_options = mi_attr.getEnum()
                                for i,str_option in enumerate(l_options):
                                    if i == mi_attr.value:b_state = True
                                    else:b_state = False
                                    mi_collectionMenu.createButton(mi_tmpMenu,l=' %s '%str_option,
                                                                   c = cgmGen.Callback(mc.setAttr,"%s"%mi_attr.p_combinedName,i),
                                                                   rb = b_state )					
                        except Exception,err:
                            log.info("option failed: %s | %s"%(attr,err))	

                    _d_moduleSettings = {'templates':{'options':['off','on'],'attr':'_tmpl'},
                                         'rigGuts':{'options':['off','lock','on'],'attr':'_rig'}}
                    for attr in _d_moduleSettings.keys():
                        try:#Skeleton
                            _l_options = _d_moduleSettings[attr]['options']
                            _attr = _d_moduleSettings[attr]['attr']
                            mi_tmpMenu = mc.menuItem(p = mmPuppetSettingsMenu, l=attr, subMenu=True)			    
                            for i,str_option in enumerate(_l_options):
                                mc.menuItem(p = mi_tmpMenu, l=str_option,
                                            c = cgmGen.Callback(func_setPuppetControlSetting,mPuppet,_attr,i))				
                        except Exception,err:
                            log.error("option failed: %s | %s"%(attr,err))
                except Exception,err:
                    log.error("|{0}| >> puppet settings menu FAILURE: {1} | {2}".format(_str_func, _short,err))                

            except Exception,err:
                log.error("|{0}| >> Puppet: {1} | {2}".format(_str_func, _short,err))                

                mc.menuItem(p=parent,l = "-"*25,en = False)
    log.debug("|{0}| >> Puppet options build: {1}".format(_str_func,  '%0.3f seconds  ' % (time.clock()-timeStart_PuppetStuff)))    
    
    
    f_time = time.clock()-timeStart_objectList    
    log.debug("|{0}| >> Build menu: {1}".format(_str_func,  '%0.3f seconds  ' % (f_time)))    
    
    
    
    
def buttonAction(self,command):
    """
    execute a command and let the menu know not do do the default button action but just kill the ui
    """			
    self.mmActionOptionVar.value=1			
    command
    killUI()	

def func_multiModuleSelect(self):
    """
    execute a command and let the menu know not do do the default button action but just kill the ui
    """	
    l_buffer = []
    if self.ml_modules:
        l_buffer = []
        for i_m in self.ml_modules:
            l_buffer.extend( i_m.rigNull.moduleSet.getList() )
        mc.select(l_buffer )
    killUI()	

def func_multiModuleKey(self):
    """
    execute a command and let the menu know not do do the default button action but just kill the ui
    """		
    l_slBuffer = mc.ls(sl=True) or []		    
    func_multiModuleSelect()
    setKey()
    if l_slBuffer:mc.select(l_slBuffer)
    killUI()	

def func_multiDynSwitch(self):
    """
    execute a command and let the menu know not do do the default button action but just kill the ui
    """		
    l_slBuffer = mc.ls(sl=True) or []		    	    
    if self.ml_modules:
        for i_m in self.ml_modules:
            try:i_m.rigNull.dynSwitch.go(arg)
            except Exception,error:log.error(error)
    if l_slBuffer:mc.select(l_slBuffer)		    
    killUI()	

def func_setPuppetControlSetting(self,mPuppet,attr,arg):
    """
    execute a command and let the menu know not do do the default button action but just kill the ui
    """	
    l_slBuffer = mc.ls(sl=True) or []		    	    	    
    try:
        mPuppet.controlSettings_setModuleAttrs(attr,arg)
    except Exception,error:
        log.error("[func_setPuppetControlSetting fail!]{%s}"%error)
    if l_slBuffer:mc.select(l_slBuffer)		    
    killUI()	

def func_multiReset(self):
    """
    execute a command and let the menu know not do do the default button action but just kill the ui
    """	
    l_slBuffer = mc.ls(sl=True) or []		    	    	    	    
    if self.ml_modules:
        for i_m in self.ml_modules:
            i_m.animReset(self.ResetModeOptionVar.value)
    if l_slBuffer:mc.select(l_slBuffer)		    	    
    killUI()		

def func_multiChangeDynParentOLD(self,attr,option):
    """
    execute a command and let the menu know not do do the default button action but just kill the ui
    """	
    l_objects = [i_o.getShortName() for i_o in self.d_objectsInfo.keys()]
    log.info("func_multiChangeDynParent>> attr: '%s' | option: '%s' | objects: %s"%(attr,option,l_objects))
    timeStart_tmp = time.clock()
    for i_o in self.d_objectsInfo.keys():
        try:
            mi_dynParent = self.d_objectsInfo[i_o]['dynParent'].get('mi_dynParent')
            mi_dynParent.doSwitchSpace(attr,option)
        except Exception,error:
            log.error("func_multiChangeDynParent>> '%s' failed. | %s"%(i_o.getShortName(),error))    

    log.info(">"*10  + ' func_multiChangeDynParent =  %0.3f seconds  ' % (time.clock()-timeStart_tmp) + '<'*10)  
    mc.select(l_objects)

def aimObjects(self):
    _str_funcName = "%s.aimObjects"%puppetKeyMarkingMenu._str_funcName
    log.debug(">>> %s "%(_str_funcName) + "="*75) 
    l_slBuffer = mc.ls(sl=True) or []		    	    	    	    	    
    for i_obj in self.ml_objList[1:]:
        try:
            if i_obj.hasAttr('mClass') and i_obj.mClass == 'cgmControl':
                if i_obj._isAimable():
                    i_obj.doAim(self.i_target)
        except Exception,error:
            log.error("%s >> obj: '%s' | error: %s"%(_str_funcName,i_obj.p_nameShort,error))
    if l_slBuffer:mc.select(l_slBuffer)		    	    

def mirrorObjects(self):
    _str_funcName = "%s.mirrorObjects"%puppetKeyMarkingMenu._str_funcName
    log.debug(">>> %s "%(_str_funcName) + "="*75)  	    
    l_slBuffer = mc.ls(sl=True) or []		    	    	    	    	    	    
    for i_obj in self.ml_objList:
        try:i_obj.doMirrorMe()
        except Exception,error:
            log.error("%s >> obj: '%s' | error: %s"%(_str_funcName,i_obj.p_nameShort,error))
    if l_slBuffer:mc.select(l_slBuffer)		    	    

def children_mirror(self,module):
    _str_funcName = "%s.children_mirror"%puppetKeyMarkingMenu._str_funcName
    log.debug(">>> %s "%(_str_funcName) + "="*75)  
    l_slBuffer = mc.ls(sl=True) or []		    	    	    	    	    	    	    
    try:module.mirrorMe()
    except Exception,error:
        log.error("%s >> obj: '%s' | error: %s"%(_str_funcName,module.p_nameShort,error))	    

    for mMod in module.get_allModuleChildren():
        try:mMod.mirrorMe()
        except Exception,error:
            log.error("%s >> obj: '%s' | error: %s"%(_str_funcName,mMod.p_nameShort,error))
    if l_slBuffer:mc.select(l_slBuffer)		    	    

def children_mirrorPush(self,module):
    _str_funcName = "%s.children_mirror"%puppetKeyMarkingMenu._str_funcName
    log.debug(">>> %s "%(_str_funcName) + "="*75)
    l_slBuffer = mc.ls(sl=True) or []		    	    	    	    	    	    	    	    
    try:module.mirrorPush()
    except Exception,error:
        log.error("%s >> obj: '%s' | error: %s"%(_str_funcName,module.p_nameShort,error))

    for mMod in module.get_allModuleChildren():
        try:mMod.mirrorPush()
        except Exception,error:
            log.error("%s >> obj: '%s' | error: %s"%(_str_funcName,mMod.p_nameShort,error))
    if l_slBuffer:mc.select(l_slBuffer)		    	    

def children_mirrorPull(self,module):
    _str_funcName = "%s.children_mirror"%puppetKeyMarkingMenu._str_funcName
    log.debug(">>> %s "%(_str_funcName) + "="*75)  

    l_slBuffer = mc.ls(sl=True) or []		    	    	    	    	    	    	    	    	    
    try:module.mirrorPull()
    except Exception,error:
        log.error("%s >> obj: '%s' | error: %s"%(_str_funcName,module.p_nameShort,error))

    for mMod in module.get_allModuleChildren():
        try:mMod.mirrorPull()
        except Exception,error:
            log.error("%s >> obj: '%s' | error: %s"%(_str_funcName,mMod.p_nameShort,error))
    if l_slBuffer:mc.select(l_slBuffer)