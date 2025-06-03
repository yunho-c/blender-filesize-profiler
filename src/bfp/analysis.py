import bpy
import math

# Parameters
# assumed sizes in bytes for primitive types
SIZEOF_FLOAT = 4  # vertex coordinates, UVs, color components
SIZEOF_INT = 4  # indices


def format_size(size_bytes):
    """Helper function to format bytes into KB, MB, GB"""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def estimate_mesh_data_size(mesh):
    """Estimates the size of various mesh components."""
    size = 0

    # Vertex coordinates (x, y, z)
    size += len(mesh.vertices) * 3 * SIZEOF_FLOAT

    # Edge data (connecting 2 vertex indices)
    size += len(mesh.edges) * 2 * SIZEOF_INT

    # Loop data (vertex index, edge index per loop)
    # Loops are fundamental to how Blender stores per-face-vertex data
    size += len(mesh.loops) * 2 * SIZEOF_INT

    # Polygon data (loop start, loop total, material index)
    size += len(mesh.polygons) * 3 * SIZEOF_INT  # Approx.

    # UV Layers
    for uv_layer in mesh.uv_layers:
        size += (
            len(uv_layer.data) * 2 * SIZEOF_FLOAT
        )  # Each UV entry has 2 floats (u,v)

    # Vertex Color Layers
    for vc_layer in mesh.vertex_colors:
        # Each color entry has 4 floats (r,g,b,a) per loop vertex
        size += len(vc_layer.data) * 4 * SIZEOF_FLOAT

    # CustomData Layers (normals, etc.) - this is a simplification
    # Blender's customdata system is complex. This is a rough pass.
    # Often normals are stored per-loop.
    if mesh.has_custom_normals:
        size += len(mesh.loops) * 3 * SIZEOF_FLOAT  # Assuming 3 floats per normal

    return size


def analyze_object(obj):
    """Analyzes a single Blender object and returns its estimated data footprint as a dictionary."""
    obj_data = {
        "name": obj.name,
        "type": obj.type,
        "total_estimated_size": 0,
        "mesh_data": None,
        "curve_data": None,
        "light_data": None,
        "materials": [],
        "particle_systems": [],
    }

    total_object_estimated_size = 0

    if obj.type == "MESH":
        mesh = obj.data
        mesh_info = {
            "name": mesh.name,
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
            "uv_layers": len(mesh.uv_layers),
            "vertex_colors": len(mesh.vertex_colors),
            "users": mesh.users,
            "estimated_size_bytes": 0,
            "modifiers": [],
            "evaluated_mesh": None,
        }

        mesh_data_original_size = estimate_mesh_data_size(mesh)
        mesh_info["estimated_size_bytes"] = mesh_data_original_size
        total_object_estimated_size += mesh_data_original_size

        if obj.modifiers:
            for mod in obj.modifiers:
                mesh_info["modifiers"].append(
                    {"name": mod.name, "type": mod.type, "show_viewport": mod.show_viewport}
                )

        eval_mesh_data = {
            "vertices": "N/A",
            "polygons": "N/A",
            "estimated_size_bytes": 0,
            "error": None,
        }
        mesh_data_evaluated_size = 0
        try:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            eval_obj = obj.evaluated_get(depsgraph)
            eval_mesh = eval_obj.to_mesh(
                preserve_all_data_layers=True, depsgraph=depsgraph
            )
            if eval_mesh:
                eval_mesh_data["vertices"] = len(eval_mesh.vertices)
                eval_mesh_data["polygons"] = len(eval_mesh.polygons)
                mesh_data_evaluated_size = estimate_mesh_data_size(eval_mesh)
                eval_mesh_data["estimated_size_bytes"] = mesh_data_evaluated_size
                eval_obj.to_mesh_clear()
            else:
                eval_mesh_data["error"] = "Could not convert evaluated object to mesh"
        except Exception as e:
            eval_mesh_data["error"] = str(e)
            mesh_data_evaluated_size = mesh_data_original_size # Fallback

        mesh_info["evaluated_mesh"] = eval_mesh_data
        obj_data["mesh_data"] = mesh_info

    elif obj.type == "CURVE":
        curve = obj.data
        num_points = sum(
            len(spline.points) for spline in curve.splines if hasattr(spline, "points")
        )
        num_bezier_points = sum(
            len(spline.bezier_points)
            for spline in curve.splines
            if hasattr(spline, "bezier_points")
        )
        curve_data_size = (num_points * 3 * SIZEOF_FLOAT) + (
            num_bezier_points * 9 * SIZEOF_FLOAT
        )
        total_object_estimated_size += curve_data_size

        obj_data["curve_data"] = {
            "name": curve.name,
            "splines": len(curve.splines),
            "total_points_poly_nurbs": num_points if num_points > 0 else 0,
            "total_bezier_points": num_bezier_points if num_bezier_points > 0 else 0,
            "estimated_size_bytes": curve_data_size,
            "users": curve.users,
        }

    elif obj.type == "LIGHT":
        light = obj.data
        obj_data["light_data"] = {
            "name": light.name,
            "type": light.type,
            "energy": light.energy,
            # Light data itself is small, mostly parameters. Size impact is negligible.
            "estimated_size_bytes": 0
        }

    # Materials and Textures
    if obj.material_slots:
        materials_list = []
        object_textures_total_size = 0
        for slot_index, slot in enumerate(obj.material_slots):
            mat_data = {"slot_index": slot_index, "name": "Empty", "textures": [], "estimated_textures_size_bytes": 0, "users": 0}
            if slot.material:
                mat = slot.material
                mat_data["name"] = mat.name
                mat_data["users"] = mat.users

                material_textures_size = 0
                textures_in_mat_list = []
                if mat.use_nodes and mat.node_tree:
                    for node in mat.node_tree.nodes:
                        if node.type == "TEX_IMAGE" and node.image:
                            img = node.image
                            channels = img.channels
                            bits_per_channel = (
                                img.depth // channels
                                if img.depth >= channels and channels > 0
                                else img.depth
                            )
                            if channels == 0: channels = 4
                            if bits_per_channel == 0: bits_per_channel = 8

                            img_size = (
                                img.size[0] * img.size[1] * channels * (bits_per_channel / 8)
                            )
                            material_textures_size += img_size

                            textures_in_mat_list.append({
                                "name": img.name,
                                "source": img.source,
                                "packed": bool(img.packed_file),
                                "packed_size_bytes": img.packed_file.size if img.packed_file else 0,
                                "filepath": img.filepath_from_user(),
                                "dimensions": [img.size[0], img.size[1]],
                                "channels": channels,
                                "bit_depth_per_channel": bits_per_channel,
                                "estimated_raw_size_bytes": img_size,
                                "users": img.users,
                            })
                mat_data["textures"] = textures_in_mat_list
                mat_data["estimated_textures_size_bytes"] = material_textures_size
                object_textures_total_size += material_textures_size
            materials_list.append(mat_data)
        obj_data["materials"] = materials_list
        total_object_estimated_size += object_textures_total_size

    # Particle Systems
    if obj.particle_systems:
        particle_systems_list = []
        object_particles_total_size = 0
        for psys_idx, psys in enumerate(obj.particle_systems):
            settings = psys.settings
            particle_base_size = settings.count * (3 * SIZEOF_FLOAT)  # Position
            if settings.type == "HAIR":
                particle_base_size += (
                    settings.count * settings.hair_step * (3 * SIZEOF_FLOAT)
                )
            object_particles_total_size += particle_base_size
            particle_systems_list.append({
                "name": psys.name,
                "type": settings.type,
                "count": settings.count,
                "display_percentage": settings.display_percentage,
                "estimated_base_size_bytes": particle_base_size,
                "settings_users": settings.users,
            })
        obj_data["particle_systems"] = particle_systems_list
        total_object_estimated_size += object_particles_total_size

    obj_data["total_estimated_size"] = total_object_estimated_size
    return obj_data


