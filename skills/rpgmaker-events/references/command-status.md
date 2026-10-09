# 事件指令实现状态

范围：RPG Maker MZ 公共事件、地图事件页中的事件指令。清单依据工程 `the-shadow/main/js/rmmz_objects.js`（运行时 1.9.0），包含该源码中的全部 command 方法及已知续行、结束标记。移动路线内部指令见下方分组表；第三方插件自定义命令不逐项列出。

“已实现”表示具有专用对象、编译、解码和行为测试；“部分实现”表示参数分型未覆盖全部。未实现指令可在结构可识别时由 OpaqueCommand 整体保留，不等于可语义编辑。非标准扩展参数也可能回退为原始块。源码 docstring 是接口用法的依据。

当前有 52 类主指令具备对象接口，其中 3 类部分实现。以下编译和解码状态均针对支持的标准参数。

## 指令总表

| 代码 | 引擎指令 | 编译 | 解码 | 接口／边界 |
|---|---|---|---|---|
| 0 | End / 空指令 | 自动生成 | 已识别 | 结束标记，无独立对象 |
| 101 | Show Text | 已实现 | 已实现 | `ShowText`；单窗口 1–4 行；MZ 五参数头 |
| 102 | Show Choices | 部分实现 | 部分实现 | ShowChoices；1–6 项、默认项、取消映射或禁用；固定右侧普通背景，独立取消分支未实现 |
| 103 | Input Number | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 104 | Select Item | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 105 | Show Scrolling Text | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 108 | Comment | 已实现 | 已实现 | `Comment`；多行注释，自动生成 408 |
| 109 | Skip | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 111 | Conditional Branch | 部分实现 | 部分实现 | `If`；支持条件见下表；其余条件整体保留 |
| 112 | Loop | 已实现 | 已实现 | `Loop`；必须配合可执行到的 BreakLoop 退出 |
| 113 | Break Loop | 已实现 | 已实现 | `BreakLoop`；必须在循环内 |
| 115 | Exit Event Processing | 已实现 | 已实现 | `ExitEvent`；结束当前事件；调用者可继续 |
| 117 | Common Event | 已实现 | 已实现 | `CommonEvent`；新增调用检查公共事件存在 |
| 118 | Label | 已实现 | 已实现 | `Label`；当前列表的标签；名称应唯一 |
| 119 | Jump to Label | 已实现 | 已实现 | `JumpToLabel`；当前列表内同名标签跳转；不静态验证标签存在或唯一性 |
| 121 | Control Switches | 已实现 | 已实现 | `SetSwitch`；单个或连续范围，ON/OFF |
| 122 | Control Variables | 部分实现 | 部分实现 | `ChangeVariable`；六种运算；Game Data 使用 ScriptValue，原生类型 3 未解码 |
| 123 | Control Self Switch | 已实现 | 已实现 | `SetSelfSwitch`；A–D；需要地图事件上下文 |
| 124 | Control Timer | 已实现 | 已实现 | `StartTimer / StopTimer`；全局计时器，非负整数秒；启动不等待结束 |
| 125 | Change Gold | 已实现 | 已实现 | `ChangeGold`；add/sub；Constant 或 VariableValue |
| 126 | Change Items | 已实现 | 已实现 | `ChangeItems`；物品 ID；add/sub；Constant 或 VariableValue |
| 127 | Change Weapons | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 128 | Change Armors | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 129 | Change Party Member | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 132 | Change Battle BGM | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 133 | Change Victory ME | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 134 | Change Save Access | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 135 | Change Menu Access | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 136 | Change Encounter | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 137 | Change Formation Access | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 138 | Change Window Color | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 139 | Change Defeat ME | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 140 | Change Vehicle BGM | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 201 | Transfer Player | 已实现 | 已实现 | `TransferPlayer`；直接／变量指定地图与坐标，朝向和淡出；不校验目标地图边界 |
| 202 | Set Vehicle Location | 已实现 | 已实现 | `SetVehicleLocation`；小船／大船／飞艇；直接或变量指定地图与坐标 |
| 203 | Set Event Location | 已实现 | 已实现 | `SetEventLocation`；直接坐标／变量坐标／交换事件位置；保留或指定朝向 |
| 204 | Scroll Map | 已实现 | 已实现 | `ScrollMap`；四方向、距离、速度、等待完成 |
| 205 | Set Movement Route | 已实现 | 已实现 | `SetMovementRoute`；Route 步骤列表，重复／跳过／等待；拒绝重复且等待 |
| 206 | Get on/off Vehicle | 已实现 | 已实现 | `GetOnOffVehicle`；切换玩家乘降；需符合引擎乘降条件 |
| 211 | Change Transparency | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 212 | Show Animation | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 213 | Show Balloon Icon | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 214 | Erase Event | 已实现 | 已实现 | `EraseEvent`；需要当前地图事件上下文；不永久删除，后续指令仍可执行 |
| 216 | Change Player Followers | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 217 | Gather Followers | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 221 | Fadeout Screen | 已实现 | 已实现 | `FadeoutScreen`；无参数；引擎控制时长并等待 |
| 222 | Fadein Screen | 已实现 | 已实现 | `FadeinScreen`；无参数；引擎控制时长并等待 |
| 223 | Tint Screen | 已实现 | 已实现 | `TintScreen`；RGB -255–255、灰度 0–255、非负帧数和等待 |
| 224 | Flash Screen | 已实现 | 已实现 | `FlashScreen`；RGB 与强度 0–255、正整数帧数和等待 |
| 225 | Shake Screen | 已实现 | 已实现 | `ShakeScreen`；强度／速度 1–9、正整数帧数和等待 |
| 230 | Wait | 已实现 | 已实现 | `Wait`；正整数帧数，不是毫秒 |
| 231 | Show Picture | 已实现 | 已实现 | `ShowPicture`；编号 1–100；图像、原点、直接／变量坐标、缩放、透明度、混合模式 |
| 232 | Move Picture | 已实现 | 已实现 | `MovePicture`；同显示图片的位置及效果；时长、等待、四种缓动；标准 MZ 13 参数，旧 12 参数原样保留 |
| 233 | Rotate Picture | 已实现 | 已实现 | `RotatePicture`；持续旋转速度 -90–90；0 停止，不是角度 |
| 234 | Tint Picture | 已实现 | 已实现 | `TintPicture`；RGB -255–255、灰度 0–255、时长与等待 |
| 235 | Erase Picture | 已实现 | 已实现 | `ErasePicture`；按编号清除图片 |
| 236 | Set Weather Effect | 已实现 | 已实现 | `SetWeatherEffect`；none/rain/storm/snow；强度 1–9、非负帧数和等待；战斗中不生效 |
| 241 | Play BGM | 已实现 | 已实现 | `PlayBGM`；名称、音量、音调、声像；空名称停止 BGM |
| 242 | Fadeout BGM | 已实现 | 已实现 | `FadeoutBGM`；非负整数秒，不自动等待 |
| 243 | Save BGM | 已实现 | 已实现 | `SaveBGM`；记住 BGM 与播放位置，不是游戏存档 |
| 244 | Resume BGM | 已实现 | 已实现 | `ReplayBGM`；恢复已保存 BGM 与位置 |
| 245 | Play BGS | 已实现 | 已实现 | `PlayBGS`；名称、音量、音调、声像；空名称停止 BGS |
| 246 | Fadeout BGS | 已实现 | 已实现 | `FadeoutBGS`；非负整数秒，不自动等待 |
| 249 | Play ME | 已实现 | 已实现 | `PlayME`；播放一次，暂时中断 BGM；空名称停止 ME |
| 250 | Play SE | 已实现 | 已实现 | `PlaySE`；播放一次，可叠加；空名称不播放 |
| 251 | Stop SE | 已实现 | 已实现 | `StopSE`；停止当前全部 SE |
| 261 | Play Movie | 已实现 | 已实现 | `PlayMovie`；不含扩展名的影片路径；引擎选择 webm/mp4 并等待，空名称不播放 |
| 281 | Change Map Name Display | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 282 | Change Tileset | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 283 | Change Battle Background | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 284 | Change Parallax | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 285 | Get Location Info | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 301 | Battle Processing | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 302 | Shop Processing | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 303 | Name Input Processing | 已实现 | 已实现 | `NameInput`；角色 ID、最大字符数 1–16；角色存在性需另核对，战斗中不生效 |
| 311 | Change HP | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 312 | Change MP | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 313 | Change State | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 314 | Recover All | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 315 | Change EXP | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 316 | Change Level | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 317 | Change Parameter | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 318 | Change Skill | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 319 | Change Equipment | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 320 | Change Name | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 321 | Change Class | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 322 | Change Actor Images | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 323 | Change Vehicle Image | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 324 | Change Nickname | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 325 | Change Profile | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 326 | Change TP | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 331 | Change Enemy HP | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 332 | Change Enemy MP | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 333 | Change Enemy State | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 334 | Enemy Recover All | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 335 | Enemy Appear | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 336 | Enemy Transform | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 337 | Show Battle Animation | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 339 | Force Action | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 340 | Abort Battle | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 342 | Change Enemy TP | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 351 | Open Menu Screen | 已实现 | 已实现 | `OpenMenu`；打开菜单，战斗中不生效 |
| 352 | Open Save Screen | 已实现 | 已实现 | `OpenSave`；打开存档界面，不自动存档，战斗中不生效 |
| 353 | Game Over | 已实现 | 已实现 | `GameOver`；切换游戏结束画面，不自动保存 |
| 354 | Return to Title Screen | 已实现 | 已实现 | `ReturnToTitle`；返回标题画面，不自动保存 |
| 355 | Script | 已实现 | 已实现 | `Script`；多行 JavaScript；仅在游戏运行时执行，不校验 JS 语法 |
| 356 | Plugin Command MV (deprecated) | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 357 | Plugin Command | 已实现 | 已实现 | `PluginCommand`，`plugin_help` 查询声明与用法；MZ 插件名、命令 ID、显示名称和字符串参数；不校验插件注册或自动填默认值 |
| 401 | Text line / 文字续行 | 自动生成 | 已识别 | 随 ShowText 处理，无独立对象 |
| 402 | When [**] | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 403 | When Cancel | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 404 | End Choices / 选项结束 | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 405 | Scrolling text line / 滚动文字续行 | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 408 | Comment line / 注释续行 | 自动生成 | 已识别 | 随 Comment 处理，无独立对象 |
| 409 | End Skip / 跳过块结束 | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 411 | Else | 自动生成 | 已识别 | 随 If 处理，无独立对象 |
| 412 | End Branch / 分支结束 | 自动生成 | 已识别 | 随 If 处理，无独立对象 |
| 413 | Repeat Above | 自动生成 | 已识别 | 随 Loop 处理，无独立对象 |
| 505 | Movement route continuation / 移动路线续行 | 自动生成 | 随 205 解码 | 与路线列表同步；不一致或扩展结构整块保留 |
| 601 | If Win | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 602 | If Escape | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 603 | If Lose | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 604 | End Battle Processing / 战斗分支结束 | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 605 | Shop goods continuation / 商品续行 | 未实现 | 原始块保留 | 无专用对象；需结构可识别 |
| 655 | Script continuation / 脚本续行 | 自动生成 | 已识别 | 随 Script 处理，无独立对象 |
| 657 | Plugin command annotation / 插件命令参数说明 | 自动生成 | 随主指令解码 | `PluginCommand.argument_labels`；特殊说明原样保留，修改参数时需提供完整标签 |

