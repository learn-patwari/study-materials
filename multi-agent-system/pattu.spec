# PyInstaller build spec for Pattu.
#
#   pip install pyinstaller
#   pyinstaller pattu.spec
#
# Produces dist/Pattu.exe — a single windowed executable with the artwork
# bundled. Assets are read through gui/assets.py, which checks sys._MEIPASS
# first, so the frozen build finds them in the unpacked bundle.

block_cipher = None

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    # Only the processed art is bundled. assets/raw/ is build-time input and
    # would roughly double the executable for no runtime benefit.
    datas=[
        ("assets/mascot", "assets/mascot"),
        ("assets/icons", "assets/icons"),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["PIL", "numpy", "pytest"],
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
    name="Pattu",
    console=False,          # no terminal window behind the mascot
    icon="assets/icons/pattu.ico",
    upx=True,
    strip=False,
    debug=False,
    bootloader_ignore_signals=False,
    disable_windowed_traceback=False,
)
