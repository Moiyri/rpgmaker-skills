# Cyclone Steam：Steamworks 接入

文件名 `Cyclone-Steam.js`，作者 Hudell，shadow 完整注册名 `Cyclone-Steam`，本地版本 1.00.01。[作者仓库](https://github.com/Hudell/cyclone-engine)、[插件页](https://makerdevs.com/plugin/cyclone-steam)。依赖 Greenworks 原生模块及配套 Steamworks 动态库，见[安装手记](../../production-notes/how-to-integrate-steam.md)。

## 关键调用

下列是 **JavaScript 接口**，放在事件页“脚本”指令中使用。本地版本没有声明可在插件指令菜单选择的专用命令；不要虚构插件指令。读取状态和执行操作前先确认 `CycloneSteam.initialized === true`，Steam 客户端运行状态不能替代初始化成功。

| 调用或属性 | 用途 |
| --- | --- |
| `CycloneSteam.initialized` | 初始化是否成功 |
| `CycloneSteam.running` | Steam 客户端是否运行 |
| `CycloneSteam.screenName` | 当前账号显示名 |
| `CycloneSteam.gameLanguage` / `uiLanguage` | 游戏语言 / Steam 界面语言 |
| `CycloneSteam.activateAchievement("ACH_ID")` | 解锁指定成就，异步结果通过内部回调记录 |
| `CycloneSteam.clearAchievement("ACH_ID")` | 清除指定成就，仅在明确的测试重置需求中使用 |
| `CycloneSteam.getStatInt("STAT_ID")` | 读取整数统计 |
| `CycloneSteam.getStatFloat("STAT_ID")` | 读取浮点统计 |
| `CycloneSteam.setStat("STAT_ID", value)` | 设置统计，类型与后台定义一致 |
| `CycloneSteam.storeStats()` | 提交统计，成功与失败异步记录 |
| `CycloneSteam.overlayEnabled` | Overlay 是否启用 |
| `CycloneSteam.activateGameOverlay("Achievements")` | 打开成就 Overlay |
| `CycloneSteam.activateGameOverlayToWebPage(url)` | 在 Overlay 打开网页 |
| `CycloneSteam.isDLCInstalled(dlcAppId)` | 检查 DLC 安装状态 |
| `CycloneSteam.isSubscribedApp(appId)` | 查询是否订阅/拥有指定 App 的许可 |
| `CycloneSteam.cloudEnabled` / `userCloudEnabled` | 查询应用 / 用户云功能启用状态，不执行存档上传 |

还提供 `achievementCount`、`dlcCount`、`friendCount`，以及会改变 DLC 安装状态的 `installDLC(appId)`、`uninstallDLC(appId)`；只在用户明确要求的功能中使用。

### 解锁成就

```js
if (typeof CycloneSteam !== "undefined" && CycloneSteam.initialized) {
    CycloneSteam.activateAchievement("ACH_ID");
}
```

将 ACH_ID 替换为 Steamworks 后台成就 API 名称。调用返回不等于解锁完成，测试时核对成功回调日志及 Steam 状态。插件缺少 Greenworks 时可能只打印模拟日志，不能将其当作实际解锁。

### 写入并提交统计

```js
if (typeof CycloneSteam !== "undefined" && CycloneSteam.initialized) {
    CycloneSteam.setStat("STAT_ID", 10);
    CycloneSteam.storeStats();
}
```

数值与触发时机按游戏需求决定，不自动在每帧提交。

### 不要把 getAchievement 当成同步布尔查询

本地 1.00.01 的 `CycloneSteam.getAchievement(id)` 将查询交给 Greenworks，但成功回调仍是 TODO，未将结果暴露出来。不要写 `if (CycloneSteam.getAchievement(id))` 判断已解锁。确需查询时先扩展正式接口，或核对已安装 Greenworks 的回调 API 后使用；不假设这里已有 Promise/布尔返回。

依据：2026-10-12 读取本地源码并核对依赖文档，未执行 Steam 调用。其他版本使用前重新核对接口。