## 条件分支参数

| 条件类型 | 状态 | 接口／说明 |
|---|---|---|
| 开关 | 已实现 | Switch.is_on / is_off |
| 变量 | 已实现 | 六种比较，常量或另一变量 |
| 独立开关 | 已实现 | SelfSwitch.is_on / is_off；A–D |
| 计时器 | 未实现 | 原始块保留；与 StartTimer/StopTimer 指令不同 |
| 角色 | 部分实现 | Actor.in_party / name_equals；职业、技能、武器、防具、状态未实现 |
| 敌人 | 未实现 | 原始块保留 |
| 人物朝向 | 已实现 | Character.facing；玩家、本事件、地图事件 |
| 金币 | 未实现 | 原始块保留 |
| 物品 | 已实现 | Item.is_owned |
| 武器 | 未实现 | 原始块保留 |
| 防具 | 未实现 | 原始块保留 |
| 按钮 | 已实现 | Button.is_pressed / is_triggered / is_repeated；标准逻辑按钮 |
| 脚本 | 已实现 | ScriptCondition；编译时不执行 |
| 交通工具 | 未实现 | 原始块保留 |

## 控制变量参数

| 功能 | 状态 | 接口／说明 |
|---|---|---|
| 单个／范围 | 已实现 | id / end，包含两端 |
| 赋值、加减乘除、取模 | 已实现 | set / add / sub / mul / div / mod |
| 常量 | 已实现 | Constant |
| 变量值 | 已实现 | VariableValue |
| 随机整数 | 已实现 | RandomValue，包含两端 |
| Game Data | 脚本替代 | 使用 ScriptValue 读取数据；原生操作数类型 3 保留为原始指令 |
| 脚本表达式 | 已实现 | ScriptValue；由游戏运行时求值 |

