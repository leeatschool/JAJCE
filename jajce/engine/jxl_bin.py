import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict

class JXLBinaries:
    """
    Manages discovery and execution of libjxl tool binaries:
    cjxl (encoder), djxl (decoder), and jxlinfo (metadata/file inspector).
    """

    @classmethod
    def get_bin_dir(cls) -> Path:
        """Returns the project-local bin directory if available."""
        # Check current working directory or relative to this file
        current_file_dir = Path(__file__).resolve().parent
        # jajce/engine -> jajce -> JAJCE -> bin
        candidates = [
            current_file_dir.parent.parent / "bin",
            Path(sys.prefix) / "bin",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
        ]
        for candidate in candidates:
            if candidate.exists() and (candidate / "cjxl.exe").exists():
                return candidate
        return current_file_dir.parent.parent / "bin"

    @classmethod
    def find_binary(cls, binary_name: str) -> Optional[str]:
        """
        Finds a binary (e.g. 'cjxl', 'djxl', 'jxlinfo').
        Checks local bin/, then WinGet paths, then system PATH.
        """
        exe_name = f"{binary_name}.exe" if sys.platform == "win32" and not binary_name.endswith(".exe") else binary_name

        # 1. Local bin folder
        local_bin = cls.get_bin_dir() / exe_name
        if local_bin.exists():
            return str(local_bin)

        # 2. PATH lookup
        path_binary = shutil.which(binary_name)
        if path_binary:
            return path_binary

        # 3. Recursive check in WinGet package cache if on Windows
        if sys.platform == "win32":
            winget_base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
            if winget_base.exists():
                found = list(winget_base.glob(f"**/{exe_name}"))
                if found:
                    return str(found[0])

        return None

    @classmethod
    def get_all(cls) -> Dict[str, Optional[str]]:
        return {
            "cjxl": cls.find_binary("cjxl"),
            "djxl": cls.find_binary("djxl"),
            "jxlinfo": cls.find_binary("jxlinfo"),
        }

    @classmethod
    def verify(cls) -> Dict[str, bool]:
        """Verifies whether the essential binaries are present and runnable."""
        results = {}
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        for name in ["cjxl", "djxl", "jxlinfo"]:
            bin_path = cls.find_binary(name)
            if not bin_path:
                results[name] = False
                continue
            try:
                proc = subprocess.run([bin_path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=flags, timeout=5)
                results[name] = proc.returncode == 0
            except Exception:
                results[name] = False
        return results
