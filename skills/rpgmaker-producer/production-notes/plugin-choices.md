# 常用功能的插件选择

经验来源：用户于 2026-10-12 提供。以下记录用户的制作习惯，不代表本次已做运行测试。

- **滤镜**：FilterControllerMZ 非常好用，使用它，不自行重写滤镜功能。具体滤镜能力不够时先讨论缺口。
- **复杂元素与 UI 动画**：可以使用 [GSAP](../references/plugins/gsap.md) 动画库，放在 `js/plugins/tools/`；它不是 RM 功能插件。
- **镜头动画**：首选 `GALV_CamControlMZ.js`，使用其平滑镜头移动；默认聚焦玩家，需要原版跟随时使用 `disable`。见[镜头手记](how-to-control-the-camera.md)。
- **事件解谜**：尤其涉及事件的解谜效果，优先评估 `VisuMZ_1_EventsMoveCore.js`。使用前必须设置事件库并配置加载，且先阅读插件说明；见[事件库架构](../references/project-architecture.md#事件库)。
- **角色阴影**：默认使用 `VisuMZ_1_EventsMoveCore.js` 的脚下阴影功能；先检查现有配置和其他阴影插件，避免重复绘制。此偏好指普通脚下阴影，不代表已确认光源方向投影能力。
- **立绘**：LL_StandingPicture 是用户最常用的立绘插件，可以满足大部分立绘需求，常规立绘优先检查它。
- **本地化**：优先 VisuMZ Message Core，文本表格优先 TSV；以原版为准，见[本地化手记](how-to-localize-with-message-core.md)。
- **脚步声**：使用 `GabeMZ_StepSound.js`，默认用区域 ID 标记，从 131 开始；有无限图层素材时另行讨论，见[脚步声手记](how-to-add-footstep-sounds.md)。
- **配音**：用户使用 MUSH_Audio_Engine 做配音；它比较庞大，不为普通音效播放直接引入。
- **手柄**：WolfPad（准确文件名 WolfPadMVZ.js）作为手柄支持候选。
- **全局数据**：CGMZ_GlobalData 配合 CGMZ_Core，用于跨存档数据与变量；不要将普通存档变量一律设为全局。
- **官方附带插件**：整体属于备选范围；TextPicture 用于图片文字。这里的官方库是 RPG Maker 附带库，不是第三方作者全系列。

实际文件名、网页、依赖和使用入口统一查阅[备选插件库](../references/plugin-library.md)，不在手记重复维护参数手册。
