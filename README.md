# Unity Bundle Extractor/Repacker

A Python script for extracting and repacking Unity .bundle files using UnityPy. This tool allows you to extract various asset types from Unity bundles, modify them, and repack them back into bundle format.

## Features

- Extract Unity bundle files to organized directory structure
- Support for multiple asset types:
  - **Textures** (Texture2D, Sprite) → PNG files
  - **Text Assets** → TXT/bytes files
  - **MonoBehaviours** → JSON (typetree) or DAT (raw binary)
  - **Audio Clips** → WAV or raw audio data
  - **Generic Assets** → Raw binary data
- Repack modified assets back into Unity bundle format
- Automatic file sanitization and organization
- Detailed manifest tracking for reliable repacking

## Requirements

```bash
pip install UnityPy Pillow
```

## Installation

1. Save the script as `script.py`
2. Install required dependencies
3. Run from command line

## Usage

### Extract a Bundle

```bash
python script.py extract YourBundleFile.bundle ExtractedFolder/
```

This will create:
```
ExtractedFolder/
├── manifest.json           # Asset tracking manifest
├── Textures/              # PNG files from Texture2D/Sprite assets
├── TextAssets/            # TXT/bytes files from TextAsset objects
├── MonoBehaviours_JSON/   # JSON files from MonoBehaviour typetrees
├── MonoBehaviours_DAT/    # Raw binary data from MonoBehaviours
├── AudioClips/            # WAV or raw audio files
└── OtherAssets/           # Generic binary data from other asset types
```

### Repack a Bundle

```bash
python script.py repack ExtractedFolder/ RepackedBundle.bundle
```

**Important**: The input directory must contain the `manifest.json` file created during extraction. The original bundle file referenced in the manifest must still exist and be accessible.

## Asset Type Support

| Asset Type | Extraction Format | Repacking Support |
|------------|------------------|-------------------|
| Texture2D/Sprite | PNG | ✅ Yes |
| TextAsset | TXT/bytes | ✅ Yes |
| MonoBehaviour (with typetree) | JSON | ✅ Yes |
| MonoBehaviour (raw) | DAT binary | ⚠️ Limited |
| AudioClip | WAV/raw audio | ⚠️ Limited |
| Other types | Raw binary | ⚠️ Limited |

## Workflow

1. **Extract** a bundle to examine and modify assets
2. **Modify** the extracted files as needed:
   - Edit PNG images in image editors
   - Modify text files
   - Edit JSON files for MonoBehaviour data
3. **Repack** the modified assets into a new bundle

## Important Notes

- **Keep the original bundle file**: Repacking requires the original bundle as a template
- **Preserve file structure**: Don't move files between the organized subdirectories
- **Manifest dependency**: The `manifest.json` file is essential for repacking
- **Binary compatibility**: Some asset modifications may not work depending on Unity version and asset complexity
- **Backup your files**: Always keep backups of original bundles before modification

## Error Handling

The script includes comprehensive error handling for:
- Corrupted or protected bundle files
- Missing dependencies
- Invalid file paths
- Asset processing failures
- Repacking inconsistencies

## Limitations

- MonoBehaviour repacking from raw DAT files has limited reliability
- AudioClip repacking may not preserve original compression formats
- Some Unity-specific asset formats may not be fully supported
- Protected or encrypted bundles cannot be processed

## Command Line Help

```bash
python script.py --help
python script.py extract --help
python script.py repack --help
```