## 验证记录

最近一轮回归：119 项标准测试，115 项通过、4 项可选工程集成测试未启用。启用集成后 118 项通过，1 项因工程公共事件 165 已清空、不再符合历史夹具而失败。公共事件 165 用作结构参考，公共事件 167 已完成条件和开关范围的脚本写入核对；这不表示所有指令均经过编辑器 UI 或完整 Playtest 验证。

验证入口：`python3 -m unittest discover -s tests -v`。集成测试需设置 `RPGMAKER_EVENTS_PROJECT` 和 `RPGMAKER_TEST_PROJECT`；未设置时明确记录跳过项。新增指令需同步更新本表的主指令、参数分型、限制及验证记录。

本轮新增注释、金币、物品、移动玩家、等待、暂时消除事件和脚本：覆盖参数编码、嵌套往返、解码后修改、多行边界、非法输入及扩展参数保留；未写入实际工程，未进行完整 Playtest。

本轮新增插件命令：依据工程 command357 源码，使用公共事件 6 的 ScreenZoom/set 及其 657 说明行作结构夹具；覆盖精确往返、参数修改、嵌套、字符串编码、无参数调用、非法输入、特殊说明与扩展字段保留。写回沿用已有保格式数据库后端；本轮未修改实际工程，未执行插件或进行编辑器／游戏 Playtest。

