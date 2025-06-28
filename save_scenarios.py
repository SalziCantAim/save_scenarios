import os
import re
import sys
from datetime import datetime
from supabase import create_client, Client

WORKSHOP_ROOT = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\824270"
SCE_ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\FPSAimTrainer\FPSAimTrainer\Saved\SaveGames\Scenarios"
BUCKET_NAME = "name"
SUPABASE_URL = "url"
SERVICE_ROLE_KEY = "api_key"

supabase: Client = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)


def find_shim_sce_files():
    shim_files = []
    total_found = 0

    print("=" * 60)
    print("Scanning for files containing 'Shim'/'Shimmy', in your steam workshop files!")
    print("=" * 60)

    if os.path.exists(WORKSHOP_ROOT):
        print(f"Scanning workshop root: {WORKSHOP_ROOT}")
        for item in os.listdir(WORKSHOP_ROOT):
            workshop_dir = os.path.join(WORKSHOP_ROOT, item)
            if os.path.isdir(workshop_dir):
                print(f"  Checking directory: {item}")
                for filename in os.listdir(workshop_dir):
                    if filename.lower().endswith('.sce'):
                        total_found += 1
                        fp = os.path.join(workshop_dir, filename)
                        result = check_shim_file(fp, 'workshop')
                        if result:
                            shim_files.append(result)
    else:
        print(f"Workshop root not found: {WORKSHOP_ROOT}")

    if os.path.exists(SCE_ROOT):
        print(f"\nScanning scenarios root: {SCE_ROOT}")
        for filename in os.listdir(SCE_ROOT):
            if filename.lower().endswith('.sce'):
                total_found += 1
                fp = os.path.join(SCE_ROOT, filename)
                result = check_shim_file(fp, 'scenarios')
                if result:
                    shim_files.append(result)
    else:
        print(f"Scenarios root not found: {SCE_ROOT}")

    print(f"\nScan complete, NOW uploading to database, do NOT close the window!")
    print(f"Total .sce files found: {total_found}")
    print(f"Files with 'shim' found: {len(shim_files)}")

    return shim_files


def check_shim_file(filepath, source):
    filename = os.path.basename(filepath)
    has_shim = False
    reasons = []

    if 'shim' in filename.lower():
        has_shim = True
        reasons.append('filename')


    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            match = re.search(r'SearchTags\s*[:=]\s*(.+)', content, re.IGNORECASE)
            if match and 'shim' in match.group(1).lower():
                has_shim = True
                reasons.append('tags')
    except Exception as e:
        print(f"    Warning: Could not read {filename}: {e}")

    if has_shim:
        print(f"   Found: {filename} (shim in: {', '.join(reasons)})")
        return {
            'filepath': filepath,
            'filename': filename,
            'source': source,
            'reasons': reasons
        }

    return None


def check_file_exists_in_bucket(filename):
    try:
        response = supabase.storage.from_(BUCKET_NAME).list()
        if hasattr(response, 'error') and response.error:
            return False

        existing_files = response if isinstance(response, list) else []
        for file_info in existing_files:
            if isinstance(file_info, dict) and file_info.get('name') == filename:
                return True
        return False
    except Exception as e:
        print(f"    Error checking bucket: {e}")
        return False


def upload_file_to_bucket(file_info):
    filepath = file_info['filepath']
    filename = file_info['filename']

    print(f"  Processing: {filename}")

    exists = check_file_exists_in_bucket(filename)
    if exists:
        print(f"     File already exists in bucket")
        return {'status': 'exists', 'filename': filename}

    try:
        with open(filepath, 'rb') as f:
            file_data = f.read()

        response = supabase.storage.from_(BUCKET_NAME).upload(filename, file_data)

        if hasattr(response, 'error') and response.error:
            error_msg = response.error.message if hasattr(response.error, 'message') else str(response.error)
            print(f"     Upload failed: {error_msg}")
            return {'status': 'failed', 'filename': filename, 'error': error_msg}

        print(f"     Uploaded successfully")
        return {'status': 'uploaded', 'filename': filename}

    except Exception as e:
        print(f"     Exception during upload: {e}")
        return {'status': 'failed', 'filename': filename, 'error': str(e)}


def main():
    print("Please wait this can take a few seconds!")
    print("=" * 60)

    try:
        shim_files = find_shim_sce_files()

        if not shim_files:
            print("\nNo .sce files with 'shim' found!")
        else:
            print(f"\nUPLOADING {len(shim_files)} FILES TO BUCKET")
            print("=" * 60)

            results = {
                'uploaded': [],
                'exists': [],
                'failed': []
            }

            for file_info in shim_files:
                result = upload_file_to_bucket(file_info)
                results[result['status']].append(result['filename'])

            print(f"\nUPLOAD SUMMARY")
            print("=" * 60)
            print(f"✓ Successfully uploaded: {len(results['uploaded'])}")
            if results['uploaded']:
                for filename in results['uploaded']:
                    print(f"    • {filename}")

            print(f"\nAlready existed: {len(results['exists'])}")
            if results['exists']:
                for filename in results['exists']:
                    print(f"    • {filename}")

            print(f"\n✗ Failed to upload: {len(results['failed'])}")
            if results['failed']:
                for filename in results['failed']:
                    print(f"    • {filename}")

    except Exception as e:
        print(f"\nERROR: The program encountered an error and could not complete please DM the following to 'Salzi' on Discord:")
        print(f"    {str(e)}")

    finally:
        print(f"\n" + "=" * 60)
        print("Program finished. Press Enter to close or simply close the window, you can now also delete this file again thank you for helping multiple creators!")
        input()


if __name__ == '__main__':
    main()