def profile_blend_file(blend_file_path: str, analyze_all_scene_objects: bool = False):
    """
    Opens a .blend file and analyzes its objects, returning structured data.

    :param blend_file_path: Path to the .blend file.
    :param analyze_all_scene_objects: If True, analyzes all objects in bpy.data.objects.
                                      If False (default), analyzes objects in the current scene (bpy.context.scene.objects).
    :return: A dictionary containing the analysis results or an error message.
    :raises RuntimeError: If the .blend file cannot be opened (re-raised).
    """
    analysis_result = {
        "file_path": blend_file_path,
        "status": "success",
        "message": "",
        "scene_name": None,
        "analysis_scope": "",
        "objects": [],
        "summary": {
            "total_objects_analyzed": 0,
            "total_estimated_size_all_objects": 0,
            # More summary fields can be added here
        }
    }

    try:
        bpy.ops.wm.open_mainfile(filepath=blend_file_path)
        analysis_result["message"] = f"Successfully opened: {blend_file_path}"
    except RuntimeError as e:
        analysis_result["status"] = "error"
        analysis_result["message"] = f"Error opening .blend file '{blend_file_path}': {e}. " \
                                     "Ensure Blender is installed and `bpy` can operate, " \
                                     "or Blender is run in background mode if required."
        # It's better to let the caller handle the exception if it's critical
        raise

    objects_to_analyze = []
    if analyze_all_scene_objects:
        analysis_result["analysis_scope"] = "all_data_objects"
        objects_to_analyze = list(bpy.data.objects)
    else:
        if bpy.context.scene:
            analysis_result["scene_name"] = bpy.context.scene.name
            analysis_result["analysis_scope"] = f"scene_objects ({bpy.context.scene.name})"
            objects_to_analyze = list(bpy.context.scene.objects)
        else:
            analysis_result["status"] = "error"
            analysis_result["message"] = "No active scene found. Cannot analyze scene objects. " \
                                         "Consider using the option to analyze all objects."
            return analysis_result # Return early with error

    if not objects_to_analyze:
        analysis_result["message"] += " No objects found to analyze based on the criteria."
        # Not necessarily an error, could be an empty scene.
    else:
        analysis_result["message"] += f" Analyzing {len(objects_to_analyze)} object(s)."
        collected_objects_data = []
        total_size_sum = 0
        for obj in objects_to_analyze:
            obj_data = analyze_object(obj) # analyze_object now returns a dict
            collected_objects_data.append(obj_data)
            total_size_sum += obj_data.get("total_estimated_size", 0)

        analysis_result["objects"] = collected_objects_data
        analysis_result["summary"]["total_objects_analyzed"] = len(collected_objects_data)
        analysis_result["summary"]["total_estimated_size_all_objects"] = total_size_sum

    analysis_result["message"] += f" Analysis complete for {blend_file_path}."
    return analysis_result
