# VisuMZ 首批候选

读取日期：2026-10-12。来源：`/Users/moiyri/Game/RPGMaker/Projects/the-shadow/main`，插件位于 `js/plugins/`。来源路径用于追溯，不是其他用户工程的固定依赖。

证据为各插件 `@plugindesc`、`@base`、`@help`、参数及命令声明，以及正式插件脚本读取的注册状态。下面是本地版本快照，不代表最新版本。用户明确选定以下 3 个重要且熟悉的插件；本次未执行 Playtest。

## 索引

| 插件及完整注册名 | 版本 | shadow 状态 | 主要用途 | 选型边界 |
| --- | --- | --- | --- | --- |
| `VisuMZ_0_CoreEngine` | 1.82 | 启用 | 引擎修正、窗口与 UI 基础设置、图片/音频等通用扩展 | 基础核心，影响广；现有工程优先复用，不为单个小改动新增 |
| `ui/VisuMZ_1_MessageCore` | 1.54 | 启用 | 消息样式、文本控制符、自动换行、选择项扩展、多语言 | 已有对话体系适合先查；不为一个字号改动引入整个消息核心 |
| `ui/VisuMZ_1_SaveCore` | 1.09 | 启用 | 存档界面、存档模式、自动存档、跨存档数据 | 不止改界面；先核对存档行为是否也符合需求 |

这 3 个版本面向 RPG Maker MZ，不能推定适用于 MV。Message Core 和 Save Core 两个 Tier 1 插件均声明 `@base VisuMZ_0_CoreEngine`。按帮助要求低 Tier 在前，CoreEngine 在这些 Tier 1 插件之前；同 Tier 的实际相互顺序需要结合具体功能核对，不按文件名自动排序。依赖存在不代表某功能已配置或启用。

## Core Engine

适合复用：工程已有该核心，需要调整窗口、文本颜色、UI 按钮、图片显示或通用事件辅助功能。它还涉及机制与引擎修正，不能视作单一界面皮肤。

查询入口示例：`PictureEasingType`、`PictureShowIcon`、`SystemSetFontSize`、`SystemSetWindowPadding`、`TextPopupShow`。这些是命令 ID，使用前查询参数帮助，不凭名称构造事件参数。

## Message Core

适合复用：消息窗口设置、扩展文本控制符、自动换行、选项显示/禁用、扩展选择列表。帮助包含 Text Language 功能与 CSV/TSV 数据说明；不是自动翻译，也不能假设 shadow 当前自定义本地化方案与它相同。

本地化优先使用 Message Core 的 Text Language，表格优先 TSV。原版依据为用户提供的 `/Users/moiyri/Game/RPGMaker/插件Demo/VisuMZ_Sample_Game_Project 2/js/plugins/VisuMZ_1_MessageCore.js`，已通过正式 `manual` 和 `help --struct Localization` 接口核对。shadow 的本地化被用户修改为多文件方案，不作为原版能力依据。原版配置入口是 `Localization:struct`，通过 `LangFiletype:str = tsv` 选择格式，`TsvFilename:str` 指定 `data/` 下的表格文件；不得把多文件拆分描述为原版功能。使用偏好见[本地化手记](../../production-notes/how-to-localize-with-message-core.md)。

命令入口：`MessageWindowProperties`、`MessageWindowXyOffsets`、`ChoiceWindowProperties`、`ChoiceWindowDistance`，以及 `SelectWeapon`、`SelectArmor`、`SelectSkill`。动态文本代码需查原 help 的具体语法与作用范围。

## Save Core

适合复用：存档列表展示、说明/图片、自动保存、标准/锁定槽/单存档模式。跨存档开关变量用 `<Global>` 名称标签，实际使用需核对与其他标签的互斥规则；普通功能不应自动改成全局数据。

命令入口：`AutosaveEnable`、`AutosaveRequest`、`AutosaveExecute`、`AutosaveForce`、`SaveCurrentSlot`、`SaveDescription`、`SavePicture`。Request、Execute、Force 对自动保存开关的处理不同，不能互换；查 help 后决定，测试时使用可覆盖的测试存档。

## 实际使用时

加载 rpgmaker-plugins，使用 `Plugins(project).get(完整注册名)` 查询 `.help()`、`.parameters.list()`、`.commands.list()` 与 `.commands.help(command_id)`。先通过 `.manual()` 读取插件用法，再按所需功能查询参数帮助；仅当接口无法提供必要信息时定向读取源码，保留子目录注册名；上述示例不是完整命令清单。

只核对需求涉及的参数、素材、依赖和交互点；检查是否与工程自定义插件重复接管同一功能。通过正式脚本预览配置修改，再在已确认范围写入，实际游戏验证后才更新条目的验证记录。

## 补充：Events and Movement Core

用户于 2026-10-12 明确：角色脚下阴影默认使用 `VisuMZ_1_EventsMoveCore.js`。shadow 完整注册名为 `gameplay/VisuMZ_1_EventsMoveCore`，已启用。原版用法依据为用户提供的 `VisuMZ_Sample_Game_Project 2`，本地版本 1.60；通过正式 `manual` 接口核对，未做游戏运行测试。

[官方说明](http://www.yanfly.moe/wiki/Events_and_Movement_Core_VisuStella_MZ)（地址来自原版 `@url` 声明）。该插件为 MZ Tier 1；完整依赖与加载顺序使用前按目标版本帮助核对。

- Movement Settings → Shadows → Show：显示事件和玩家角色的脚下阴影。
- Default Filename：指定 `img/system/` 下的阴影图片。
- `<Hide Shadow>`：隐藏事件阴影。
- `<Shadow Filename: filename>`：指定事件阴影图片。

标签放在事件备注时跨事件页生效，放在事件页注释时仅当前页生效。先读取 `.manual()`，再通过参数帮助与当前值确定配置，不凭界面显示名猜参数键。shadow 同时启用了 GALV 阴影插件，实施前检查是否重复绘制；本次选型记录不授权自动禁用或修改任何工程插件。不要将这里的脚下图片阴影表述为随光源方向变化的角色投影。

### 事件解谜与事件库

制作解谜效果，尤其涉及事件时，优先评估本插件现有功能：事件模板的复制／替换／生成、区域规则、碰撞范围、扩展触发、同步移动、独立数据和事件位置保存。按实际需求查询用法，不凭功能名称推断实现。

用户要求：使用插件前必须先设置事件库并配置加载，具体前置步骤见[项目架构中的事件库](../project-architecture.md#事件库)。使用时必须通过 `.manual()` 阅读插件说明，尤其是 Event Template Settings 与所用功能章节，再查参数或命令帮助；不直接按记忆构造配置或标签。此条为用户工程约定，区分于插件单项功能的技术依赖。
