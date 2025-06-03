import argparse
import sys

from bfp import analysis

def main():
    parser = argparse.ArgumentParser(
        prog="bfp",
        description="BFP: Blender Filesize Profiler - Analyzes object data sizes in a .blend file.",
        epilog="Example: bfp input.blend --all-objects --verbose",
    )

    parser.add_argument(
        "input_path", type=str, help="The required path to the .blend file."
    )

    parser.add_argument(
        "--all-objects",
        action="store_true",
        help="Analyze all objects in the .blend file (bpy.data.objects). If not set, analyzes objects in the current scene (bpy.context.scene.objects).",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output."
    )

    parser.add_argument(
        "-w", "--web", action="store_true", help="Display results in a web viewer (Not yet implemented)."
    )

    parser.add_argument(
        "-s",
        "--save",
        type=str,
        default=None,  # if unprovided
        metavar="FILEPATH",
        help="Save analysis results to a file (Not yet implemented).",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_project_version()}",
        help="Print bfp version.",
    )

    if len(sys.argv) == 1:  # no arguments (just 'bfp')
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    # Start
    if args.verbose:
        print("[bfp] CLI started")
        print(f"[bfp] Analyzing file: {args.input_path}")
        if args.all_objects:
            print("[bfp] Mode: Analyzing all objects in the file.")
        else:
            print("[bfp] Mode: Analyzing objects in the current scene.")

    # Process
    if args.verbose:
        print("[bfp] Handing off to profiler...")
    try:
        # Assuming bfp.py is in the bfp package directory and contains profile_blend_file
        analysis.profile_blend_file(args.input_path, analyze_all_scene_objects=args.all_objects)
    except FileNotFoundError: # More specific error from trying to open the .blend file
        print(f"  Error: Input .blend file '{args.input_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e: # Catch errors from bpy.ops.wm.open_mainfile or other bpy issues
        print(f"  Error during Blender processing: {e}", file=sys.stderr)
        print(f"  Ensure the .blend file is valid and Blender's Python environment (bpy) is correctly set up and accessible.")
        sys.exit(1)
    except Exception as e: # Catch any other unexpected errors
        print(f"  An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


    # Display section is now handled by profile_blend_file's print statements.
    # The placeholder file reading logic below is no longer needed.
    # try:
    #     with open(args.input_path, "r") as f: # This would fail for a .blend file anyway
    #         content_preview = f.read(100)  # Read first 100 chars
    #         print(f"  First 100 chars of input: '{content_preview}...'\n")
    # except FileNotFoundError:
    #     print(f"  Error: Input file '{args.input_path}' not found.", file=sys.stderr)
    #     sys.exit(1)
    # except IOError as e:
    #     print(
    #         f"  Error: Could not read input file '{args.input_path}': {e}",
    #         file=sys.stderr,
    #     )
    #     sys.exit(1)

    # End
    if args.verbose:
        print("[bfp] CLI finished.")
    sys.exit(0)


def get_project_version():
    try:
        from . import __version__

        return __version__
    except ImportError:
        return "unknown"


if __name__ == "__main__":
    main()
