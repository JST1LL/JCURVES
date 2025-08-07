bl_info = {
    "name": "J.CURVES",
    "author": "J.STILL",
    "version": (1, 0, 1),
    "blender": (4, 5, 1),
    "location": "View3D > J.CURVES",
    "warning": "",
    "doc_url": "https://github.com/JST1LL/JCURVES",
    "category": "Curves"
}

import bpy

from .jcurves import CURVE_OT_ADDJCURVE, JCurves

def register():
    bpy.utils.register_class(CURVE_OT_ADDJCURVE)
    bpy.utils.register_class(JCurves)
    
def unregister():
    bpy.utils.unregister_class(CURVE_OT_ADDJCURVE)
    bpy.utils.unregister_class(JCurves)