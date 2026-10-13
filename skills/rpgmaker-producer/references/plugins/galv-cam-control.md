# GALV Cam Control MZ

## 选型与来源

用户指定为镜头动画、剧情镜头的首选插件：移动镜头带有用户偏好的平滑缓动效果。准确文件名 `GALV_CamControlMZ.js`，shadow 完整注册名 `visual/GALV_CamControlMZ`，当前启用。

本地原版来源为 `插件Demo/GalvsMZPlugins_2023.12.13`，版本 1.8，面向 MZ。通过正式 `manual` 和命令帮助接口核对用法。[作者网站](http://galvs-scripts.com)来自本地 `@url` 声明；具体插件发布页尚未核对。本库不分发第三方源码。

## 命令入口

| 命令 ID | 用途 |
| --- | --- |
| `focusCharacter` | 聚焦角色；`charId=0` 为玩家，其他值为事件 ID |
| `focusXY` | 聚焦地图坐标 |
| `disable` | 恢复聚焦玩家并关闭平滑移动，使用 RM 原版镜头跟随 |
| `waitForCam` | 等待镜头移动完成；持续移动的目标可能导致等待无法结束 |
| `zoom` | 镜头缩放，倍率与持续帧数通过命令指定 |

聚焦命令的 speed 值越大，镜头越慢。使用前查询 `.commands.help(id)`，不要按直觉反向设置。使用聚焦命令会重新启用平滑镜头。插件自身的镜头缩放与 `Zoom.js` 的地图显示倍率分别核对，不混用两者。

使用习惯、滚动和地图传送注意事项见[制作手记](../../production-notes/how-to-control-the-camera.md)。只完成本地声明、帮助与启用状态核对，未运行画面测试。
