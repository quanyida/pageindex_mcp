#!/usr/bin/env python3
"""PageIndex MCP Installer"""
import sys
import subprocess
from pathlib import Path

def main():
    print("="*60)
    print("PageIndex MCP Installer")
    print("="*60)
    print()

    if sys.version_info < (3, 9):
        print("ERROR: Python 3.9+ required!")
        sys.exit(1)
    print(f"Python version: {sys.version}")

    # Check if running in virtual environment
    in_venv = hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    if in_venv:
        print(f"Running in virtual environment: {sys.prefix}")
    else:
        print("WARNING: Not running in a virtual environment!")
        print("It's recommended to use a virtual environment.")
        print("You can create one by running:")
        print("  python -m venv venv")
        print("Then activate it and re-run this script.")
        print()
    print()

    print("Installing dependencies...")
    package_dir = Path(__file__).parent
    req_file = package_dir / "requirements.txt"
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-r", str(req_file)
    ])
    print()
    print("Dependencies installed successfully!")
    print()

    env_file = package_dir / ".env"
    env_example = package_dir / ".env.example"
    if not env_file.exists():
        print("Creating .env file from .env.example...")
        shutil.copy(env_example, env_file)
        print()
        print("IMPORTANT: Edit .env file and add your API Key!")
        print()

    print("="*60)
    print("INSTALLATION COMPLETE!")
    print("="*60)
    print()
    print("Now run this command to add to Claude:")
    print()
    package_path = package_dir.resolve()
    cmd = 'claude mcp add pageindex "{}" "{}" -- --workspace "{}"'.format(
        sys.executable,
        package_path / "mcp_server" / "server.py",
        package_path / "data"
    )
    print(cmd)
    print()
    print("Or customize the workspace path if needed.")
    if not in_venv:
        print()
        print("TIP: If you create a virtual environment later, use:")
        print("  venv\Scripts\python.exe (Windows)  or  venv/bin/python (Linux/Mac)")
        print("as the Python path in the claude mcp add command.")
    print()

if __name__ == "__main__":
    main()
