"""Compatibility entrypoint; plugin declarations belong to rpgmaker-plugins."""
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parents[3] / 'rpgmaker-plugins/scripts/plugin_core/declarations.py'
if not _path.is_file():
    raise ImportError('Plugin help requires the sibling rpgmaker-plugins skill')
_spec = importlib.util.spec_from_file_location('_rpgmaker_plugin_declarations', _path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
_plugin_metadata = _module._plugin_metadata
plugin_help = _module.plugin_help
