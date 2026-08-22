# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['mac.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('app.py', '.')],
    hiddenimports=[],
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
    name='Loqin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    name='Loqin.app',
    icon='assets/loqin_logo_small.icns',
    bundle_identifier='com.notaayushsrivastava.loqin',
    info_plist={
        'CFBundleName': 'Loqin',
        'CFBundleDisplayName': 'Loqin',
        'CFBundleShortVersionString': '1.7.0',
        'CFBundleVersion': '1.7.0',
        'NSHumanReadableCopyright': 'Copyright © 2026 Aayush Srivastava',
        'NSLocationWhenInUseUsageDescription': 'Loqin needs location access to scan for nearby VIT Wi-Fi networks for automatic login.',
        'NSLocationUsageDescription': 'Loqin needs location access to scan for nearby VIT Wi-Fi networks for automatic login.'
    },
)
