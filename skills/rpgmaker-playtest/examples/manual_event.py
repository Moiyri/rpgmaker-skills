"""Copy to PROJECT/test/manual_event.py and fill in the skill path, NW.js and source event."""
from pathlib import Path
import sys

SKILL = Path('/absolute/path/to/rpgmaker-skills/skills/rpgmaker-playtest')
sys.path.insert(0, str(SKILL / 'scripts'))
from manual_test import collect_manual
from event_test import launch_event_test
from hooks import Hook, Hooks

PROJECT = Path(__file__).resolve().parents[1]
NWJS = '/absolute/path/to/nwjs'

if __name__ == '__main__':
    hooks = Hooks()
    hooks.add(Hook('ready', on='game.ready'))
    hooks.add(Hook('error', on='runtime.error'))
    hooks.add(Hook('fatalError', on='runtime.error', fatal=True, action='finish'))
    hooks.add(Hook('warning', on='runtime.warning'))
    hooks.add(Hook('calls', on='event.call'))
    hooks.add(Hook('end', on='event.end'))
    hooks.add(Hook('exit', on='process.exit'))
    # No event-end finish here: the user can inspect the final scene, then close the game.
    collect_manual(lambda report_dir: launch_event_test(
        PROJECT, NWJS, common_event_id=138, hooks=hooks, report_dir=report_dir,
    ))
