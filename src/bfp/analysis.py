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
    """Analyzes a single Blender object and prints its estimated data footprint."""
    print(f'\n--- Object: "{obj.name}" (Type: {obj.type}) ---')

    total_object_estimated_size = 0
    mesh_data_original_size = 0
    mesh_data_evaluated_size = 0
    textures_total_size = 0

    if obj.type == "MESH":
        # --- Original Mesh Data (before modifiers) ---
        mesh = obj.data
        print(f'  Mesh Data (Original): "{mesh.name}"')
        print(f"    Vertices: {len(mesh.vertices)}")
        print(f"    Edges: {len(mesh.edges)}")
        print(f"    Polygons: {len(mesh.polygons)}")
        print(f"    UV Layers: {len(mesh.uv_layers)}")
        print(f"    Vertex Colors: {len(mesh.vertex_colors)}")

        mesh_data_original_size = estimate_mesh_data_size(mesh)
        total_object_estimated_size += mesh_data_original_size
        print(f"    Estimated Raw Mesh Size: {format_size(mesh_data_original_size)}")
        if mesh.users > 1:
            print(
                f"    * Note: This mesh data ('{mesh.name}') is used by {mesh.users} objects."
            )

        # --- Modifiers ---
        if obj.modifiers:
            print(f"  Modifiers ({len(obj.modifiers)}):")
            for mod in obj.modifiers:
                print(
                    f'    - "{mod.name}" (Type: {mod.type}, Show in Viewport: {mod.show_viewport})'
                )
        else:
            print("  Modifiers: None")

        # --- Evaluated Mesh Data (after modifiers) ---
        print("  Evaluated Mesh Data (After Modifiers):")
        eval_mesh_verts_count_str = 'N/A'
        eval_mesh_polys_count_str = 'N/A'
        try:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            eval_obj = obj.evaluated_get(depsgraph)
            # For some object types, .data might not be a mesh directly after evaluation
            # or it might be an instance. to_mesh() creates a new mesh.
            eval_mesh = eval_obj.to_mesh(
                preserve_all_data_layers=True, depsgraph=depsgraph
            )
            if eval_mesh:
                eval_mesh_verts_count_str = str(len(eval_mesh.vertices))
                eval_mesh_polys_count_str = str(len(eval_mesh.polygons))
                print(f"    Vertices: {eval_mesh_verts_count_str}")
                print(f"    Polygons: {eval_mesh_polys_count_str}")
                mesh_data_evaluated_size = estimate_mesh_data_size(eval_mesh)
                # This evaluated mesh size isn't added to total_object_estimated_size directly
                # as it's a result of the original mesh + modifiers, not separate stored data.
                # However, it's a good indicator of render-time complexity.
                print(
                    f"    Estimated Evaluated Mesh Size (indicative): {format_size(mesh_data_evaluated_size)}"
                )
                eval_obj.to_mesh_clear()  # Clean up the temporary mesh
            else:
                print(
                    "    Could not convert evaluated object to mesh for stats (e.g., for curves not converted)."
                )
        except Exception as e:
            print(f"    Could not evaluate mesh: {e}")
            print(
                f"    (Original mesh stats will be used for total if evaluation fails)"
            )
            mesh_data_evaluated_size = mesh_data_original_size  # Fallback for summary

    elif obj.type == "CURVE":
        curve = obj.data
        print(f'  Curve Data: "{curve.name}"')
        num_points = sum(
            len(spline.points) for spline in curve.splines if hasattr(spline, "points")
        )
        num_bezier_points = sum(
            len(spline.bezier_points)
            for spline in curve.splines
            if hasattr(spline, "bezier_points")
        )
        print(f"    Splines: {len(curve.splines)}")
        if num_points > 0:
            print(f"    Total Points (Poly/NURBS): {num_points}")
        if num_bezier_points > 0:
            print(f"    Total Bezier Points: {num_bezier_points}")
        # Curve data size is harder to generalize simply, depends on point types etc.
        # A rough estimate:
        curve_data_size = (num_points * 3 * SIZEOF_FLOAT) + (
            num_bezier_points * 9 * SIZEOF_FLOAT
        )  # handle, point, handle
        total_object_estimated_size += curve_data_size
        print(f"    Estimated Curve Points Size: {format_size(curve_data_size)}")
        if curve.users > 1:
            print(
                f"    * Note: This curve data ('{curve.name}') is used by {curve.users} objects."
            )

    elif obj.type == "LIGHT":
        light = obj.data
        print(f'  Light Data: "{light.name}" (Type: {light.type})')
        print(f"    Energy: {light.energy}")
        # Light data itself is small, mostly parameters.

    # Add more object type handlers here if needed (ARMATURE, LATTICE, FONT, etc.)

    # --- Materials and Textures ---
    if obj.material_slots:
        print(f"  Materials ({len(obj.material_slots)}):")
        slot_textures_total_size = 0
        for slot_index, slot in enumerate(obj.material_slots):
            if slot.material:
                mat = slot.material
                print(f'    Slot [{slot_index}]: "{mat.name}"')
                if mat.users > 1:
                    print(
                        f"      * Note: This material ('{mat.name}') is used by {mat.users} objects/slots."
                    )

                material_textures_size = 0
                if mat.use_nodes and mat.node_tree:
                    texture_nodes_in_mat = []
                    for node in mat.node_tree.nodes:
                        if node.type == "TEX_IMAGE":
                            if node.image:
                                img = node.image
                                texture_nodes_in_mat.append(img)

                                # Estimate image size (uncompressed)
                                # depth is per channel bit depth (e.g., 8 for 8-bit, 32 for float)
                                channels = img.channels
                                bits_per_channel = (
                                    img.depth // channels
                                    if img.depth >= channels and channels > 0
                                    else img.depth
                                )  # Heuristic for packed formats
                                if channels == 0:
                                    channels = (
                                        4  # Default if unknown, e.g. for .hdr sometimes
                                    )
                                if bits_per_channel == 0:
                                    bits_per_channel = 8  # Default if unknown

                                img_size = (
                                    img.size[0]
                                    * img.size[1]
                                    * channels
                                    * (bits_per_channel / 8)
                                )
                                material_textures_size += img_size

                                print(f'      - Image Texture: "{img.name}"')
                                print(f"          Source: {img.source}")
                                if img.packed_file:
                                    print(
                                        f"          Packed: Yes (Size: {format_size(img.packed_file.size)})"
                                    )
                                else:
                                    print(
                                        f"          Filepath: {img.filepath_from_user()}"
                                    )
                                print(
                                    f"          Dimensions: {img.size[0]}x{img.size[1]}, Channels: {channels}, Bit Depth: {bits_per_channel} per channel"
                                )
                                print(
                                    f"          Estimated Raw Texture Size: {format_size(img_size)}"
                                )
                                if img.users > 1:
                                    print(
                                        f"          * Note: This image data ('{img.name}') is used by {img.users} users (nodes/textures)."
                                    )

                    if not texture_nodes_in_mat:
                        print("      - No Image Texture nodes found in this material.")

                slot_textures_total_size += material_textures_size
                if material_textures_size > 0:
                    print(
                        f'    Estimated Textures Size for "{mat.name}": {format_size(material_textures_size)}'
                    )

            else:
                print(f"    Slot [{slot_index}]: Empty")

        textures_total_size = slot_textures_total_size
        total_object_estimated_size += textures_total_size
        if textures_total_size > 0:
            print(
                f"  Total Estimated Textures Size for this object: {format_size(textures_total_size)}"
            )
    else:
        print("  Materials: None")

    # --- Particle Systems ---
    if obj.particle_systems:
        print(f"  Particle Systems ({len(obj.particle_systems)}):")
        for psys_idx, psys in enumerate(obj.particle_systems):
            settings = psys.settings
            print(f'    System [{psys_idx}]: "{psys.name}" (Type: {settings.type})')
            print(
                f"      Count: {settings.count} (Viewport: {settings.display_percentage}%)"
            )
            # Estimating particle data size is complex: depends on instance type, hair data, physics cache etc.
            # This is a very rough placeholder, as actual memory is much more involved.
            particle_base_size = settings.count * (3 * SIZEOF_FLOAT)  # Position
            if settings.type == "HAIR":
                particle_base_size += (
                    settings.count * settings.hair_step * (3 * SIZEOF_FLOAT)
                )  # Segments
            print(
                f"      Rough Estimated Base Particle Data Size: {format_size(particle_base_size)}"
            )
            total_object_estimated_size += (
                particle_base_size  # Add with caution, very approximate
            )
            if settings.users > 1:
                print(
                    f"      * Note: These particle settings ('{settings.name}') are used by {settings.users} systems."
                )

    print(
        f'\n  Estimated Total for "{obj.name}" (Original Mesh/Curve + Textures + Basic Particles): {format_size(total_object_estimated_size)}'
    )
    if obj.type == "MESH":
        print(
            f"    (Evaluated mesh complexity: Verts={eval_mesh_verts_count_str}, Polys={eval_mesh_polys_count_str})"
        )


