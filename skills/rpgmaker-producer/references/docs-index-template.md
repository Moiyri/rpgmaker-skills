# 项目文档总目录模板

`docs/README.md` 作为项目文档入口，包含基本信息表和文档目录。

基本信息填写游戏名称、RPG Maker 版本、目标平台、NW.js 版本、其内置 Node.js 版本和 Steam App ID。内容以工程实际配置或用户确认为准；尚待查明的值写「待确认」，按项目适用情况保留字段。内置 Node.js 版本从 NW.js 运行环境读取。

目录链接到已建立的主题目录 README。具体设计、运行流程和经常变化的内容放在对应主题文档，插件清单放在 `docs/development/plugins.md`。文档结构随用户确认的需求维护。

## 模板

```markdown
# 项目文档

## 基本信息

| 项目 | 内容 |
| --- | --- |
| 游戏名称 | 待确认 |
| RPG Maker 版本 | 待确认 |
| 目标平台 | 待确认 |
| NW.js 版本 | 待确认 |
| 内置 Node.js 版本 | 待确认 |
| Steam App ID | 待确认 |

## 文档目录

- [流程](workflows/README.md)
- [架构](architecture/README.md)
- [视觉](visuals/README.md)
- [策划](design/README.md)
- [UI](ui/README.md)
- [系统](systems/README.md)
- [开发规范](development/README.md)
```
