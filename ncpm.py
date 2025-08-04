import os
import json
import shutil
import requests
from tqdm import tqdm

# ─── CONFIG ────────────────────────────────────────────────────────────────────
MANIFEST_URL = "https://raw.githubusercontent.com/SuperGamer474/N0vaCommand/refs/heads/main/ncpm/official.json"
BASE_DIR = os.path.join(
    os.environ.get('USERPROFILE', os.path.expanduser('~')),
    'N0vaCommand', 'files', '.packages'
)
PATH_FILE = os.path.join(
    os.environ.get('USERPROFILE', os.path.expanduser('~')),
    'N0vaCommand', 'path.json'
)
FILES_DIR = os.path.join(
    os.environ.get('USERPROFILE', os.path.expanduser('~')),
    'N0vaCommand', 'files'
)
# ────────────────────────────────────────────────────────────────────────────────

def add_to_path(new_abs_path):
    """
    Auto-add the installed package folder to path.json (relative to FILES_DIR).
    """
    try:
        with open(PATH_FILE, 'r') as f:
            paths = json.load(f)
    except Exception:
        paths = []

    rel_path = os.path.relpath(new_abs_path, FILES_DIR).replace('\\', '/')

    if rel_path not in paths:
        paths.append(rel_path)
        with open(PATH_FILE, 'w') as f:
            json.dump(paths, f, indent=2)
        print(f"🌟 Auto-added '{rel_path}' to path!")
    else:
        print(f"⚡ '{rel_path}' is already in path!")

def install(pkg_identifier):
    try:
        creator, pkgname = pkg_identifier.split('.', 1)
    except ValueError:
        print("❌ Bad format! Use 'ncpm install creator.PackageName'")
        return

    # ── 1️⃣ Fetch manifest
    try:
        data = requests.get(MANIFEST_URL).json()
    except Exception:
        print("❌ Couldn't fetch package list—check your internet!")
        return

    # ── 2️⃣ Find the right package
    for pkg in data.get('packages', []):
        if pkg['creator'] == creator and pkg['package_name'] == pkgname:
            url       = pkg['install_url']
            unzip     = str(pkg.get('unzip', 'false')).lower() == 'true'
            file_name = os.path.basename(url)
            dest_dir  = os.path.join(BASE_DIR, creator, pkgname)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, file_name)

            # ▶️ Download with tqdm
            try:
                resp  = requests.get(url, stream=True)
                total = int(resp.headers.get('content-length', 0))
                with open(dest_path, 'wb') as f, tqdm(
                    resp.iter_content(chunk_size=8192),
                    total=total//8192 if total else None,
                    unit='chunk',
                    ascii=False,
                    leave=False,
                    desc=f"Downloading {creator}.{pkgname}"
                ) as bar:
                    for chunk in bar:
                        f.write(chunk)
            except Exception as e:
                print(f"❌ Download error: {e}")
                return

            # 📦 Try unpacking if requested
            if unzip:
                try:
                    shutil.unpack_archive(dest_path, dest_dir)
                    os.remove(dest_path)
                except Exception:
                    print(f"⚠️ Error unzipping {file_name}.")

            # 🚀 Auto-add the package folder to path.json
            add_to_path(dest_dir)

            print(f"✅ Successfully installed {creator}.{pkgname}!")
            return

    # ── 3️⃣ Not found
    print(f"❌ Package not found: {pkg_identifier}")

def uninstall(pkg_identifier):
    try:
        creator, pkgname = pkg_identifier.split('.', 1)
    except ValueError:
        print("❌ Bad format! Use 'ncpm uninstall creator.PackageName'")
        return

    target_dir = os.path.join(BASE_DIR, creator, pkgname)
    if os.path.isdir(target_dir):
        try:
            shutil.rmtree(target_dir)
            print(f"🗑️ Uninstalled {creator}.{pkgname}.")
        except Exception as e:
            print(f"❌ Failed to uninstall {target_dir}.")
    else:
        print("❌ Nothing to uninstall!")
