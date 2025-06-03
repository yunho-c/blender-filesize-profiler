import argparse
import sys
import json

from bfp import analysis
from bfp import serialization
from bfp.visualization import visualize_sunburst


def main():
    parser = argparse.ArgumentParser(
        prog="bfp",
        description="BFP: Blender Filesize Profiler - Analyzes object data sizes in .blend files and can visualize results.",
        epilog="Examples:\n"
               "  bfp scene.blend\n"
               "  bfp scene.blend --all-objects --verbose --save results.yaml\n"
               "  bfp scene.blend --web\n"
               "  bfp results.yaml (visualizes a previously saved analysis)\n",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "input_path", type=str, help="Path to the .blend file for analysis or .yaml file for visualization."
    )
    parser.add_argument(
        "--all-objects",
        action="store_true",
        help="When analyzing a .blend file, analyze all objects (bpy.data.objects). Default is current scene.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output."
    )
    parser.add_argument(
        "-w",
        "--web",
        action="store_true",
        help="Display analysis results as a sunburst chart in a web browser. If input is .blend, analysis is run first.",
    )
    parser.add_argument(
        "-s",
        "--save",
        type=str,
        default=None,
        metavar="FILEPATH",
        help="Save analysis results (from .blend file) to a YAML file. Ignored if input is already YAML.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_project_version()}",
        help="Print bfp version.",
    )

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    analysis_data = None
    input_is_yaml = args.input_path.lower().endswith((".yaml", ".yml"))

    if input_is_yaml:
        if args.verbose:
            print(f"[bfp] CLI: Input is YAML file: {args.input_path}. Proceeding to visualization.")
        # Directly visualize if --web is implicitly true for YAML, or explicitly set
        visualize_sunburst(args.input_path, verbose=args.verbose, is_filepath=True)
        sys.exit(0) # visualize_sunburst now calls sys.exit, but good to be explicit.

    # If not YAML, it must be a .blend file for analysis
    if args.verbose:
        print("[bfp] CLI: Input is .blend file. Performing analysis.")
        print(f"[bfp] Analyzing file: {args.input_path}")
        if args.all_objects:
            print("[bfp] Mode: Analyzing all objects in the file.")
        else:
            print("[bfp] Mode: Analyzing objects in the current scene.")

    try:
        analysis_data = analysis.profile_blend_file(
            args.input_path, analyze_all_scene_objects=args.all_objects
        )

        if args.verbose:
            print("[bfp] Profiler finished. Raw analysis data:")
            print(json.dumps(analysis_data, indent=2))
        else:
            if analysis_data and analysis_data.get("status") == "success":
                summary = analysis_data.get("summary", {})
                print(f"Analysis Summary for: {analysis_data.get('file_path')}")
                print(f"  Scene: {analysis_data.get('scene_name', 'N/A')}")
                print(f"  Scope: {analysis_data.get('analysis_scope', 'N/A')}")
                print(f"  Objects Analyzed: {summary.get('total_objects_analyzed', 0)}")
                total_size_bytes = summary.get('total_estimated_size_all_objects', 0)
                print(f"  Total Estimated Size: {analysis.format_size(total_size_bytes)}")
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

    if args.save and analysis_data and analysis_data.get("status") == "success":
        if args.verbose:
            print(f"[bfp] Serializing analysis results to: {args.save}")
        try:
            serialization.serialize_to_yaml(analysis_data, args.save)
        except Exception as e:
            print(f"  Error saving to file '{args.save}': {e}", file=sys.stderr)
    elif args.save and (not analysis_data or analysis_data.get("status") != "success"):
        print(f"  Skipping YAML serialization due to analysis error or no data.", file=sys.stderr)

    if args.web and analysis_data and analysis_data.get("status") == "success":
        if args.verbose:
            print("[bfp] CLI: --web flag is set. Visualizing analysis results.")
        visualize_sunburst(analysis_data, verbose=args.verbose, is_filepath=False)
        # visualize_sunburst calls sys.exit()

    if args.verbose:
        print("[bfp] CLI finished.")

    if analysis_data and analysis_data.get("status") == "error":
        sys.exit(1)
    elif not args.web: # If not web, and no error, exit 0 (web exits via visualize_sunburst)
        sys.exit(0)


def get_project_version():
    try:
        from . import __version__

        return __version__
    except ImportError:
        return "unknown"


if __name__ == "__main__":
    main()
