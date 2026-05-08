import os
import sys
import subprocess
import shutil
import toml

def main():
    # 1. Read version from pyproject.toml
    with open('pyproject.toml', 'r') as f:
        config = toml.load(f)
    version = config['project']['version']
    print(f"Building Euler OMR version {version}...")

    # 2. Run PyInstaller
    # We use --onedir to package it into a folder, not a single huge exe.
    # We hide console with --noconsole
    # We set the icon
    # We collect all submodules and data using pyinstaller spec logic
    
    cmd = [
        "pyinstaller",
        "--name=EulerOMR",
        "--onedir",
        "--windowed",
        "--icon=assets/icons/app.ico",
        # We don't use --add-data for assets anymore; we'll copy it manually to the root
        "--hidden-import=pypdfium2",
        "--hidden-import=cv2",
        "--hidden-import=PIL",
        "--hidden-import=openpyxl",
        "--hidden-import=scipy",
        "--hidden-import=matplotlib",
        "--clean",
        "-y",
        "main.py"
    ]
    
    print("Running PyInstaller...")
    subprocess.run(cmd, check=True)

    # 3. Manually copy assets folder to the root of the dist folder (next to the .exe)
    dist_root = os.path.join("dist", "EulerOMR")
    dest_assets = os.path.join(dist_root, "assets")
    print(f"Moving assets to {dest_assets} (next to the .exe)...")
    if os.path.exists(dest_assets):
        shutil.rmtree(dest_assets)
    shutil.copytree("assets", dest_assets)
    
    # 4. Create a clean zip for production distribution
    dist_folder = os.path.join("dist", "EulerOMR")
    zip_name = f"EulerOMR-v{version}-windows"
    zip_path = os.path.join("dist", zip_name)
    
    print(f"Zipping the build into {zip_path}.zip...")
    shutil.make_archive(zip_path, 'zip', "dist", "EulerOMR")
    
    # 4. Create an installer using Inno Setup
    iscc_path = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    installer_script = os.path.join("scripts", "installer_setup.iss")
    if os.path.exists(iscc_path) and os.path.exists(installer_script):
        print("Running Inno Setup Compiler...")
        subprocess.run([iscc_path, installer_script], check=True)
        print(f" -> dist/EulerOMR_Setup_v{version}.exe")
    else:
        print("Skipping installer build (Inno Setup not found).")
    
    print("Build and packaging complete! Your artifacts are ready at:")
    print(f" -> {zip_path}.zip")

if __name__ == "__main__":
    main()
