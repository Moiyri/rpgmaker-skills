# 地图目录与属性

```python
print(db.maps.list())
for m in db.maps.find('城镇'):
    print(m.id, m.name)
m = db.maps.get(1)
print(m.describe())
m.name = '入口'                # 编辑器 Name
m.display_name = '旧镇'        # Display Name
m.parent_id = 0                # 根目录；其他值为父地图 ID
m.tileset_id = 1
m.scroll_type = 'none'         # none / vertical / horizontal / both
m.autoplay_bgm = True
m.bgm.name = 'Theme'
m.bgm.volume = 80
m.parallax_name = 'Sky'
preview = db.preview()
print(preview)
db.commit(preview)
```

`list(search='', offset=0, limit=50)` 返回 ID、名称、尺寸、父级、图块集。find 按编辑器名称子串搜索，返回地图对象。缺失地图文件报错，不把损坏条目当成空地图。

| 属性 | 地图窗口设置 |
|---|---|
| name / display_name | 名称／显示名称 |
| tileset_id / scroll_type | 图块集／滚动类型 |
| width / height | 宽高读取；用 resize 调整 |
| encounter_step | 遇敌步数 |
| autoplay_bgm / autoplay_bgs | 自动播放 BGM/BGS |
| bgm / bgs | name、volume、pitch、pan；clear 清空音频名 |
| specify_battleback | 指定战斗背景 |
| battleback1_name / battleback2_name | 两层战斗背景 |
| disable_dashing | 禁止奔跑 |
| parallax_name | 远景图片 |
| parallax_loop_x / parallax_loop_y | 水平／垂直循环 |
| parallax_sx / parallax_sy | 滚动速度 -32–32 |
| parallax_show | 在编辑器中显示远景 |
| note | 备注，保留已有插件标签 |

parent_id 用于地图树层级，禁止自身或循环父级；不会调整编辑器排序号。改图块集会影响现有地图外观及通行，应自行核对，不重绘图块。修改属性保留全部图块、事件、遇敌列表和未知字段。

图块绘制及遇敌列表编辑暂未提供。地图事件由事件技能负责；不同技能修改同一地图时先提交，再重新读取，避免旧快照覆盖。格式、备份和冲突检查沿用数据库后端；未自动验证素材或实际游戏表现。

## 创建、删除、调整大小和地图树

```python
print(db.maps.tree())
m = db.maps.create('测试地图', width=17, height=13, tileset_id=1, parent_id=0)
print(m.id)
m.resize(20, 15)
preview = db.preview()
print(preview)
db.commit(preview)
# 删除已有地图：db.maps.delete(id)，同样预览提交。
```

create 从 1 起选择最小可用编号，或使用显式 id；MapInfos 槽位必须为空且 MapNNN.json 路径不存在（包括符号链接和目录占用）。ID 1–999，尺寸 1–256。提交再次校验，创建使用原子禁止覆盖方式发布；冲突停止，不临时换编号。目录显示顺序追加，编号空缺不会压缩。新地图使用实测 Map003 默认结构：六层全零、events=[]，UTF-8 无 BOM、LF，无末尾换行。

resize 左上角锚定，六层逐行复制重叠区域，右侧／底部补零或裁剪；不绘制图块。越界事件立即报错。缩小时预览检查玩家／载具出生点及原生固定坐标传送、载具定位。

delete 清空 MapInfos 槽位并删除对应文件；有子地图、原生静态引用则拒绝。脚本、插件和变量指定的动态地图引用不能完整检查，需调用方确认。新创建未提交的地图不支持同会话删除。

创建／删除通过正式 database.py 的 create_file/delete_file 操作执行，仅允许 MapNNN.json。事务覆盖目录与文件，失败尝试回滚；备份恢复支持撤销创建或恢复删除。恢复创建时若地图已被修改，拒绝删除；恢复删除时若路径已占用，拒绝覆盖。多文件替换不是操作系统级原子事务，若 recovery_required 按事务日志恢复。
