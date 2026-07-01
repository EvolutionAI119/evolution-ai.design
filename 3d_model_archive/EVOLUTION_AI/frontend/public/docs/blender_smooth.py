"""
Blender Mesh Smoothing Script
Run with: blender --background --python blender_smooth.py
"""
import bpy

# Clean default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Import STL
bpy.ops.import_mesh.stl(filepath=r"D:\API\AI_3D_Model_Build\EVOLUTION_AI\frontend\public\docs\car_body_ultra_smooth.stl")
obj = bpy.context.selected_objects[0]
bpy.context.view_layer.objects.active = obj

# Add Smooth modifier (Laplacian)
bpy.ops.object.modifier_add(type='SMOOTH')
smooth_mod = obj.modifiers[-1]
smooth_mod.iterations = 5
smooth_mod.factor = 0.5

# Add Subdivision Surface for finer detail
bpy.ops.object.modifier_add(type='SUBSURF')
subsurf = obj.modifiers[-1]
subsurf.levels = 1
subsurf.render_levels = 2
subsurf.subdivision_type = 'CATMULL_CLARK'

# Shade smooth
bpy.ops.object.shade_smooth()

# Apply modifiers
bpy.ops.object.modifier_apply(modifier=smooth_mod.name)
bpy.ops.object.modifier_apply(modifier=subsurf.name)

# Export STL
bpy.ops.export_mesh.stl(filepath=r"D:\API\AI_3D_Model_Build\EVOLUTION_AI\frontend\public\docs\car_body_blender_smooth.stl", use_selection=True)

print(f"Blender smoothing complete: D:\API\AI_3D_Model_Build\EVOLUTION_AI\frontend\public\docs\car_body_blender_smooth.stl")
