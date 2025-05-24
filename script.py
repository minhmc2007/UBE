import UnityPy
import os
import sys
import json
from PIL import Image
import argparse

# Helper function to ensure output directory exists
def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def sanitize_name(name):
    """Sanitizes a name to be used as a filename."""
    if not name:
        return ""
    # Remove invalid characters for filenames
    return "".join(c for c in name if c.isalnum() or c in (' ', '.', '_', '-')).rstrip().strip()

def extract_bundle(bundle_path, output_dir):
    print(f"Extracting '{bundle_path}' to '{output_dir}'...")
    ensure_dir(output_dir)
    try:
        env = UnityPy.load(bundle_path)
    except Exception as e:
        print(f"Error: Failed to load bundle '{bundle_path}'. It might be corrupted, protected, or not a valid Unity bundle.")
        print(f"Details: {e}")
        sys.exit(1)


    manifest = {
        "original_bundle_path": os.path.abspath(bundle_path),
        "assets": []
    }

    # Create subdirectories for different asset types
    dir_textures = os.path.join(output_dir, "Textures")
    dir_textassets = os.path.join(output_dir, "TextAssets")
    dir_monobehaviours_json = os.path.join(output_dir, "MonoBehaviours_JSON")
    dir_monobehaviours_dat = os.path.join(output_dir, "MonoBehaviours_DAT")
    dir_audioclips = os.path.join(output_dir, "AudioClips")
    dir_other = os.path.join(output_dir, "OtherAssets")

    ensure_dir(dir_textures)
    ensure_dir(dir_textassets)
    ensure_dir(dir_monobehaviours_json)
    ensure_dir(dir_monobehaviours_dat)
    ensure_dir(dir_audioclips)
    ensure_dir(dir_other)

    for obj in env.objects:
        asset_info = {
            "path_id": obj.path_id,
            "type": str(obj.type.name), # Using str() to ensure it's a plain string
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
            if obj.type.name in ["Texture2D", "Sprite"]:
                try:
                    # Ensure name is unique if multiple textures have same name by appending path_id
                    filename = f"{asset_name}_{obj.path_id}.png"
                    filepath = os.path.join(dir_textures, filename)
                    img = data.image
                    if img:
                        img.save(filepath)
                        asset_info["extracted_filename"] = os.path.join("Textures", filename)
                        print(f"  Saved {obj.type.name}: {asset_info['extracted_filename']}")
                        processed = True
                    else:
                        print(f"    {obj.type.name} {asset_name} has no image data.")
                except Exception as e:
                    print(f"    Error saving {obj.type.name} {asset_name}: {e}")
            
            elif obj.type.name == "TextAsset":
                filename_txt = f"{asset_name}_{obj.path_id}.txt"
                filepath_txt = os.path.join(dir_textassets, filename_txt)
                filename_bytes = f"{asset_name}_{obj.path_id}.bytes"
                filepath_bytes = os.path.join(dir_textassets, filename_bytes)
                
                saved_as = ""
                try:
                    # data.script can be bytes or str depending on UnityPy version and asset
                    script_content = data.script
                    if isinstance(script_content, bytes):
                        try:
                            text_content = script_content.decode('utf-8')
                            with open(filepath_txt, "w", encoding="utf-8") as f:
                                f.write(text_content)
                            saved_as = os.path.join("TextAssets", filename_txt)
                        except UnicodeDecodeError: # Fallback to binary if not UTF-8
                            with open(filepath_bytes, "wb") as f:
                                f.write(script_content)
                            saved_as = os.path.join("TextAssets", filename_bytes)
                    elif isinstance(script_content, str):
                        with open(filepath_txt, "w", encoding="utf-8") as f:
                            f.write(script_content)
                        saved_as = os.path.join("TextAssets", filename_txt)
                    else:
                         print(f"    TextAsset {asset_name} has unknown script type: {type(script_content)}")

                    if saved_as:
                        asset_info["extracted_filename"] = saved_as
                        print(f"  Saved TextAsset: {saved_as}")
                        processed = True
                except Exception as e:
                    print(f"    Error saving TextAsset {asset_name}: {e}")

            elif obj.type.name == "MonoBehaviour":
                if obj.serialized_type and obj.serialized_type.nodes:
                    try:
                        tree = obj.read_typetree()
                        filename = f"{asset_name}_{obj.path_id}.json"
                        filepath = os.path.join(dir_monobehaviours_json, filename)
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(tree, f, indent=4)
                        asset_info["extracted_filename"] = os.path.join("MonoBehaviours_JSON", filename)
                        print(f"  Saved MonoBehaviour (JSON): {asset_info['extracted_filename']}")
                        processed = True
                    except Exception as e:
                        print(f"    Error saving MonoBehaviour {asset_name} as JSON: {e}. Trying raw.")
                        # Fallback handled below if this fails
                
                if not processed: # Try saving as raw .dat if JSON failed or no typetree
                    try:
                        # obj.raw_data directly is one way, or obj.script for simpler cases
                        raw_data_bytes = None
                        if hasattr(obj, 'raw_data'): # for the container object
                            raw_data_bytes = obj.raw_data
                        elif hasattr(data, 'raw_data') and isinstance(data.raw_data, bytes): # for the read data object
                             raw_data_bytes = data.raw_data
                        elif hasattr(data, 'm_Script') and isinstance(data.m_Script, bytes): # common field name
                             raw_data_bytes = data.m_Script
                        
                        if raw_data_bytes:
                            filename_dat = f"{asset_name}_{obj.path_id}.dat"
                            filepath_dat = os.path.join(dir_monobehaviours_dat, filename_dat)
                            with open(filepath_dat, "wb") as f_dat:
                                f_dat.write(raw_data_bytes)
                            asset_info["extracted_filename"] = os.path.join("MonoBehaviours_DAT", filename_dat)
                            asset_info["type"] = "MonoBehaviour_DAT" # Mark as raw for repacking logic
                            print(f"  Saved MonoBehaviour (RAW): {asset_info['extracted_filename']}")
                            processed = True
                        else:
                            print(f"    MonoBehaviour {asset_name} has no typetree and no obvious raw data field to save.")
                    except Exception as e_raw:
                         print(f"    Failed to save MonoBehaviour {asset_name} as raw data: {e_raw}")

            elif obj.type.name == "AudioClip":
                try:
                    # data here is the AudioClip object from obj.read()
                    if data.m_AudioData:
                        # UnityPy's AudioClip handling can be complex (FSB, etc.)
                        # .export() is the preferred way if available, as it might handle conversions.
                        # Let's try to get a .wav if possible.
                        exported_name = f"{asset_name}_{obj.path_id}"
                        # Some UnityPy versions/AudioClip types might save directly or return data.
                        # This part is highly dependent on the specifics of the AudioClip internal format and UnityPy version.
                        # A common approach is to try data.export()
                        potential_wav_filename = data.export(exported_name) # May save as exported_name.wav or return bytes
                        
                        if isinstance(potential_wav_filename, str) and os.path.exists(potential_wav_filename):
                            # If it saved a file, move it to our target directory
                            target_filename = os.path.basename(potential_wav_filename) # Use the name UnityPy gave
                            target_filepath = os.path.join(dir_audioclips, target_filename)
                            if os.path.abspath(potential_wav_filename) != os.path.abspath(target_filepath):
                                os.rename(potential_wav_filename, target_filepath)
                            asset_info["extracted_filename"] = os.path.join("AudioClips", target_filename)
                            print(f"  Saved AudioClip (exported): {asset_info['extracted_filename']}")
                            processed = True
                        elif isinstance(potential_wav_filename, bytes): # if export() returned bytes
                            target_filename = f"{exported_name}.wav" # Assume wav
                            target_filepath = os.path.join(dir_audioclips, target_filename)
                            with open(target_filepath, "wb") as f:
                                f.write(potential_wav_filename)
                            asset_info["extracted_filename"] = os.path.join("AudioClips", target_filename)
                            print(f"  Saved AudioClip (bytes exported): {asset_info['extracted_filename']}")
                            processed = True
                        else: # Fallback to m_AudioData (might be raw, e.g. FSB)
                            extension = ".audioclipraw" # Indicate it's raw
                            filename = f"{asset_name}_{obj.path_id}{extension}"
                            filepath = os.path.join(dir_audioclips, filename)
                            with open(filepath, "wb") as f:
                                f.write(data.m_AudioData)
                            asset_info["extracted_filename"] = os.path.join("AudioClips", filename)
                            print(f"  Saved AudioClip (raw m_AudioData): {asset_info['extracted_filename']}")
                            processed = True
                    else:
                        print(f"    AudioClip {asset_name} has no m_AudioData.")
                except Exception as e:
                    print(f"    Error saving AudioClip {asset_name}: {e}")

            if not processed:
                # Generic fallback for other types: save raw data if possible from obj
                try:
                    raw_obj_data = obj.get_raw_data() if hasattr(obj, 'get_raw_data') else obj.raw_data
                    if raw_obj_data and isinstance(raw_obj_data, bytes):
                        filename = f"{asset_name}_{obj.path_id}.genericdat"
                        filepath = os.path.join(dir_other, filename)
                        with open(filepath, "wb") as f:
                            f.write(raw_obj_data)
                        asset_info["extracted_filename"] = os.path.join("OtherAssets", filename)
                        asset_info["type"] += "_genericdat"
                        print(f"  Saved generic asset (RAW): {asset_info['extracted_filename']}")
                    else:
                        print(f"    Asset {asset_name} (Type: {obj.type.name}): No standard extraction or raw data method found.")
                except Exception as e_gen:
                     print(f"    Could not save generic asset {asset_name} (Type: {obj.type.name}): {e_gen}")

            if asset_info["extracted_filename"]:
                 manifest["assets"].append(asset_info)

        except Exception as e:
            print(f"  Major error processing object with PathID {obj.path_id} (Type: {obj.type.name}): {e}")
            asset_info["extracted_filename"] = "ERROR_EXTRACTING" # Mark as error
            asset_info["name"] = asset_info.get("name") or f"UnknownName_{obj.path_id}"
            manifest["assets"].append(asset_info)


    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)
    print(f"Extraction complete. Manifest saved to '{manifest_path}'")


