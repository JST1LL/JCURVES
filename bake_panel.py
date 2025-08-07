import bpy
from bpy.props import EnumProperty, IntProperty, BoolProperty, PointerProperty

# SETTINGS
class JCurvesBakeProps(bpy.types.PropertyGroup):
    resolution: EnumProperty(
        name="Resolution",
        description="Resolution for the new baked image",
        items=[
            ('1024', '1024', '1024x1024'),
            ('2048', '2048', '2048x2048'),
            ('4096', '4096', '4096x4096'),
            ('8192', '8192', '8192x8192'),
        ],
        default='2048',
    )

    max_samples: IntProperty(
        name="Max Samples",
        description="Render samples for baking (Cycles)",
        default=1,
        min=1,
        max=10000
    )

    denoise: BoolProperty(
        name="Denoise After Bake",
        description="Apply denoising to the baked image",
        default=False
    )

    bake_margin: IntProperty(
        name="Bake Margin",
        description="Number of pixels to extend the bake beyond UVs",
        default=8,
        min=0,
        max=100
    )

    clear_image: BoolProperty(
        name="Clear Image Before Bake",
        description="Clear image to background color before baking",
        default=True
    )

    bake_to_selected_image: BoolProperty(
        name="Bake to Selected Image",
        description="Bake directly to the currently selected image instead of creating a new one",
        default=False,
    )

    show_advanced: BoolProperty(
        name="Advanced Bake Settings",
        description="Toggle to show advanced options",
        default=False
    )


# BAKE IMAGE
class MATERIAL_OT_bake_image(bpy.types.Operator):
    bl_idname = "material.bake_image"
    bl_label = "Bake Image"
    bl_description = "Create a new image and bake texture color to it"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.jcurves_bake_props
        resolution = int(props.resolution)

        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object selected.")
            return {'CANCELLED'}

        mat = obj.active_material
        if not mat or not mat.use_nodes:
            self.report({'ERROR'}, "Active material has no node tree.")
            return {'CANCELLED'}

        scene = context.scene

        # SAVE RENDER ENGINE AND DEVICE
        original_engine = scene.render.engine
        original_device = scene.cycles.device

        # SWITCH TO CYCLES
        if scene.render.engine != 'CYCLES':
            scene.render.engine = 'CYCLES'

        # SWITCH RENDER DEVICE
        scene.cycles.device = 'GPU'

        # DECIDE WHICH IMAGE TO BAKE TO
        image = None

        if props.bake_to_selected_image:
            # Try to get image from Image Editor
            for area in context.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    if area.spaces.active.image:
                        image = area.spaces.active.image
                        break

            # Fallback: get image from active texture node
            if not image:
                active_node = mat.node_tree.nodes.active
                if active_node and active_node.type == 'TEX_IMAGE' and active_node.image:
                    image = active_node.image

            if not image:
                self.report({'ERROR'}, "No image selected in Image Editor or active node.")
                return {'CANCELLED'}

            # Ensure image is correct resolution (optional)
            if image.size[0] != resolution or image.size[1] != resolution:
                self.report({'WARNING'}, f"Selected image is {image.size[0]}x{image.size[1]}, but bake resolution is {resolution}x{resolution}. Using selected image anyway.")

        else:
            # Create new image
            image_name = f"{mat.name}_Baked_{resolution}x{resolution}"
            image = bpy.data.images.new(
                name=image_name,
                width=resolution,
                height=resolution,
                alpha=True,
                float_buffer=False
            )
            image.generated_color = (0.0, 0.0, 0.0, 1.0)
            self.report({'INFO'}, f"Created image: {image_name}")

        # CREATE IMAGE TEXTURE NODE
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        bake_node = nodes.new(type='ShaderNodeTexImage')
        bake_node.image = image
        bake_node.label = "Baked Image"
        bake_node.location = (0, 0)

        # Select and make active
        for node in nodes:
            node.select = False
        bake_node.select = True
        nodes.active = bake_node

        # SAVE & APPLY BAKE SETTINGS
        old_samples = scene.cycles.samples
        old_denoise = scene.cycles.use_denoising
        old_margin = scene.render.bake.margin
        old_clear = scene.render.bake.use_clear
        old_bake_type = scene.cycles.bake_type
        
        # Updated bake pass settings for newer Blender versions
        old_use_diffuse = scene.render.bake.use_pass_diffuse
        if hasattr(scene.render.bake, 'use_pass_direct'):
            old_use_direct = scene.render.bake.use_pass_direct
            old_use_indirect = scene.render.bake.use_pass_indirect
        else:
            old_use_direct = old_use_indirect = None

        scene.cycles.samples = props.max_samples
        scene.cycles.use_denoising = props.denoise
        scene.render.bake.margin = props.bake_margin
        scene.render.bake.use_clear = props.clear_image
        scene.cycles.bake_type = 'DIFFUSE'
        scene.render.bake.use_pass_diffuse = True
        if hasattr(scene.render.bake, 'use_pass_direct'):
            scene.render.bake.use_pass_direct = False
            scene.render.bake.use_pass_indirect = False

        # RUN BAKE
        try:
            bpy.ops.object.bake(type='DIFFUSE')
            self.report({'INFO'}, "Baking completed (Diffuse color only).")
        except RuntimeError as e:
            self.report({'ERROR'}, f"Baking failed: {e}")
            if not props.bake_to_selected_image:
                bpy.data.images.remove(image)
            nodes.remove(bake_node)
            self._restore_bake_settings(context, old_samples, old_denoise, old_margin,
                                       old_clear, old_bake_type, old_use_diffuse, 
                                       old_use_direct, old_use_indirect)
            scene.render.engine = original_engine
            scene.cycles.device = original_device
            return {'CANCELLED'}

        # RESTORE SETTINGS
        self._restore_bake_settings(context, old_samples, old_denoise, old_margin,
                                   old_clear, old_bake_type, old_use_diffuse,
                                   old_use_direct, old_use_indirect)

        scene.render.engine = original_engine
        scene.cycles.device = original_device

        # Final report
        action = "Baked to existing image" if props.bake_to_selected_image else "Created and baked to new image"
        self.report({'INFO'}, f"{action}: {image.name}")
        context.area.tag_redraw()

        return {'FINISHED'}

    def _restore_bake_settings(self, context, samples, denoise, margin, clear, btype, 
                              use_diffuse, use_direct, use_indirect):
        scene = context.scene
        scene.cycles.samples = samples
        scene.cycles.use_denoising = denoise
        scene.render.bake.margin = margin
        scene.render.bake.use_clear = clear
        scene.cycles.bake_type = btype
        scene.render.bake.use_pass_diffuse = use_diffuse
        if use_direct is not None:
            scene.render.bake.use_pass_direct = use_direct
        if use_indirect is not None:
            scene.render.bake.use_pass_indirect = use_indirect


