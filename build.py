#!/usr/bin/env python3
"""
Build script for talkie tools using CMake.
Builds the project in the build/ directory and copies level9 binary to talkie/data/l9.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None, check=True):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)} {'(in ' + str(cwd) + ')' if cwd else ''}")
    try:
        result = subprocess.run(
            cmd, cwd=cwd, check=check, capture_output=True, text=True
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return e


def main():
    # Get the project root directory
    project_root = Path(__file__).parent
    tools_dir = project_root / "tools"
    build_dir = project_root / "build"
    target_dir = project_root / "talkie" / "data"

    # List of subdirectories in tools to build
    build_subdirs = ["level9", "Magnetic"]

    # Ensure build directory exists
    build_dir.mkdir(exist_ok=True)

    # Build each subdirectory
    for subdir in build_subdirs:
        subdir_path = tools_dir / subdir
        if not subdir_path.exists():
            print(f"Warning: {subdir_path} does not exist, skipping")
            continue

        subdir_build_dir = build_dir / subdir
        subdir_build_dir.mkdir(exist_ok=True)

        print(f"Building {subdir}...")

        # Run cmake configure
        cmake_configure_cmd = ["cmake", str(subdir_path)]
        run_command(cmake_configure_cmd, cwd=subdir_build_dir)

        # Run cmake build
        cmake_build_cmd = ["cmake", "--build", "."]
        run_command(cmake_build_cmd, cwd=subdir_build_dir)

    # Find and copy the level9 binary
    level9_binary = build_dir / "level9" / "level9"
    target_path = target_dir / "l9"
    print(f"Copying {level9_binary} to {target_path}")
    shutil.copy2(level9_binary, target_path)
    target_path.chmod(0o755)

    magnetic_binary = build_dir / "Magnetic" / "bin" / "magnetic"
    target_path = target_dir / "magnetic"
    print(f"Copying {magnetic_binary} to {target_path}")
    shutil.copy2(magnetic_binary, target_path)
    target_path.chmod(0o755)

if __name__ == "__main__":
    main()
