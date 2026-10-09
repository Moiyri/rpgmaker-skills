"""Movement 指令入门示例。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from event_api import EventList, SetMovementRoute, SetEventLocation, ScrollMap, Route

event = EventList([
    SetEventLocation(1, x=5, y=6, direction='down'),
    SetMovementRoute(-1, [
        Route.move('right'),
        Route.jump(0, -1),
        Route.turn('down'),
        Route.wait(30),
    ], skippable=True, wait=True),
    ScrollMap('up', distance=3, speed=4, wait=True),
])

if __name__ == '__main__':
    print(event.compile())
