# jcurves.py
import bpy
from pathlib import Path


# ---------------------------
# PROPERTY GROUP
# ---------------------------
class SimpleBakeProps(bpy.types.PropertyGroup):
    use_existing_colors: bpy.props.BoolProperty(
        name="Use Existing Colors",
        description="If checked, do not add the J.CURVEScolor modifier (keeps existing color setup)",
        default=False,
    )


# ---------------------------
# GET ADDON DIRECTORY
# ---------------------------
def get_addon_dir():
    return Path(__file__).resolve().parent


# ---------------------------
# OPERATOR 1: Add Curve
# ---------------------------
class CURVE_OT_ADDJCURVE(bpy.types.Operator):
    bl_label = "Add Curve"
    bl_idname = 'curve.add_jcurve'
    bl_description = "Add a nurbs path and apply J.CURVES geometry nodes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        file_path = get_addon_dir() / "blendfile" / "J_Curves Geometry Nodes.blend"
        node_group_name = "J.CURVES"

        # Load node group if not already loaded
        if node_group_name not in bpy.data.node_groups:
            if not file_path.exists():
                self.report({'ERROR'}, f"Blend file not found: {file_path}")
                return {'CANCELLED'}

            try:
                with bpy.data.libraries.load(str(file_path), link=True) as (data_from, data_to):
                    if node_group_name in data_from.node_groups:
                        data_to.node_groups = [node_group_name]
                    else:
                        self.report({'ERROR'}, f"Node group '{node_group_name}' not found in .blend file.")
                        return {'CANCELLED'}
            except Exception as e:
                self.report({'ERROR'}, f"Failed to link node group: {e}")
                return {'CANCELLED'}

        # Create the curve
        bpy.ops.curve.primitive_nurbs_path_add(enter_editmode=True)
        bpy.ops.curve.spline_type_set(type='POLY')

        # Apply modifier to selected curve objects
        for obj in context.selected_objects:
            if obj.type == "CURVE" and node_group_name not in obj.modifiers:
                mod = obj.modifiers.new(node_group_name, "NODES")
                mod.node_group = bpy.data.node_groups[node_group_name]
                mod.show_viewport = True
                mod.show_render = True

        return {'FINISHED'}


# ---------------------------
# OPERATOR 2: Convert to Mesh
# ---------------------------
class CURVE_OT_CONVERT_TO_MESH(bpy.types.Operator):
    bl_label = "Convert to Mesh"
    bl_idname = 'curve.convert_to_mesh'
    bl_description = "Convert curve to mesh and make materials local"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object selected.")
            return {'CANCELLED'}

        if obj.type != 'CURVE':
            self.report({'ERROR'}, "Active object is not a curve.")
            return {'CANCELLED'}

        # Switch to object mode if needed
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Convert to mesh
        try:
            bpy.ops.object.convert(target='MESH')
        except RuntimeError as e:
            self.report({'ERROR'}, f"Convert failed: {e}")
            return {'CANCELLED'}

        mesh_obj = context.active_object

        # Make materials local
        made_local = False
        for slot in mesh_obj.material_slots:
            mat = slot.material
            if not mat:
                continue

            if mat.library is not None:
                local_name = mat.name
                existing_local = bpy.data.materials.get(local_name)
                if existing_local and existing_local.library is None:
                    slot.material = existing_local
                    self.report({'INFO'}, f"Reused local material: {local_name}")
                else:
                    new_mat = mat.copy()
                    slot.material = new_mat
                    self.report({'INFO'}, f"Made material local: {new_mat.name}")
                    made_local = True

        # Add color modifier if materials were made local and option is enabled
        props = context.scene.simple_bake_props
        if made_local and not props.use_existing_colors:
            mod_name = "J.CURVEScolor"
            if mod_name not in mesh_obj.modifiers:
                blend_file = get_addon_dir() / "blendfile" / "J_Curves Geometry Nodes.blend"

                if not blend_file.exists():
                    self.report({'WARNING'}, f"Blend file not found: {blend_file}")
                else:
                    color_node_group_name = "J.CURVEScolor"
                    # Load node group if missing
                    if color_node_group_name not in bpy.data.node_groups:
                        try:
                            with bpy.data.libraries.load(str(blend_file), link=False) as (data_from, data_to):
                                if color_node_group_name in data_from.node_groups:
                                    data_to.node_groups = [color_node_group_name]
                                else:
                                    self.report({'WARNING'}, f"Node group '{color_node_group_name}' not found in .blend file.")
                        except Exception as e:
                            self.report({'WARNING'}, f"Failed to load node group: {e}")

                    # Assign if available
                    if color_node_group_name in bpy.data.node_groups:
                        mod = mesh_obj.modifiers.new(mod_name, "NODES")
                        mod.node_group = bpy.data.node_groups[color_node_group_name]
                        mod.show_viewport = True
                        mod.show_render = True
                        mod.show_group_selector = False
                        self.report({'INFO'}, f"Added Geometry Nodes modifier: {mod_name}")
                    else:
                        self.report({'WARNING'}, "Could not assign J.CURVEScolor node group.")

        self.report({'INFO'}, "Converted to mesh and materials made local.")
        return {'FINISHED'}


# ---------------------------
# PANEL: J.CURVES
# ---------------------------
class JCurves(bpy.types.Panel):
    bl_label = "J.CURVES"
    bl_idname = "PT_JCurves_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'J.CURVES'

    def draw(self, context):
        layout = self.layout
        props = context.scene.simple_bake_props

        row = layout.row()
        row.scale_y = 1.5
        row.operator('curve.add_jcurve', text="ADD CURVE")

        row = layout.row()
        row.scale_y = 1.5
        row.operator('curve.convert_to_mesh', text="CONVERT TO MESH")

        layout.separator()
        layout.prop(props, "use_existing_colors", text="Use Existing Colors")


# ---------------------------
# REGISTRATION
# ---------------------------
classes = (
    SimpleBakeProps,
    CURVE_OT_ADDJCURVE,
    CURVE_OT_CONVERT_TO_MESH,
    JCurves,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Register property group
    if not hasattr(bpy.types.Scene, "simple_bake_props"):
        bpy.types.Scene.simple_bake_props = bpy.props.PointerProperty(type=SimpleBakeProps)

def unregister():
    # Unregister property first
    if hasattr(bpy.types.Scene, "simple_bake_props"):
        del bpy.types.Scene.simple_bake_props
    
    # Unregister classes
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


# Allow running in text editor
if __name__ == "__main__":
    register()