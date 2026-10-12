"""给 VisuMZ Message 的支持语言列表添加 German。

只通过插件接口查询和修改。默认预览，显式 --write 才提交。
本脚本仅扩展插件语言选项，不创建德语翻译内容。
用法：python3 add_message_language.py PROJECT [--write]
"""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from plugins import Plugins


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    plugins=Plugins(args.project)
    message=plugins.get('VisuMZ_1_MessageCore')
    path=['Localization:struct','Languages:arraystr']
    print(message.help())
    if 'German' in message.parameters.get(path):
        print('German 已存在，不重复添加。')
        return
    message.parameters.append(path,'German')
    preview=plugins.preview()
    print(preview['diff'])
    if args.write:
        print(plugins.commit(preview))

if __name__=='__main__':
    main()
