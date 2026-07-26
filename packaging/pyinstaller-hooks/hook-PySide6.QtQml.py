import json
from pathlib import Path, PurePath
import subprocess

from PyInstaller.utils.hooks import get_hook_config
from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info


hiddenimports, binaries, datas = add_qt6_dependencies(__file__)


def hook(hook_api):
    qml_root = Path(get_hook_config(hook_api, "winter", "qml_root")).resolve()
    qml_source = Path(
        pyside6_library_info.location["QmlImportsPath"]
    ).resolve()
    scanner = (
        Path(pyside6_library_info.location["LibraryExecutablesPath"])
        / "qmlimportscanner.exe"
    )
    result = subprocess.run(
        [
            scanner,
            "-rootPath",
            qml_root,
            "-importPath",
            qml_source,
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    modules = {}
    for entry in json.loads(result.stdout):
        if entry.get("type") != "module" or "path" not in entry:
            continue
        module_directory = Path(entry["path"]).resolve()
        if module_directory.is_relative_to(qml_source):
            modules[module_directory] = entry.get("plugin")

    qml_destination = PurePath(pyside6_library_info.qt_rel_dir) / "qml"
    qml_binaries = []
    qml_datas = []
    for module_directory, plugin in sorted(modules.items()):
        qmldir = module_directory / "qmldir"
        if not qmldir.is_file():
            raise RuntimeError(f"Scanned QML module has no qmldir: {module_directory}")
        if plugin and not (module_directory / f"{plugin}.dll").is_file():
            raise RuntimeError(
                f"Scanned QML module has no plugin binary: {module_directory}"
            )

        nested_modules = {
            path.parent
            for path in module_directory.rglob("qmldir")
            if path.parent != module_directory
        }
        for source in module_directory.rglob("*"):
            if not source.is_file() or any(
                nested in source.parents for nested in nested_modules
            ):
                continue
            destination = qml_destination / source.relative_to(
                qml_source
            ).parent
            entry = (str(source), str(destination))
            if source.suffix.casefold() == ".dll":
                qml_binaries.append(entry)
            else:
                qml_datas.append(entry)

    hook_api.add_binaries(qml_binaries)
    hook_api.add_datas(qml_datas)
