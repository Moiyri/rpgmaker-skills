# How to Integrate Steam

## 所需插件与运行库

- `Cyclone-Steam.js`：RM 侧接口；[作者仓库](https://github.com/Hudell/cyclone-engine)、[插件页](https://makerdevs.com/plugin/cyclone-steam)。本文调用依据 shadow 本地 1.00.01，插件页本次未能读取。
- [Greenworks 预编译包](https://github.com/greenheartgames/greenworks/releases)：包含 `greenworks.js` 和平台 `.node` 原生扩展。
- [Steamworks SDK](https://partner.steamgames.com/downloads/list)：提供配套 Steam 动态库，需要用户的开发者访问权限。
- Steam 客户端及有目标 App ID 许可的测试账号。

遇到登录、验证或手动下载，列出所需版本、系统、架构及文件名，请用户下载后提供路径，不绕过验证。注册插件使用 rpgmaker-plugins；事件脚本写入使用 rpgmaker-events。接入方案先确认具体平台、App ID 和功能范围，不因安装运行库自动上传或发布游戏。

## 1. 确认目标运行环境

在实际游戏 NW.js 的开发者控制台读取：

```js
({ nw: process.versions.nw, node: process.versions.node,
   abi: process.versions.modules, platform: process.platform, arch: process.arch })
```

以最终发布包的 NW.js 为准，编辑器测试环境可能不同。NW.js 内置 Node.js；电脑终端的 `node -v` 不能代替游戏环境。按 NW.js 版本、操作系统和架构选择 Greenworks，再根据该发布包说明选配 Steamworks SDK，不随意混用最新版。

使用匹配的预编译包通常无需另装 Node.js、npm 或编译工具。没有匹配包时再讨论更换 NW.js 或源码编译；更换运行环境后重测游戏。[NW.js 原生模块说明](https://docs.nwjs.io/For%20Users/Advanced/Use%20Native%20Node%20Modules/)随版本有不同构建流程，不照抄旧教程的工具链。

## 2. 安装文件（Windows x64 示例）

在含 `index.html` 的游戏目录保留 Greenworks 包的结构：

```text
game/
  index.html
  package.json
  greenworks.js
  steam_appid.txt
  lib/
    greenworks-win64.node
    steam_api64.dll
    sdkencryptedappticket64.dll
  js/plugins/
    Cyclone-Steam.js
```

`greenworks.js` 与 `.node` 来自同一预编译包；两个 DLL 来自配套 SDK：

- `redistributable_bin/win64/steam_api64.dll`
- `public/steam/lib/win64/sdkencryptedappticket64.dll`

按包说明保留其他必需文件；`.lib` 编译链接文件不能代替运行时 DLL。macOS/Linux 使用对应平台库与原生模块，文件名以下载包加载器为准，不直接套 Windows 示例。依据：[Greenworks 安装说明](https://github.com/greenheartgames/greenworks/blob/master/docs/quick-start-nwjs.md)。

## 3. 注册与本地初始化

将 Cyclone-Steam 注册并启用。当前插件用 `require('./greenworks')` 加载根目录入口并调用 `initAPI()`。必须在 NW.js 中运行，普通浏览器直接打开 index.html 不提供该环境。

开发用 `steam_appid.txt` 只写实际 App ID。放置位置必须能被启动时的工作目录找到；常规部署按 Steamworks 文档放在可执行文件旁。RM 部署可能有外层启动器与内层游戏目录，需核对实际工作目录，不固定塞进 data/。

启动并登录 Steam，使用具有目标游戏许可的账号，再启动游戏。控制台确认：

```js
CycloneSteam.initialized
CycloneSteam.screenName
```

初始化必须为 true。只有插件无报错、或显示 Play Test，不代表 Steam 接入成功。失败时依次检查版本/架构、动态库缺失、App ID、Steam 登录与账号许可、游戏和 Steam 的系统用户环境。[Steamworks 初始化文档](https://partner.steamgames.com/doc/sdk/api)。

## 4. 接入具体功能并验证发布包

按已确认需求使用[关键接口](../references/plugins/cyclone-steam.md)，成就/统计 ID 使用 Steamworks 后台配置的 API 名称，不用显示名称。测试账号、测试成就与具体写入范围须明确，初始化检查本身不需要解锁或清除成就。

将配套文件放入最终部署目录，确认运行时与预编译包匹配。上传 Steam 构建时移除开发用 `steam_appid.txt`，从 Steam 启动后检查实际 App ID、初始化和所需功能。成就、统计、Overlay、云存档分别验证；初始化成功不等于全部功能可用。

此插件的云接口只提供启用状态查询，不自动同步 RM 存档。需要云存档时单独确定 Auto-Cloud 或 API 方案，不能仅凭 cloudEnabled 宣称已接入。

## 记录范围

2026-10-12 核对官方 Greenworks、NW.js、Steamworks 文档和 shadow 的 Cyclone-Steam 源码；当前只整理安装流程，未安装、更换运行库，未运行 Steam 测试或上传构建。