## 地图事件管理状态

| 功能 | 状态 | 接口／边界 |
|---|---|---|
| 全局事件名称搜索 | 已实现 | search_events(name=...)；地图页和公共事件；大小写不敏感子串 |
| 全局开关／变量引用搜索 | 已实现（静态范围） | search_events(switch=... / variable=...)；页条件、公共触发开关、已知原生指令、移动路线开关；脚本和插件动态引用不解析 |
| 列出地图所有事件 | 已实现 | list_map；含名称、备注、坐标、全部页摘要 |
| 创建地图事件 | 已实现 | MapDocument.create_event；复用空闲 ID 或追加，不能覆盖已有事件 |
| 删除地图事件 | 已实现 | delete_event；置 null，不移动其他 ID，不自动修复引用 |
| 编辑名称、备注和坐标 | 已实现 | MapEvent.name / note / x / y；note 默认留空或保留，仅特殊用途编辑；导出检查地图边界 |
| 页出现条件 | 已实现 | set_conditions：双开关、变量阈值、独立开关、物品、角色；AND 关系 |
| 页图像 | 已实现 | set_image：图块／行走图、索引、朝向、图案；不校验资源文件存在 |
| 自主移动设置 | 已实现 | set_movement：类型、速度、频率；路线使用原生字典，只有结构校验 |
| 页选项 | 已实现 | set_options：行走／踏步动画、固定朝向、穿透 |
| 优先级与触发方式 | 已实现 | priority / trigger，包含自动和并行 |
| 页指令增删改查 | 已实现 | page.commands 接入 EventList，支持范围同上方指令表 |
| 新建／复制／粘贴页 | 已实现 | add_page / copy_page；副本独立 |
| 删除／重排／清空页 | 已实现 | delete_page / move_page / clear_page；至少一页，页序影响生效优先级 |
| 新建地图 | 未实现 | 仅现有地图 |
| 移动路线指令对象 | 已实现（205 指令） | Route / RouteStep；自主移动 set_movement 的 route 仍接收原生 moveRoute |

地图管理验证：新增 10 项行为测试，覆盖全局搜索、常量不误判、所有页属性、页复制排序清空、创建删除的 ID 稳定性、源快照冲突、插件字段保留、BOM/换行、正式脚本副本写入与字节级恢复。原工程只读，尚未进行编辑器 UI 与完整 Playtest。

地图 002 实测：修复新建地图 events=[] 的兼容性，新增一项回归测试；通过正式脚本创建两页 NPC 并核对独立开关条件和指令往返，未进行 Playtest。

插件帮助查询验证：配置参数、命令参数、选项、多行说明、空默认值、多语言回退、嵌套结构体、重复／缺失声明、同名歧义及越界路径；CLI 与 Python 接口结果一致，不执行 JavaScript。真实工程 Ve_1_Message 只读查询已核对。

VisuMZ_0_CoreEngine 查询验证：26 项配置声明、49 项命令声明（含 14 项 Separator 分隔项）、32 个结构体；修复 `@ ----` 分隔行污染默认值和描述的问题，新增回归测试。完整帮助原样返回，尚未验证运行时命令行为。

插件帮助改为纯文本：默认简短命令概要，按 command、section、struct 查询详情；仅概要截短长默认值，详情保留完整默认值和参数限制。新增文本返回及长值保留测试。

## 移动路线步骤

以下步骤均已编译／解码并测试，作为 SetMovementRoute.steps 使用，不放进 EventList。

