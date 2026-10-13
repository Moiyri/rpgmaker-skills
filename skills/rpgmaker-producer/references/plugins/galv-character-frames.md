# GALV Character Frames MZ

准确文件名 `GALV_CharacterFramesMZ.js`，shadow 注册名 `visual/GALV_CharacterFramesMZ`，已启用。本地原版来源为 `插件Demo/GalvsMZPlugins_2023.12.13`，版本 1.0，面向 MZ。[作者网站](http://galvs-scripts.com)来自原版 `@url`；具体发布页尚未核对。

提供地图角色行走图多帧支持，突破默认每方向 3 帧。默认在文件名加入 `%(帧数)`，如 `$Veloria_Walk%(4).png`；文件实际布局须与帧数一致，命名统一见[命名规则](../naming-rules.md#素材文件与目录)。

使用前通过 `.manual()` 阅读说明，再查参数与当前值：`fileSymbol`（Filename Symbol）可改变 `%` 标记；`fSpeedMod`（Frame Speed Modifier）调整帧播放速度，公式中的 `f` 表示帧数，计算结果从引擎默认动画等待值中减去。

原版帮助说明会覆盖部分角色动画方法，与其他改动行走图动画的插件一起使用时需测试；若搭配 GALV Diagonal Movement，帮助要求本插件在其之前加载。不要直接推断与 VisuMZ 八方向图布局兼容。

已核对原版帮助、参数及 shadow 启用状态，未修改工程、未做运行测试。不分发第三方源码。
