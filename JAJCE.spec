# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata, collect_data_files

block_cipher = None

# Custom datas: bin executables and UI assets
datas = [
    ('assets', 'assets'),
    ('bin', 'bin'),
]
binaries = []
hiddenimports = [
    'piexif',
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PIL',
    'PIL.Image',
    'PIL.JpegImagePlugin',
    'PIL.PngImagePlugin',
    'PIL.WebPImagePlugin',
    'transformers',
    'transformers.models.smolvlm',
    'transformers.models.smolvlm.processing_smolvlm',
    'transformers.models.smolvlm.modeling_smolvlm',
    'transformers.models.auto',
    'transformers.models.auto.processing_auto',
    'tokenizers',
    'accelerate',
    'safetensors',
    'huggingface_hub',
]

# Copy critical metadata for HuggingFace ecosystem
for pkg in ['transformers', 'tokenizers', 'huggingface_hub', 'safetensors', 'accelerate', 'torch', 'tqdm', 'regex', 'requests', 'packaging', 'filelock']:
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

# Collect tokenizers and transformers data files & submodules
for pkg in ['tokenizers', 'transformers', 'accelerate']:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as e:
        print(f"Warning collecting {pkg}: {e}")

# De-duplicate
hiddenimports = sorted(list(set(hiddenimports)))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'tensorboard',
        'torch.utils.tensorboard',
        'IPython',
        'notebook',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JAJCE',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='JAJCE',
)
