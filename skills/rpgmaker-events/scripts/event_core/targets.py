"""定位公共事件与地图事件页的数据库路径。"""
from __future__ import annotations

from .compiler import integer
from .backend import require, fields

def locate(target):
    require(isinstance(target, dict), 'target must be an object')
    if target.get('kind') == 'common':
        fields(target, {'kind', 'id'})
        return 'CommonEvents.json', [integer(target['id'], 1), 'list']
    fields(target, {'kind', 'map_id', 'event_id', 'page_index'})
    require(target['kind'] == 'map', 'kind must be common or map')
    return f"Map{integer(target['map_id'], 1):03}.json", ['events', integer(target['event_id'], 1), 'pages', integer(target['page_index']), 'list']
