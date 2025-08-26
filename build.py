#!/usr/bin/env python3
"""
Build script for talkie tools using CMake.
Builds the project in the build/ directory and copies level9 binary to talkie/data/l9.
"""

import os
import subprocess
import shutil
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

    # Ensure build directory exists
    build_dir.mkdir(exist_ok=True)

    # Run cmake configure
    cmake_configure_cmd = ["cmake", str(tools_dir)]
    run_command(cmake_configure_cmd, cwd=build_dir)

    # Run cmake build
    cmake_build_cmd = ["cmake", "--build", "."]
    run_command(cmake_build_cmd, cwd=build_dir)

    # Find and copy the level9 binary
    level9_binary = build_dir / "level9" / "level9"
    if not level9_binary.exists():
        # Try without subdirectory
        level9_binary = build_dir / "level9"

    if level9_binary.exists():
        target_path = target_dir / "l9"
        print(f"Copying {level9_binary} to {target_path}")
        shutil.copy2(level9_binary, target_path)

        # Make sure the binary is executable
        target_path.chmod(0o755)
        print(f"Successfully copied level9 binary to {target_path}")
    else:
        print("Error: level9 binary not found after build")
        sys.exit(1)


if __name__ == "__main__":
    main()