def repack_bundle(input_dir, output_bundle_path):
    print(f"Repacking '{input_dir}' to '{output_bundle_path}'...")
    manifest_path = os.path.join(input_dir, "manifest.json")

    if not os.path.exists(manifest_path):
        print(f"Error: manifest.json not found in '{input_dir}'. Cannot repack without manifest.")
        print("Please ensure the input directory was created by the 'extract' command of this script.")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    original_bundle_path = manifest.get("original_bundle_path")
    if not original_bundle_path or not os.path.exists(original_bundle_path):
        print(f"Error: Original bundle path '{original_bundle_path}' from manifest is invalid or not found.")
        print("Repacking requires the original bundle file used for extraction.")
        return

    print(f"Using original bundle '{original_bundle_path}' as template.")
    env = UnityPy.load(original_bundle_path)

    modified_count = 0
    for asset_entry in manifest["assets"]:
        if asset_entry["extracted_filename"] == "ERROR_EXTRACTING" or not asset_entry["extracted_filename"] :
            print(f"  Skipping asset PathID {asset_entry['path_id']} (Name: {asset_entry['name']}) due to previous extraction error or no file.")
            continue

        original_path_id = asset_entry["path_id"]
        extracted_file_rel_path = asset_entry["extracted_filename"]
        asset_type = asset_entry["type"] # Type as stored in manifest (e.g., "Texture2D", "MonoBehaviour_DAT")
        asset_name_from_manifest = asset_entry["name"]

        modified_file_path = os.path.join(input_dir, extracted_file_rel_path)

        if os.path.exists(modified_file_path):
            target_obj = None
            # Find the object in the loaded environment by its path_id
            for obj_in_env in env.objects:
                if obj_in_env.path_id == original_path_id:
                    target_obj = obj_in_env
                    break
            
            if target_obj:
                try:
                    data = target_obj.read() # Read the original object's data structure
                    print(f"  Processing PathID {original_path_id} (Name: {asset_name_from_manifest}, Type: {asset_type})")

                    asset_updated = False
                    if asset_type in ["Texture2D", "Sprite"]:
                        img = Image.open(modified_file_path)
                        data.image = img # Set the new image
                        data.save()     # Save the changes to the data object
                        print(f"    Updated Texture/Sprite from '{extracted_file_rel_path}'")
                        asset_updated = True
                    
                    elif asset_type == "TextAsset":
                        with open(modified_file_path, "rb") as f:
                            new_script_bytes = f.read()
                        
                        # data.script can be str or bytes. Try to match original or common practice.
                        if isinstance(data.script, str):
                            try:
                                data.script = new_script_bytes.decode('utf-8')
                            except UnicodeDecodeError:
                                print(f"    Warning: TextAsset '{asset_name_from_manifest}' was string, new file not UTF-8. Trying to set as bytes.")
                                data.script = new_script_bytes # May or may not work depending on Unity version/field
                        else: # Original was bytes or can accept bytes
                            data.script = new_script_bytes
                        data.save()
                        print(f"    Updated TextAsset from '{extracted_file_rel_path}'")
                        asset_updated = True

                    elif asset_type == "MonoBehaviour_JSON": # Repack from JSON typetree
                        with open(modified_file_path, "r", encoding="utf-8") as f:
                            new_tree = json.load(f)
                        target_obj.save_typetree(new_tree) # Use save_typetree on the container object
                        print(f"    Updated MonoBehaviour (JSON) from '{extracted_file_rel_path}'")
                        asset_updated = True
                    
                    elif asset_type == "MonoBehaviour_DAT": # Repack from raw .dat file
                        with open(modified_file_path, "rb") as f:
                            raw_mb_data = f.read()
                        # Applying raw data is tricky. Common fields are m_Script or obj.raw_data for the container
                        # We need to modify the 'data' object read from target_obj.read()
                        if hasattr(data, 'm_Script') and isinstance(data.m_Script, bytes):
                            data.m_Script = raw_mb_data
                            data.save()
                            print(f"    Updated MonoBehaviour (RAW via m_Script) from '{extracted_file_rel_path}'")
                            asset_updated = True
                        elif hasattr(data, 'raw_data') and isinstance(data.raw_data, bytes): # Less common for 'data' object
                            data.raw_data = raw_mb_data
                            data.save()
                            print(f"    Updated MonoBehaviour (RAW via data.raw_data) from '{extracted_file_rel_path}'")
                            asset_updated = True
                        else:
                            # Fallback: try to set on target_obj directly if UnityPy allows and if it's simple
                            # This is less standard for complex objects.
                            # if hasattr(target_obj, 'script'): target_obj.script = raw_mb_data (dangerous)
                            print(f"    MonoBehaviour (RAW) {asset_name_from_manifest}: Don't know how to reliably apply raw .dat data back. Skipped.")
                    
                    elif asset_type.startswith("AudioClip"): # Handles .wav or .audioclipraw
                        # Repacking audio: replace m_AudioData.
                        # This assumes the modified file (e.g. .wav) can be directly used as m_AudioData,
                        # which might not be true if original was compressed (e.g. FSB) and Unity expects that format.
                        # For true repacking of WAV to original format, a conversion step might be needed.
                        if hasattr(data, 'm_AudioData'):
                            with open(modified_file_path, "rb") as f:
                                new_audio_data_bytes = f.read()
                            data.m_AudioData = new_audio_data_bytes
                            if hasattr(data, 'm_Size'): # Update size if field exists
                                data.m_Size = len(new_audio_data_bytes)
                            data.save()
                            print(f"    Updated AudioClip from '{extracted_file_rel_path}' (raw m_AudioData replacement)")
                            asset_updated = True
                        else:
                            print(f"    AudioClip {asset_name_from_manifest}: Cannot find m_AudioData field in parsed data. Skipped.")
                    
                    elif asset_type.endswith("_genericdat"):
                        with open(modified_file_path, "rb") as f:
                            raw_generic_data = f.read()
                        # Attempt to set raw data on the container object if UnityPy supports such a field directly.
                        # This is highly speculative.
                        if hasattr(target_obj, 'raw_data'): # Check the container object
                            target_obj.raw_data = raw_generic_data
                            # No explicit save call on 'target_obj' or 'data' here typically,
                            # as modifying 'target_obj.raw_data' directly (if supported)
                            # would be saved when 'env.file.save()' is called.
                            print(f"    Updated generic asset (RAW via obj.raw_data) from '{extracted_file_rel_path}'")
                            asset_updated = True
                        else:
                            print(f"    Generic asset (RAW) {asset_name_from_manifest}: No standard method to set raw data. Skipped.")
                    else:
                        print(f"    Skipping repack for asset type '{asset_type}' (PathID {original_path_id}) - repacking not implemented for this type.")

                    if asset_updated:
                        modified_count += 1

                except Exception as e:
                    print(f"    Error updating object PathID {original_path_id} (Name: {asset_name_from_manifest}) from '{extracted_file_rel_path}': {e}")
            else:
                print(f"  Warning: Object with PathID {original_path_id} (Name: {asset_name_from_manifest}) from manifest not found in the loaded original bundle. Skipping.")
        else:
            print(f"  Info: Modified file '{extracted_file_rel_path}' for PathID {original_path_id} (Name: {asset_name_from_manifest}) not found in input directory '{input_dir}'. Asset will not be changed.")

    if modified_count > 0:
        try:
            # Ensure the output directory for the bundle exists
            output_bundle_dir = os.path.dirname(os.path.abspath(output_bundle_path))
            if output_bundle_dir and not os.path.exists(output_bundle_dir): # Create only if a path is specified
                 ensure_dir(output_bundle_dir)
            
            with open(output_bundle_path, "wb") as f:
                f.write(env.file.save()) # env.file.save() serializes the entire modified environment
            print(f"Repacking complete. {modified_count} asset(s) potentially modified. Saved to '{output_bundle_path}'")
        except Exception as e:
            print(f"Error saving repacked bundle to '{output_bundle_path}': {e}")
    else:
        print("Repacking complete. No assets were modified (or no modifiable files were found/matched).")
        # Avoid creating an empty or identical file if no changes and output doesn't exist
        if not os.path.exists(output_bundle_path) and original_bundle_path:
            if os.path.exists(original_bundle_path): # Check original exists to avoid issues if it was deleted
                 print(f"'{output_bundle_path}' was not written as no changes were applied from the input directory.")
        elif os.path.exists(output_bundle_path): # If output file already exists
             print(f"'{output_bundle_path}' might be identical to the original or previous version if no effective changes were made.")


