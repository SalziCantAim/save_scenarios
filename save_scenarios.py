import os
import re
import zipfile
import sys
from datetime import datetime
from supabase import create_client, Client

WORKSHOP_ROOT = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\824270"
SCE_ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\FPSAimTrainer\FPSAimTrainer\Saved\scens\Scenarios"
BUCKET_NAME = "supabase_bucket"
SUPABASE_URL = "supabase_url"
SERVICE_ROLE_KEY = "secret"

supabase: Client = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

def find_shim_sce_files(root_dir, label):
    shim_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith('.sce'):
                fp = os.path.join(dirpath, filename)
                inc = False
                reasons = []
                if 'shim' in filename.lower():
                    inc = True
                    reasons.append('filename')
                try:
                    text = open(fp, 'r', encoding='utf-8', errors='ignore').read()
                    m = re.search(r'SearchTags\s*[:=]\s*(.+)', text, re.IGNORECASE)
                    if m and 'shim' in m.group(1).lower():
                        inc = True
                        reasons.append('SearchTags')
                except Exception as e:
                    print(f"Warning reading {fp}: {e}")
                if inc:
                    shim_files.append((fp, reasons, label))
    return shim_files

def create_zip(files):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    name = f"shim_scenarios_{ts}.zip"
    path = os.path.join(os.getcwd(), name)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fp, reasons, label in files:
            base = WORKSHOP_ROOT if label=='workshop' else SCE_ROOT
            rel = os.path.relpath(fp, base)
            arc = os.path.join(label, rel)
            zf.write(fp, arc)
            print(f"Added {arc} ({','.join(reasons)})")
    print(f"Created zip: {path}")
    return path

def upload_to_supabase(zip_path, bucket):
    fname = os.path.basename(zip_path)
    try:
        data = open(zip_path, 'rb').read()
        res = supabase.storage.from_(bucket).upload(fname, data)
        if hasattr(res, 'error') and res.error:
            err = res.error.message if hasattr(res.error, 'message') else res.error
            print(f"Upload error: {err}")
            return None
        url_res = supabase.storage.from_(bucket).get_public_url(fname)
        public = (getattr(url_res, 'publicURL', None)
                  or getattr(url_res, 'public_url', None)
                  or (url_res.get('publicURL') if isinstance(url_res, dict) else None)
                 )
        if public:
            print(f"URL: {public}")
            return public
        print("Uploaded")
    except Exception as e:
        print(f"Exception during upload: {e}")
    return None

def main():
    if getattr(sys, 'frozen', False):
        os.chdir(sys._MEIPASS)
    w = find_shim_sce_files(WORKSHOP_ROOT, 'workshop')
    s = find_shim_sce_files(SCE_ROOT, 'scenarios')
    all_files = w + s
    if not all_files:
        print("No matching .sce files found.")
        return
    zp = create_zip(all_files)
    upload_to_supabase(zp, BUCKET_NAME)

if __name__ == '__main__':
    main()
