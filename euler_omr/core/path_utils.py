import os
import sys

def get_root_dir():
    """
    Returns the absolute path to the application root directory.
    Handles both development (script) and production (packaged) environments.
    """
    if getattr(sys, 'frozen', False):
        # When running as a packaged EXE (PyInstaller)
        # The base path is the folder containing the executable
        base_path = os.path.dirname(sys.executable)
        
        # Check if assets is in an 'internal' subdirectory
        internal_path = os.path.join(base_path, "internal")
        if os.path.exists(os.path.join(internal_path, "assets")):
            return internal_path
        return base_path
    else:
        # When running as a script in development
        # root is two levels up from this file (euler_omr/core/path_utils.py)
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_asset_path(*path_parts):
    """
    Returns the absolute path to an asset file or directory.
    """
    return os.path.join(get_root_dir(), "assets", *path_parts)
