"""修改 Liy_Graphics 地图 72 的 black 层脚本。

用法：python3 edit_black_layer_script.py PROJECT NEW_SCRIPT.js [--write]
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from plugins import Plugins


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('script_file', type=Path)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()

    plugins = Plugins(args.project)
    parameters = plugins.get('Liy_Graphics').parameters
    map_path = ['mapLayerSetting', 70]
    layer_path = map_path + ['layers', 3]
    # 下标来自查询；配置顺序变化时停止，避免误改其他地图或图层。
    if parameters.get(map_path + ['mapId']) != 72:
        raise ValueError('地图下标已变化，请重新查询地图 72')
    if parameters.get(layer_path + ['layerBitmap']) != 'black':
        raise ValueError('图层下标已变化，请重新查询 black 层')
    path = layer_path + ['script']
    print(parameters.help('LayerSprite'))
    # 保留 JavaScript 文件原有换行，不手动处理插件参数的 JSON 编码。
    new_script = args.script_file.read_bytes().decode('utf-8-sig')
    parameters.set(path, new_script)
    preview = plugins.preview()
    print(preview['diff'])
    if args.write:
        print(plugins.commit(preview))


if __name__ == '__main__':
    main()
