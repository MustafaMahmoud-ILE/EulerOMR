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
        "--add-data=assets;assets",
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
    
    # 3. Create a clean zip for production distribution
    dist_folder = os.path.join("dist", "EulerOMR")
    zip_name = f"EulerOMR-v{version}-windows"
    zip_path = os.path.join("dist", zip_name)
    
    print(f"Zipping the build into {zip_path}.zip...")
    shutil.make_archive(zip_path, 'zip', "dist", "EulerOMR")
    
    print("Build and packaging complete! Your artifact is ready at:")
    print(f" -> {zip_path}.zip")

if __name__ == "__main__":
    main()
