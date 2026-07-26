from pathlib import Path


project = Path(SPECPATH).parent


analysis = Analysis(
    [str(project / "src" / "winter" / "__main__.py")],
    pathex=[str(project / "src")],
    binaries=[],
    datas=[
        (
            str(project / "src" / "winter" / "ui" / "qml"),
            "winter/ui/qml",
        ),
        (str(project / "assets" / "winter.ico"), "winter/assets"),
    ],
    hiddenimports=[],
    hookspath=[str(project / "packaging" / "pyinstaller-hooks")],
    hooksconfig={
        "winter": {
            "qml_root": str(project / "src" / "winter" / "ui" / "qml"),
        },
    },
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2", "tkinter"],
    noarchive=False,
    optimize=1,
)

python_archive = PYZ(analysis.pure)

executable = EXE(
    python_archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Winter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon=str(project / "assets" / "winter.ico"),
    codesign_identity=None,
    entitlements_file=None,
)

distribution = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Winter",
)
