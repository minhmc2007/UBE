# UnityPy Bundle Tool
# A script for extracting and repacking Unity asset bundles.
#
# Developer: minhmc2007
# GitHub:    https://github.com/minhmc2007

import UnityPy
import os
import sys
import json
from PIL import Image
import argparse
import threading
import time

# Spinner Animation Class (Metasploit-style)
class Spinner:
    def __init__(self, message="Loading"):
        self.spinner_chars = ['-', '\\', '|', '/']
        self.base_message = message.lower()
        self.spinning = False
        self.thread = None
        self.idx = 0

    def _get_animated_text(self):
        """Creates the letter-by-letter capitalization effect"""
        if not self.base_message:
            return self.base_message
        
        # Get which letter to capitalize based on animation frame
        letter_idx = (self.idx // 2) % len(self.base_message)  # Slower letter animation
        
        animated_text = ""
        for i, char in enumerate(self.base_message):
            if i == letter_idx and char.isalpha():
                animated_text += char.upper()
            else:
                animated_text += char.lower()
        
        return animated_text

    def _spin(self):
        while self.spinning:
            animated_message = self._get_animated_text()
            spinner_char = self.spinner_chars[self.idx % len(self.spinner_chars)]
            sys.stdout.write(f'\r{animated_message} {spinner_char}')
            sys.stdout.flush()
            self.idx += 1
            time.sleep(0.15)  # Slightly slower for better visual effect

    def start(self):
        self.spinning = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()

    def stop(self, final_message=None):
        self.spinning = False
        if self.thread:
            self.thread.join()
        if final_message:
            sys.stdout.write(f'\r{final_message}\n')
        else:
            sys.stdout.write(f'\r{self.base_message} ✓\n')
        sys.stdout.flush()

# Helper Functions
def ensure_dir(directory):
    """Ensures that the specified directory exists, creating it if necessary."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: '{directory}'")

def sanitize_name(name):
    """Sanitizes a name to be used as a filename by removing invalid characters."""
    if not name:
        return ""
    return "".join(c for c in name if c.isalnum() or c in (' ', '.', '_', '-')).rstrip().strip()

# Extraction Function
def extract_bundle(bundle_path, output_dir):
    """Extracts assets from a Unity .bundle file into categorized subdirectories."""
    print(f"\n=== Extracting Bundle ===\nInput: '{bundle_path}'\nOutput Directory: '{output_dir}'")
    ensure_dir(output_dir)

    # Start spinner for UnityPy loading
    spinner = Spinner("Loading UnityPy")
    spinner.start()

    # Load the bundle
    try:
        env = UnityPy.load(bundle_path)
        spinner.stop("Loading UnityPy ✓")
    except Exception as e:
        spinner.stop("Loading UnityPy ✗")
        print(f"ERROR: Failed to load bundle '{bundle_path}'.\nDetails: {e}")
        print("The file might be corrupted, protected, or not a valid Unity bundle.")
        sys.exit(1)

    # Start spinner for extraction process
    extraction_spinner = Spinner("Extracting bundle")
    extraction_spinner.start()

    # Initialize manifest to track extracted assets
    manifest = {
        "original_bundle_path": os.path.abspath(bundle_path),
        "assets": []
    }

    # Define subdirectories for asset types
    dirs = {
        "Textures": os.path.join(output_dir, "Textures"),
        "TextAssets": os.path.join(output_dir, "TextAssets"),
        "MonoBehaviours_JSON": os.path.join(output_dir, "MonoBehaviours_JSON"),
        "MonoBehaviours_DAT": os.path.join(output_dir, "MonoBehaviours_DAT"),
        "AudioClips": os.path.join(output_dir, "AudioClips"),
        "OtherAssets": os.path.join(output_dir, "OtherAssets")
    }
    for dir_path in dirs.values():
        ensure_dir(dir_path)

    # Process each object in the bundle
    for obj in env.objects:
        asset_info = {
            "path_id": obj.path_id,
            "type": str(obj.type.name),
            "name": "",
            "extracted_filename": ""
        }

        try:
            data = obj.read()
            asset_name = sanitize_name(getattr(data, "m_Name", ""))
            if not asset_name:
                asset_name = f"{obj.type.name}_{obj.path_id}"
            asset_info["name"] = asset_name
            processed = False

            # Handle Textures and Sprites
            if obj.type.name in ["Texture2D", "Sprite"]:
                try:
                    filename = f"{asset_name}_{obj.path_id}.png"
                    filepath = os.path.join(dirs["Textures"], filename)
                    img = data.image
                    if img:
                        img.save(filepath)
                        asset_info["extracted_filename"] = os.path.join("Textures", filename)
                        processed = True
                    else:
                        pass  # WARNING handled silently during spinner
                except Exception as e:
                    pass  # ERROR handled silently during spinner

            # Handle TextAssets
            elif obj.type.name == "TextAsset":
                filename_txt = f"{asset_name}_{obj.path_id}.txt"
                filepath_txt = os.path.join(dirs["TextAssets"], filename_txt)
                filename_bytes = f"{asset_name}_{obj.path_id}.bytes"
                filepath_bytes = os.path.join(dirs["TextAssets"], filename_bytes)
                try:
                    script_content = data.script
                    if isinstance(script_content, bytes):
                        try:
                            text_content = script_content.decode('utf-8')
                            with open(filepath_txt, "w", encoding="utf-8") as f:
                                f.write(text_content)
                            asset_info["extracted_filename"] = os.path.join("TextAssets", filename_txt)
                        except UnicodeDecodeError:
                            with open(filepath_bytes, "wb") as f:
                                f.write(script_content)
                            asset_info["extracted_filename"] = os.path.join("TextAssets", filename_bytes)
                    elif isinstance(script_content, str):
                        with open(filepath_txt, "w", encoding="utf-8") as f:
                            f.write(script_content)
                        asset_info["extracted_filename"] = os.path.join("TextAssets", filename_txt)
                    if asset_info["extracted_filename"]:
                        processed = True
                except Exception as e:
                    pass  # ERROR handled silently during spinner

            # Handle MonoBehaviours
            elif obj.type.name == "MonoBehaviour":
                if obj.serialized_type and obj.serialized_type.nodes:
                    try:
                        tree = obj.read_typetree()
                        filename = f"{asset_name}_{obj.path_id}.json"
                        filepath = os.path.join(dirs["MonoBehaviours_JSON"], filename)
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(tree, f, indent=4)
                        asset_info["extracted_filename"] = os.path.join("MonoBehaviours_JSON", filename)
                        processed = True
                    except Exception as e:
                        pass  # WARNING handled silently during spinner
                if not processed:
                    try:
                        raw_data = getattr(obj, 'raw_data', None) or \
                                  (getattr(data, 'raw_data', None) if hasattr(data, 'raw_data') else None) or \
                                  (getattr(data, 'm_Script', None) if hasattr(data, 'm_Script') else None)
                        if raw_data and isinstance(raw_data, bytes):
                            filename_dat = f"{asset_name}_{obj.path_id}.dat"
                            filepath_dat = os.path.join(dirs["MonoBehaviours_DAT"], filename_dat)
                            with open(filepath_dat, "wb") as f:
                                f.write(raw_data)
                            asset_info["extracted_filename"] = os.path.join("MonoBehaviours_DAT", filename_dat)
                            asset_info["type"] = "MonoBehaviour_DAT"
                            processed = True
                        else:
                            pass  # WARNING handled silently during spinner
                    except Exception as e:
                        pass  # ERROR handled silently during spinner

            # Handle AudioClips
            elif obj.type.name == "AudioClip":
                try:
                    if data.m_AudioData:
                        exported_name = f"{asset_name}_{obj.path_id}"
                        result = data.export(exported_name)
                        if isinstance(result, str) and os.path.exists(result):
                            target_filename = os.path.basename(result)
                            target_filepath = os.path.join(dirs["AudioClips"], target_filename)
                            os.rename(result, target_filepath)
                            asset_info["extracted_filename"] = os.path.join("AudioClips", target_filename)
                            processed = True
                        elif isinstance(result, bytes):
                            filename = f"{exported_name}.wav"
                            filepath = os.path.join(dirs["AudioClips"], filename)
                            with open(filepath, "wb") as f:
                                f.write(result)
                            asset_info["extracted_filename"] = os.path.join("AudioClips", filename)
                            processed = True
                        else:
                            filename = f"{asset_name}_{obj.path_id}.audioclipraw"
                            filepath = os.path.join(dirs["AudioClips"], filename)
                            with open(filepath, "wb") as f:
                                f.write(data.m_AudioData)
                            asset_info["extracted_filename"] = os.path.join("AudioClips", filename)
                            processed = True
                    else:
                        pass  # WARNING handled silently during spinner
                except Exception as e:
                    pass  # ERROR handled silently during spinner

            # Handle Other Assets
            if not processed:
                try:
                    raw_data = obj.get_raw_data() if hasattr(obj, 'get_raw_data') else obj.raw_data
                    if raw_data and isinstance(raw_data, bytes):
                        filename = f"{asset_name}_{obj.path_id}.genericdat"
                        filepath = os.path.join(dirs["OtherAssets"], filename)
                        with open(filepath, "wb") as f:
                            f.write(raw_data)
                        asset_info["extracted_filename"] = os.path.join("OtherAssets", filename)
                        asset_info["type"] += "_genericdat"
                    else:
                        pass  # WARNING handled silently during spinner
                except Exception as e:
                    pass  # ERROR handled silently during spinner

            if asset_info["extracted_filename"]:
                manifest["assets"].append(asset_info)

        except Exception as e:
            asset_info["extracted_filename"] = "ERROR_EXTRACTING"
            manifest["assets"].append(asset_info)

    # Stop extraction spinner
    extraction_spinner.stop("Extracting bundle ✓")

    # Save manifest
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)
    print(f"\nExtraction Complete!\nManifest saved to: '{manifest_path}'\nAssets extracted: {len(manifest['assets'])}")

# Repacking Function
def repack_bundle(input_dir, output_bundle_path):
    """Repacks assets from an input directory into a new Unity .bundle file."""
    print(f"\n=== Repacking Bundle ===\nInput Directory: '{input_dir}'\nOutput Bundle: '{output_bundle_path}'")
    manifest_path = os.path.join(input_dir, "manifest.json")

    # Validate manifest
    if not os.path.exists(manifest_path):
        print(f"ERROR: 'manifest.json' not found in '{input_dir}'.\nPlease ensure the directory was created by the 'extract' command.")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    original_bundle_path = manifest.get("original_bundle_path")
    if not original_bundle_path or not os.path.exists(original_bundle_path):
        print(f"ERROR: Original bundle '{original_bundle_path}' not found.\nRepacking requires the original bundle file.")
        return

    # Start spinner for UnityPy loading
    spinner = Spinner("Loading UnityPy")
    spinner.start()

    print(f"Loading original bundle as template: '{original_bundle_path}'")
    env = UnityPy.load(original_bundle_path)
    modified_count = 0

    spinner.stop("Loading UnityPy ✓")

    # Start spinner for repacking process
    repack_spinner = Spinner("Repacking bundle")
    repack_spinner.start()

    # Process each asset in the manifest
    for asset_entry in manifest["assets"]:
        if asset_entry["extracted_filename"] == "ERROR_EXTRACTING" or not asset_entry["extracted_filename"]:
            continue

        path_id = asset_entry["path_id"]
        rel_path = asset_entry["extracted_filename"]
        asset_type = asset_entry["type"]
        name = asset_entry["name"]
        modified_file_path = os.path.join(input_dir, rel_path)

        if not os.path.exists(modified_file_path):
            continue

        target_obj = next((obj for obj in env.objects if obj.path_id == path_id), None)
        if not target_obj:
            continue

        try:
            data = target_obj.read()
            asset_updated = False

            # Handle Textures and Sprites
            if asset_type in ["Texture2D", "Sprite"]:
                img = Image.open(modified_file_path)
                data.image = img
                data.save()
                asset_updated = True

            # Handle TextAssets
            elif asset_type == "TextAsset":
                with open(modified_file_path, "rb") as f:
                    new_script = f.read()
                if isinstance(data.script, str):
                    try:
                        data.script = new_script.decode('utf-8')
                    except UnicodeDecodeError:
                        data.script = new_script
                else:
                    data.script = new_script
                data.save()
                asset_updated = True

            # Handle MonoBehaviours (JSON)
            elif asset_type == "MonoBehaviour":
                try:
                    with open(modified_file_path, "r", encoding="utf-8") as f:
                        new_tree = json.load(f)
                    target_obj.save_typetree(new_tree)
                    asset_updated = True
                except Exception as e:
                    pass  # ERROR handled silently during spinner

            # Handle MonoBehaviours (Raw)
            elif asset_type == "MonoBehaviour_DAT":
                with open(modified_file_path, "rb") as f:
                    raw_data = f.read()
                if hasattr(data, 'm_Script') and isinstance(data.m_Script, bytes):
                    data.m_Script = raw_data
                    data.save()
                    asset_updated = True
                elif hasattr(data, 'raw_data') and isinstance(data.raw_data, bytes):
                    data.raw_data = raw_data
                    data.save()
                    asset_updated = True

            # Handle AudioClips
            elif asset_type.startswith("AudioClip"):
                if hasattr(data, 'm_AudioData'):
                    with open(modified_file_path, "rb") as f:
                        data.m_AudioData = f.read()
                    if hasattr(data, 'm_Size'):
                        data.m_Size = len(data.m_AudioData)
                    data.save()
                    asset_updated = True

            # Handle Generic Assets
            elif asset_type.endswith("_genericdat"):
                with open(modified_file_path, "rb") as f:
                    target_obj.raw_data = f.read()
                asset_updated = True

            if asset_updated:
                modified_count += 1

        except Exception as e:
            pass  # ERROR handled silently during spinner

    # Stop repacking spinner
    repack_spinner.stop("Repacking bundle ✓")

    # Save the repacked bundle
    try:
        output_dir = os.path.dirname(os.path.abspath(output_bundle_path))
        ensure_dir(output_dir)
        with open(output_bundle_path, "wb") as f:
            f.write(env.file.save())
        status = f"{modified_count} asset(s) modified" if modified_count > 0 else "No assets modified"
        print(f"\nRepacking Complete!\nStatus: {status}\nSaved to: '{output_bundle_path}'")
    except Exception as e:
        print(f"ERROR: Failed to save repacked bundle to '{output_bundle_path}': {e}")

# Main Function with CLI
def main():
    print("=====================================================")
    print("=      Unity Bundle Tool by minhmc2007              =")
    print("=      https://github.com/minhmc2007/UBE            =")
    print("=====================================================\n")
    
    parser = argparse.ArgumentParser(
        description="A command-line tool to extract and repack Unity .bundle files using UnityPy.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  (Extract)  python %(prog)s extract YourBundle.bundle C:/output_folder/
  (Repack)   python %(prog)s repack C:/output_folder/ NewBundle.bundle

-----------------------------------------------------------------
Developed by minhmc2007 (https://github.com/minhmc2007)
-----------------------------------------------------------------
"""
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # Extract Command
    extract_parser = subparsers.add_parser("extract", help="Extract a .bundle file into a structured folder.")
    extract_parser.add_argument("bundle_file", help="Path to the input .bundle file.")
    extract_parser.add_argument("output_dir", help="Directory where assets will be extracted.")

    # Repack Command
    repack_parser = subparsers.add_parser("repack", help="Repack a folder into a .bundle file.")
    repack_parser.add_argument("input_dir", help="Directory with extracted assets and manifest.json.")
    repack_parser.add_argument("output_bundle_file", help="Path for the new repacked .bundle file.")

    args = parser.parse_args()

    if args.command == "extract":
        if not os.path.isfile(args.bundle_file):
            print(f"ERROR: Bundle file '{args.bundle_file}' not found.")
            sys.exit(1)
        extract_bundle(args.bundle_file, args.output_dir)
    elif args.command == "repack":
        if not os.path.isdir(args.input_dir):
            print(f"ERROR: Input directory '{args.input_dir}' not found.")
            sys.exit(1)
        repack_bundle(args.input_dir, args.output_bundle_file)

if __name__ == "__main__":
    main()
