# 修改分辨率

## 使用插件

- `Zoom.js`：调整地图显示倍率，见[插件参考](../references/plugins/zoom.md)。
- `VisuMZ_0_CoreEngine.js`：开启完美像素（Pixel Image Rendering），见[官方说明](http://www.yanfly.moe/wiki/Core_Engine_VisuStella_MZ)。

## 修改流程

提高游戏分辨率时，在数据库「系统」的 **Advanced Settings** 中，同时修改屏幕宽高和 UI 区域宽高，使二者匹配目标尺寸。再设置 Zoom 的地图倍率，并打开完美像素。

| 目标 | 屏幕宽 × 高 | UI 区域宽 × 高 | Zoom 倍率 |
| --- | --- | --- | --- |
| 1080p | 1920 × 1080 | 1920 × 1080 | 2.0 |
| 720p | 1280 × 720 | 1280 × 720 | 1.5 |

这是用户的制作搭配约定。修改后检查地图可见范围，以及对话框、菜单、立绘和其他 UI 的尺寸与位置。

在 `VisuMZ_0_CoreEngine.js` 中设置：

`Quality of Life Settings → Misc → Pixel Image Rendering = true`

准确参数路径为 `["QoL:struct", "PixelateImageRendering:eval"]`。这里的完美像素指上述像素化选项；`Font Smoothing` 是字体设置。

agent 实施时，数据库设置通过 rpgmaker-database 修改；插件配置先通过 rpgmaker-plugins 的 `manual`、`help` 查询用法、声明和当前值，再用正式脚本预览与提交。

## 非整数倍率提醒

采用 720p、Zoom 1.5 倍时，必须向用户说明：**非整数缩放倍率会使源像素映射到不均匀的屏幕像素宽度，可能出现像素拉伸、变形或边缘不均匀，建议改用整数倍缩放。**

风险来自缩放倍率，不是分辨率数值本身。开启完美像素可以避免平滑模糊，但不能消除非整数倍率带来的像素不均匀。向用户提出整数倍率方案后，由用户确定最终分辨率与倍率。

## 检查效果

实际运行检查图块与角色的像素边缘，确认地图倍率正确；再检查菜单、对话框、标题和立绘的位置、裁切及可操作区域。配置读取与静态检查通过不代表画面已验证。

## 来源与核对

- 用户于 2026-10-12 确认屏幕与 UI 区域同步设置、1080p 配 2 倍、720p 配 1.5 倍及非整数倍率提醒。
- 完美像素参数已核对 shadow 的 Core Engine 1.82 声明，默认 false；Zoom 的本地版本与修改版来源见插件参考。
- 本次更新制作手记，未修改游戏配置，未执行画面对比测试。