# PANEL
class JCURVES_PT_bake_panel(bpy.types.Panel):
    bl_label = "Bake HairCards"
    bl_idname = "JCURVES_PT_bake_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'J.CURVES'
    bl_parent_id = "PT_JCurves_panel"
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        props = context.scene.jcurves_bake_props

        layout.label(text="Image Resolution")
        layout.prop(props, "resolution", text="")

        layout.operator("material.bake_image", text="Bake Image", icon='IMAGE_DATA')

        box = layout.box()
        row = box.row()
        row.alignment = 'LEFT'
        icon = 'DOWNARROW_HLT' if props.show_advanced else 'RIGHTARROW'
        row.prop(props, "show_advanced", text="Advanced Settings", icon=icon, emboss=False)

        if props.show_advanced:
            col = box.column()
            col.use_property_split = True
            col.use_property_decorate = False
            col.prop(props, "max_samples")
            col.prop(props, "denoise")
            col.prop(props, "bake_margin")
            col.prop(props, "clear_image")
            col.prop(props, "bake_to_selected_image")


# REGISTRATION
classes = (
    JCurvesBakeProps,
    MATERIAL_OT_bake_image,
    JCURVES_PT_bake_panel,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    if not hasattr(bpy.types.Scene, "jcurves_bake_props"):
        bpy.types.Scene.jcurves_bake_props = PointerProperty(type=JCurvesBakeProps)

def unregister():
    from bpy.utils import unregister_class
    if hasattr(bpy.types.Scene, "jcurves_bake_props"):
        del bpy.types.Scene.jcurves_bake_props
    for cls in reversed(classes):
        unregister_class(cls)
        
if __name__ == "__main__":
    register()