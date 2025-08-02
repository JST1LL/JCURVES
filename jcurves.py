import bpy
from bpy.utils import resource_path
from pathlib import Path

USER = Path(resource_path('USER'))
src = USER / "scripts/addons" / "J_CURVES"

file_path = src / "blendfile" / "J_Curves Geometry Nodes.blend"
inner_path = "NodeTree"
object_name = "J.CURVES"


class JCurves(bpy.types.Panel):
    bl_label = "J.CURVES"
    bl_idname = "PT_JCurves_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'J.CURVES'
    
    def draw(self, context):
        layout = self.layout
        layout.scale_y = 1.5
        row = layout.row()
        row.operator('add.jcurve_operator', text="ADD CURVE")


class CURVE_OT_ADDJCURVE(bpy.types.Operator):
    bl_label = "Add Curve"
    bl_idname = 'add.jcurve_operator'

    def execute(self, context):

        if object_name not in bpy.data.node_groups:
            bpy.ops.wm.link(
                filepath=str(file_path / inner_path / object_name),
                directory=str(file_path / inner_path),
                filename=object_name
            )

        # Now add the curve and apply modifiers
        bpy.ops.curve.primitive_nurbs_path_add(enter_editmode=True)
        bpy.ops.curve.spline_type_set(type='POLY')

        for obj in context.selected_objects:
            if obj.type == "CURVE" and "J.CURVES" not in obj.modifiers:
                modifier = obj.modifiers.new("J.CURVES", "NODES")
                replacement = bpy.data.node_groups["J.CURVES"]
                modifier.node_group = replacement
                obj.modifiers.active.show_group_selector = False

        return {'FINISHED'}


register, unregister = bpy.utils.register_classes_factory(
    (JCurves, CURVE_OT_ADDJCURVE)
)

if __name__ == "__main__":
    register()

