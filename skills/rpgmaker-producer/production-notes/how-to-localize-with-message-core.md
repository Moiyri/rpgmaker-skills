# How to Localize with Message Core

## 使用插件

- `VisuMZ_1_MessageCore.js`：[Message Core 官网](http://www.yanfly.moe/wiki/Message_Core_VisuStella_MZ)。声明依赖 `VisuMZ_0_CoreEngine.js`，核心在前。
- 本地原版依据：用户提供的 `/Users/moiyri/Game/RPGMaker/插件Demo/VisuMZ_Sample_Game_Project 2`。通过插件技能的 `manual`、`help --struct Localization` 读取帮助，不以 shadow 的修改版说明原版行为。

## 制作偏好

本地化优先使用 Message Core 的 Text Language 功能，文本表格优先 TSV。shadow 的本地化已由用户改成多文件方案；这是项目定制，不是原插件的使用前提。此偏好不意味着将现有工程自动迁移回原版。

## 本地化键

统一遵循[命名规则](../references/naming-rules.md)中的本地化键规范。

在原版 Message Core 的 TSV 中，点号是完整键名的一部分，不表示嵌套对象。例如在 `Key` 列填写 `item.001.name`，文本中通过 `\tl{item.001.name}` 引用。原版键名不区分大小写，避免仅靠大小写区分条目。

## 原版配置入口

先读 `.manual()` 的 Text Language Information，再查询 `.help("Localization")` 和当前参数。参数位于 `Localization:struct`：

| 字段 | 用途 |
| --- | --- |
| `Enable:eval` | 启用语言切换 |
| `LangFiletype:str` | 选用 `tsv`；帮助将 TSV 标为 Recommended |
| `TsvFilename:str` | 指定 `data/` 下的 TSV 文件 |
| `DefaultLocale:str` | 默认语言 |
| `Languages:arraystr` | 支持的语言 |
| `AddOption:eval` | 是否将语言切换加入选项菜单 |

原版帮助以 `data/Language.tsv` 为例：启用并保存配置后，在 Playtest 中按提示生成语言表并重启。实际文件名以参数为准。表格使用 `Key` 和各语言列；语言列与默认语言结合实际表格与用户确认；文本键遵循[命名规则](../references/naming-rules.md)，不直接套用项目自定义 JSON 的字段。

TSV 使用制表符分隔；导入表格软件时关闭文本自动转数字、日期和公式，保留文本键及前导零。该功能负责读取译文与切换语言，不会自动翻译。实际修改插件参数仍须通过 rpgmaker-plugins 的正式脚本完成。

来源与验证：用户于 2026-10-12 确认插件与 TSV 偏好，并指定原版 Demo 为依据。以上配置已核对本地原版帮助；未修改工程，未执行 Playtest。具体翻译协作和文件组织流程尚未约定。
