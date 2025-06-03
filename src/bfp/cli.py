import argparse
import sys
import json # For verbose printing of the results dict

from bfp import analysis
from bfp import serialization # Import the new serialization module

def main():
    parser = argparse.ArgumentParser(
        prog="bfp",
        description="BFP: Blender Filesize Profiler - Analyzes object data sizes in a .blend file.",
        epilog="Example: bfp input.blend --all-objects --verbose --save results.yaml",
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
        help="Save analysis results to a YAML file.",
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

    analysis_data = None
    try:
        analysis_data = analysis.profile_blend_file(
            args.input_path, analyze_all_scene_objects=args.all_objects
        )

        if args.verbose:
            print("[bfp] Profiler finished. Raw analysis data:")
            # Pretty print the dictionary for readability if verbose
            print(json.dumps(analysis_data, indent=2))
        else:
            # Print a concise summary if not verbose
            if analysis_data and analysis_data.get("status") == "success":
                summary = analysis_data.get("summary", {})
                print(f"Analysis Summary for: {analysis_data.get('file_path')}")
                print(f"  Scene: {analysis_data.get('scene_name', 'N/A')}")
                print(f"  Scope: {analysis_data.get('analysis_scope', 'N/A')}")
                print(f"  Objects Analyzed: {summary.get('total_objects_analyzed', 0)}")
                total_size_bytes = summary.get('total_estimated_size_all_objects', 0)
                print(f"  Total Estimated Size: {analysis.format_size(total_size_bytes)}") # Use format_size from analysis
                if analysis_data.get("message"):
                     print(f"  Status: {analysis_data.get('message')}")
            elif analysis_data:
                print(f"Analysis failed: {analysis_data.get('message')}", file=sys.stderr)


    except FileNotFoundError:
        print(f"  Error: Input .blend file '{args.input_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"  Error during Blender processing: {e}", file=sys.stderr)
        print(f"  Ensure the .blend file is valid and Blender's Python environment (bpy) is correctly set up and accessible.")
        sys.exit(1)
    except Exception as e:
        print(f"  An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

    # Save results
    if args.save and analysis_data and analysis_data.get("status") == "success":
        if args.verbose:
            print(f"[bfp] Serializing analysis results to: {args.save}")
        try:
            # The analysis_data from profile_blend_file should be directly serializable
            serialization.serialize_to_yaml(analysis_data, args.save)
        except Exception as e:
            print(f"  Error saving to file '{args.save}': {e}", file=sys.stderr)
            # Decide if this should be a fatal error (sys.exit(1)) or just a warning
            # For now, let it continue and exit normally if analysis itself was okay.
    elif args.save and (not analysis_data or analysis_data.get("status") != "success"):
        print(f"  Skipping YAML serialization due to analysis error or no data.", file=sys.stderr)


    # End
    if args.verbose:
        print("[bfp] CLI finished.")

    if analysis_data and analysis_data.get("status") == "error":
        sys.exit(1) # Exit with error if analysis reported an error
    else:
        sys.exit(0)


def get_project_version():
    try:
        from . import __version__

        return __version__
    except ImportError:
        return "unknown"


if __name__ == "__main__":
    main()
