"""Copy to PROJECT/test/manual_game.py; fill paths and optional save slot."""
from pathlib import Path
from contextlib import contextmanager
import sys

SKILL = Path('/absolute/path/to/rpgmaker-skills/skills/rpgmaker-playtest')
sys.path.insert(0, str(SKILL / 'scripts'))
from session import launch
from hooks import Hook, Hooks
from manual_test import collect_manual

PROJECT = Path(__file__).resolve().parents[1]
NWJS = '/absolute/path/to/nwjs'
SAVE_SLOT = None  # None: title screen; integer: load the existing save.

@contextmanager
def open_game(report_dir):
    hooks = Hooks()
    hooks.add(Hook('ready', on='game.ready'))
    hooks.add(Hook('error', on='runtime.error'))
    hooks.add(Hook('fatalError', on='runtime.error', fatal=True, action='finish'))
    hooks.add(Hook('warning', on='runtime.warning'))
    hooks.add(Hook('exit', on='process.exit'))
    with launch(PROJECT, NWJS, hooks=hooks, report_dir=report_dir) as game:
        if SAVE_SLOT is not None and not game.terminated:
            game.call('loadGame', slot=SAVE_SLOT)
        yield game

if __name__ == '__main__':
    collect_manual(open_game)