| 路线代码 | 接口 | 支持范围 |
|---|---|---|
| 1–13 | Route.move | 四方向、四斜向、随机、接近／远离玩家、前进／后退 |
| 14 | Route.jump | 相对 x/y 格数，可为负数 |
| 15 | Route.wait | 正整数帧数 |
| 16–26 | Route.turn | 四方向、左右 90°、180°、随机左右 90°、随机、朝向／背向玩家 |
| 27–28 | Route.switch | 普通开关 ON/OFF |
| 29–30 | Route.speed / frequency | 速度 1–6、频率 1–5 |
| 31–40 | Route.option | walking、stepping、direction_fix、through、transparent 的 ON/OFF |
| 41–43 | Route.image / opacity / blend | 图像索引 0–7、不透明度 0–255、四种混合模式 |
| 44 | Route.se | 名称、音量、音调、声像 |
| 45 | Route.script | JavaScript 原文；不执行或验证脚本 |
| 0 | 自动生成 | 路线结束标记，不产生 505 |

Movement 验证：95 项基础回归加 1 项路线文件写回／恢复测试，共 96 项全部通过。覆盖 45 种路线代码、205/505 同步、嵌套缩进、解码后修改、非法组合、扩展结构保留；使用工程三份实际路线片段核对结构和紧凑 JSON 字节。文件测试覆盖 BOM、LF/CRLF、未修改字段保留和事务恢复。新建步骤采用实际工程的 indent:null，读取时保留是否存在该字段。尚未进行编辑器 UI 或游戏 Playtest，未修改实际工程。地图边界、碰撞、资源存在性及动态目标不作静态保证。

指令模块整理：实现统一按引擎分类放入 message、game_progression、flow_control、party、movement、timing、map_commands、advanced；OpaqueCommand 放入 opaque。TransferPlayer 已归入 movement，commands.py 仅兼容导出。event_api 的名称、参数、编译／解码行为与支持范围均不变；全部 96 项回归测试含工程副本集成测试通过。

目录整理：以上指令分类模块统一迁入 `event_core/commands/`，原 commands.py 替换为该包的 __init__.py；event_core.commands 导入及 event_api 公共接口保持兼容。地图管理、查询和编解码保留在包外。支持范围不变，96 项回归测试含工程副本集成测试通过。

Picture 验证：102 项回归测试全部通过（含工程副本集成测试）。新增 6 项覆盖五种指令参数、两个原点、四种混合模式及缓动、直接／变量坐标、嵌套解码修改、非法值与扩展保留；231/232/235 使用工程实际片段对照，233/234 依据工程 command233/234 源码核对。覆盖 BOM、LF/CRLF、未修改字段和事务恢复；未进行编辑器或游戏 Playtest。图片资源存在性、插件扩展编号与运行效果未校验。

Scene Control 验证：106 项测试全部通过，含工程副本集成测试；五条指令依据工程 command303/351–354 核对参数顺序，覆盖精确结构、嵌套往返、修改名字输入参数、非法参数和扩展保留。尚未进行编辑器或游戏 Playtest。

Audio & Video 验证：111 项回归测试全部通过，含工程副本集成测试。新增五项覆盖十条指令的精确结构、嵌套往返及修改、空名称、非法值和扩展保留；八类音频使用工程真实指令夹具，ME/视频依据引擎源码核对。资源存在性、格式可播放性及实际音视频播放尚未验证。

Screen 验证：116 项测试全部通过，含工程副本集成测试。新增五项覆盖六条指令精确参数、四种天气、零时长色调／天气、嵌套往返与修改、非法值和扩展保留。221–225 采用工程实际指令夹具，236 依据工程源码核对；未进行编辑器或游戏 Playtest。

物品使用示例验证：新增测试通过；全套回归及工程 165 夹具漂移情况见上方最近验证记录。新增 Label、JumpToLabel、ExitEvent，依据工程源码核对 118/119/115；覆盖嵌套往返、非法标签参数及扩展保留，验证示例条件分流、成功扣除顺序、失败提示调用和成功跳过失败区。未进行游戏 Playtest。

物品示例按工程公共事件 1204 重写：剔除 // 开头说明注释后，编译结果与参考数组完全一致；保留两条普通分段注释，验证 IF/ELSE、Use Fail 标签和特殊引导退出位置。标准回归 119 项：115 项通过，4 项可选集成测试跳过。本次未修改工程。

ShowChoices 初步验证：121 项标准测试，117 项通过，4 项集成测试跳过；覆盖选项结构、往返、分支递归编辑及非法值。1205 发条流程通过正式脚本写入并回读一致，未 Playtest。402/404 随选项生成和解码；403 独立取消分支仅保留。
