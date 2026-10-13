# RPG Maker 官方附带插件

用户明确：RPG Maker 官方附带的插件库整体属于备选范围。这里不是指 CGMZ、Visu 等第三方作者的全系列，也不是官方商店所有付费插件。整体纳入候选不等于全部安装、启用或已验证；按目标引擎版本、本地附带库和具体需求查询。

[官方插件说明](https://rpgmakerofficial.com/product/MZ_help-en/01_11_05.html)。尚未逐项盘点本地完整官方附带库，后续按实际需求补充准确名称、来源和用法。

## TextPicture：图片文字

- 准确 JS 名称：`TextPicture.js`，作者 Yoji Ojima，面向 MZ；本地未声明版本号。
- shadow 路径 `js/plugins/TextPicture.js`，注册名 `TextPicture`，已启用。
- [官方 TextPicture 源码讲解](https://rpgmakerofficial.com/product/mz/plugin/make/koushiki.html)。

将文字作为图片显示，可使用文字控制符。事件顺序：先调用插件命令 `set`（Set Text Picture），以 `text` 参数设置文字；再执行“显示图片”，图片文件名留空，设置图片 ID、位置等。之后可用图片事件指令移动或擦除。设置文字命令本身不会立即显示，也不是给任意已有图片加文字。

适合简单字幕、文字图片与图片演出；复杂排版需求先确认能力边界。本次核对本地声明与源码，未执行游戏测试。
