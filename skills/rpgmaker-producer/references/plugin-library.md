# 备选插件库

用户提供候选来源，agent 根据实际需求匹配，不主动搜索新插件。此库保存选型摘要，不分发第三方插件源码。使用前在目标工程重新查询版本、注册路径、启用状态、参数和命令；不将来源工程的配置复制成通用默认值。

## 收录与证据

每批记录来源、读取日期、引擎和版本；每项必须记录准确的 JS 文件名（含扩展名）、工程内完整注册路径、插件官方说明/发布网页及其来源类型，再记录用途、适用/不适用场景、依赖与加载顺序、使用入口和验证状态。区分“用户提供的候选”“用户明确推荐”“已做运行验证”，不要由安装或启用状态推断推荐程度或兼容性。

本批：用户明确选定熟悉的 Core Engine、Message Core、Save Core，来源为 shadow 工程。另按用户要求收录地图两倍放大的 Zoom，另加入 FilterControllerMZ、WolfPadMVZ、CGMZ Core/GlobalData、TextPicture、LL_StandingPicture、MUSH_Audio_Engine，不因来源工程安装了其他插件而一并纳入。所有条目只经过本地声明、help 与注册清单读取，未做游戏运行验证。未核实项保持明确，不推测插件内部实现。

## 已整理

- [VisuMZ：用户选定的插件](plugins/visumz.md)：核心引擎、对话、存档，以及补充收录的 Events and Movement Core（角色阴影默认选型）。

选择时先检查目标工程现有能力，再考虑新增。核心扩展不因收录而成为新项目必装项；为一个小功能引入整个核心或依赖链不符合默认选型规则。禁用插件需要纳入已确认的实施方案后才能启用。

- [Zoom：地图两倍放大](plugins/zoom.md)：1080p 项目的地图显示比例候选，shadow 配置为 2.0。

## JS 名称与网页

| JS 文件名 | shadow 中路径（相对 js/plugins/） | 网页 |
| --- | --- | --- |
| `VisuMZ_0_CoreEngine.js` | `VisuMZ_0_CoreEngine.js` | [Core Engine 官方说明](http://www.yanfly.moe/wiki/Core_Engine_VisuStella_MZ) |
| `VisuMZ_1_MessageCore.js` | `ui/VisuMZ_1_MessageCore.js` | [Message Core 官方说明](http://www.yanfly.moe/wiki/Message_Core_VisuStella_MZ) |
| `VisuMZ_1_SaveCore.js` | `ui/VisuMZ_1_SaveCore.js` | [Save Core 官方说明](http://www.yanfly.moe/wiki/Save_Core_VisuStella_MZ) |
| `Zoom.js` | `visual/Zoom.js` | [ScSWinter 的 MultiTweaks 仓库](https://github.com/scswinter/MultiTweaks)（相关作者项目，非本地修改版发布页） |

Visu 网页来自本地插件的 `@url` 声明。Zoom 本地未声明发布网页；已核实 ScSWinter 的 MultiTweaks 仓库包含同类地图缩放功能，但尚未确认本地 Arthran、KuiMoiyri 修改版的独立发布页。不得将该仓库视作同版本 Zoom.js 的下载地址，也不因提供网页而引入整个 MultiTweaks。

## 新增候选与官方库范围

RPG Maker 官方附带插件整体纳入候选范围；按引擎版本和需求使用，不把第三方全系列自动纳入。

| 条目 | 用途与偏好 |
| --- | --- |
| [FilterControllerMZ.js](plugins/filter-controller.md) | 滤镜优先使用，不自行重写 |
| [WolfPadMVZ.js](plugins/wolfpad.md) | 手柄按键、摇杆和震动 |
| [CGMZ_Core.js / CGMZ_GlobalData.js](plugins/cgmz-global-data.md) | 基础依赖与跨存档数据、变量 |
| [官方附带库 / TextPicture.js](plugins/official-plugins.md) | 官方库整体候选；图片文字 |
| [LL_StandingPicture.js](plugins/ll-standing-picture.md) | 用户最常用的立绘插件，覆盖大部分立绘需求 |
| [MUSH_Audio_Engine.js](plugins/mush-audio.md) | 配音候选；大型音频引擎 |

各条目内记录完整注册路径、网页、使用入口和验证边界。

## 需要用户下载的插件

遇到 itch.io 等站点需要验证或手动下载时，列出插件名、作者下载页、所需 JS 文件名，请用户自行下载并提供本地路径，再继续读取分析。不要以其他工程的修改版代替原版。MUSH Audio Engine 的作者下载页为 https://kamo-studio.itch.io/rpg-maker-mz-plugin-mush-audio-engine ，所需文件为 `MUSH_Audio_Engine.js`。

## 平台接入

- [Cyclone-Steam.js](plugins/cyclone-steam.md)：Steamworks 接入与关键脚本接口，需配套 Greenworks、Steamworks SDK 和 NW.js。

## 地图光照

- [Community_Lighting_MZ.js](plugins/community-lighting.md)：光照效果候选；agent 布光效果可能不理想，需要实际画面与用户确认。

## 镜头动画

- [GALV_CamControlMZ.js](plugins/galv-cam-control.md)：镜头动画与剧情镜头首选，支持平滑移动、聚焦及恢复原版跟随。

## 脚步声

- [GabeMZ_StepSound.js](plugins/gabe-step-sound.md)：默认按地图区域 ID 标记脚步材质，从 131 开始分配。

## 多帧行走图

- [GALV_CharacterFramesMZ.js](plugins/galv-character-frames.md)：通过默认 `%(帧数)` 文件名标记支持多帧角色行走图。

## 动画库

- [GSAP / gsap.min.js](plugins/gsap.md)：复杂元素与 UI 动画候选；属于 JavaScript 动画库，放在 `js/plugins/tools/`，不作为普通 RM 功能插件描述。
