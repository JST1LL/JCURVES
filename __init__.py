bl_info = {
    "name": "J.CURVES",
    "author": "J.STILL",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "View3D > J.CURVES",
    "warning": "",
    "doc_url": "https://github.com/JST1LL/JCURVES",
    "category": "Curves"
}

import bpy
from . import jcurves
from . import bake_panel

def register():
    jcurves.register()
    bake_panel.register()

def unregister():
    jcurves.unregister()
    bake_panel.unregister()

if __name__ == "__main__":
    register()