def profile_blend_file(blend_file_path: str, analyze_all_scene_objects: bool = False):
    """
    Opens a .blend file and analyzes its objects.

    :param blend_file_path: Path to the .blend file.
    :param analyze_all_scene_objects: If True, analyzes all objects in bpy.data.objects.
                                      If False (default), analyzes objects in the current scene (bpy.context.scene.objects).
    :raises RuntimeError: If the .blend file cannot be opened.
    """
    print(f"Starting Object Data Profiler for: {blend_file_path}")

    try:
        bpy.ops.wm.open_mainfile(filepath=blend_file_path)
        print(f"Successfully opened: {blend_file_path}")
    except RuntimeError as e:
        print(f"Error opening .blend file '{blend_file_path}': {e}")
        print(
            "Please ensure Blender is installed and `bpy` can operate, or Blender is run in background mode if required."
        )
        raise  # Re-raise the exception to be handled by the caller (e.g., cli.py)

    objects_to_analyze = []
    if analyze_all_scene_objects:
        print("Analyzing all objects found in bpy.data.objects.")
        objects_to_analyze = list(bpy.data.objects)
    else:
        if bpy.context.scene:
            print(f"Analyzing objects in the current scene: {bpy.context.scene.name}")
            objects_to_analyze = list(bpy.context.scene.objects)
        else:
            print(
                "No active scene found after loading .blend file. Cannot analyze scene objects."
            )
            print(
                "Consider using the option to analyze all objects in the file if appropriate."
            )
            # Or raise an error, or return an empty result/status
            return  # Or raise ValueError("No active scene to analyze")

    if not objects_to_analyze:
        print("No objects found to analyze based on the criteria.")
    else:
        print(f"Analyzing {len(objects_to_analyze)} object(s):")
        for obj in objects_to_analyze:
            analyze_object(obj)  # analyze_object is defined in this file

    # The disclaimers previously in __main__ can be handled by the CLI if needed.
    # For example, by returning structured data from this function and having the CLI print summaries.
    print(f"\n--- Analysis complete for {blend_file_path} ---")
