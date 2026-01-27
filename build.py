"""
Build script for OpenGameBoost.
Creates a standalone Windows executable using PyInstaller.
"""
import os
import subprocess
import sys
import shutil

def create_spec_file():
    """Create a PyInstaller spec file for the build."""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/*', 'assets'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'psutil',
        'win32gui',
        'win32process',
        'win32con',
        'win32api',
        'pywintypes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OpenGameBoost',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
    uac_admin=True,  # Request admin rights
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
)
'''
    with open('OpenGameBoost.spec', 'w') as f:
        f.write(spec_content)
    print("Created OpenGameBoost.spec")

def create_version_info():
    """Create version info file for Windows executable."""
    version_info = '''# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'OpenGameBoost'),
            StringStruct(u'FileDescription', u'Open Source Gaming Optimizer'),
            StringStruct(u'FileVersion', u'1.0.0.0'),
            StringStruct(u'InternalName', u'OpenGameBoost'),
            StringStruct(u'LegalCopyright', u'MIT License'),
            StringStruct(u'OriginalFilename', u'OpenGameBoost.exe'),
            StringStruct(u'ProductName', u'OpenGameBoost'),
            StringStruct(u'ProductVersion', u'1.0.0.0'),
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    with open('version_info.txt', 'w') as f:
        f.write(version_info)
    print("Created version_info.txt")

def create_default_icon():
    """Create a placeholder icon instruction."""
    os.makedirs('assets', exist_ok=True)
    readme_content = '''# Assets Directory

Place your icon file here as `icon.ico` to include it in the build.

You can create an icon using:
- https://www.icoconverter.com/
- GIMP
- ImageMagick

Recommended icon size: 256x256 pixels
'''
    with open('assets/README.md', 'w') as f:
        f.write(readme_content)
    print("Created assets directory")

def build():
    """Build the executable."""
    print("=" * 50)
    print("OpenGameBoost Build Script")
    print("=" * 50)
    
    # Check if running on Windows
    if sys.platform != 'win32':
        print("WARNING: This build script is designed for Windows.")
        print("Cross-compilation from Linux/Mac requires additional setup.")
        print("The executable should be built on a Windows machine.")
        print()
    
    # Create necessary files
    create_default_icon()
    create_version_info()
    create_spec_file()
    
    # Check for PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
    
    # Install dependencies
    print("\nInstalling dependencies...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    
    # Clean previous builds
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            print(f"Cleaning {folder}...")
            shutil.rmtree(folder)
    
    # Build
    print("\nBuilding executable...")
    result = subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        'OpenGameBoost.spec'
    ])
    
    if result.returncode == 0:
        print("\n" + "=" * 50)
        print("BUILD SUCCESSFUL!")
        print("=" * 50)
        print("\nThe executable is located at: dist/OpenGameBoost.exe")
    else:
        print("\n" + "=" * 50)
        print("BUILD FAILED!")
        print("=" * 50)
        print("Check the error messages above.")
    
    return result.returncode

def create_installer():
    """Create an installer using NSIS or Inno Setup (instructions only)."""
    installer_info = '''
# Creating an Installer

## Option 1: Inno Setup (Recommended)
1. Download Inno Setup: https://jrsoftware.org/isinfo.php
2. Use the following script template:

[Setup]
AppName=OpenGameBoost
AppVersion=1.0.0
DefaultDirName={pf}\\OpenGameBoost
DefaultGroupName=OpenGameBoost
OutputBaseFilename=OpenGameBoost_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

[Files]
Source: "dist\\OpenGameBoost.exe"; DestDir: "{app}"

[Icons]
Name: "{group}\\OpenGameBoost"; Filename: "{app}\\OpenGameBoost.exe"
Name: "{commondesktop}\\OpenGameBoost"; Filename: "{app}\\OpenGameBoost.exe"

[Run]
Filename: "{app}\\OpenGameBoost.exe"; Description: "Launch OpenGameBoost"; Flags: nowait postinstall skipifsilent

## Option 2: NSIS
Download NSIS: https://nsis.sourceforge.io/

## Option 3: Distribute as portable
The dist/OpenGameBoost.exe can be distributed as-is as a portable application.
'''
    with open('INSTALLER_GUIDE.md', 'w') as f:
        f.write(installer_info)
    print("Created INSTALLER_GUIDE.md")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--installer':
        create_installer()
    else:
        build()
        create_installer()