def main():
    parser = argparse.ArgumentParser(
        description="Extract and repack Unity .bundle files using UnityPy.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  To extract:
    python %(prog)s extract YourBundleFile.bundle ExtractedFolder/
  To repack:
    python %(prog)s repack ExtractedFolder/ RepackedBundle.bundle
        (Ensure 'ExtractedFolder/' contains manifest.json and modified assets from a previous extraction)
"""
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Sub-command to execute")

    parser_extract = subparsers.add_parser("extract", help="Extract a .bundle file to a directory.")
    parser_extract.add_argument("bundle_file", help="Path to the .bundle file to extract.")
    parser_extract.add_argument("output_dir", help="Directory to save extracted assets and manifest.json.")

    parser_repack = subparsers.add_parser("repack", help="Repack a directory (previously extracted by this script) into a new .bundle file.")
    parser_repack.add_argument("input_dir", help="Directory containing extracted assets and manifest.json.")
    parser_repack.add_argument("output_bundle_file", help="Path to save the new repacked .bundle file.")

    args = parser.parse_args()

    if args.command == "extract":
        if not os.path.isfile(args.bundle_file):
            print(f"Error: Bundle file '{args.bundle_file}' not found.")
            sys.exit(1)
        # Create output_dir if it's just a name and doesn't exist
        abs_output_dir = os.path.abspath(args.output_dir)
        if not os.path.isdir(abs_output_dir) and not os.path.splitext(abs_output_dir)[1]: # if not a dir and no extension
            ensure_dir(abs_output_dir)
        elif os.path.isfile(abs_output_dir):
            print(f"Error: Output directory '{args.output_dir}' points to an existing file.")
            sys.exit(1)

        extract_bundle(args.bundle_file, args.output_dir)

    elif args.command == "repack":
        if not os.path.isdir(args.input_dir):
            print(f"Error: Input directory '{args.input_dir}' not found.")
            sys.exit(1)
        
        # Ensure the directory for the output bundle exists, if specified with a path
        output_bundle_dir = os.path.dirname(os.path.abspath(args.output_bundle_file))
        if output_bundle_dir and not os.path.exists(output_bundle_dir): # If it's not just a filename in the current directory
            ensure_dir(output_bundle_dir)

        repack_bundle(args.input_dir, args.output_bundle_file)

if __name__ == "__main__":
    main()
