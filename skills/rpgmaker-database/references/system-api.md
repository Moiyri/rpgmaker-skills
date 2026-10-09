# System（系统）

统一入口 `db.system`，覆盖编辑器 System 1 和 System 2。Types 保持 `db.types`。

```python
s = db.system
print(s.describe())
s.game_title = 'The Shadow'
s.currency_unit = '金币'
s.starting_party.set([1])
s.title.image1 = 'Layer1'
s.title.image2 = ''
s.title.draw_game_title = False
s.title.command_window.background = 'window'  # window / dim / transparent
s.title.command_window.offset_x = 0
s.title.command_window.offset_y = 0
s.set_window_tone(0, 0, 0, 0)
s.side_view = False
s.battle_system = 'turn_based'  # turn_based / tpb_active / tpb_wait
s.player_start.set(map_id=1, x=1, y=0)
s.boat.character_name = 'Vehicle'
s.boat.character_index = 0
s.boat.position.clear()
print(s.options.list())
s.options.set('autosave', True)
print(s.music.list())
s.music.get('title').name = 'Theme'
s.music.get('title').volume = 80
print(s.sounds.list())
s.sounds.get('cursor').pitch = 100
preview = db.preview()
print(preview)
db.commit(preview)
```

- `starting_party`：get/list/set/add/remove/clear。使用角色 ID，顺序即初始队伍顺序；提交检查角色存在，不允许重复。
- `title.clear_images()` 清空两层标题图；`title.command_window` 修改偏移与背景。
- `boat / ship / airship`：图像 name/index 设置、`clear_image()`、`position.get/set/clear`、`music`。`player_start` 不允许 clear。地图位置提交时检查地图存在与边界。
- `options.get/set/list`：布尔值开关；list 列出名称及状态。工程缺少的选项报错，不自动添加版本专属字段。
- `music.get/list/clear`：title、battle、victory、defeat、game_over、boat、ship、airship。
- `sounds.get/list/clear`：按用途名称操作，list 列出全部 24 种。包括 cursor、ok、cancel、save、load 等。
- 音频对象：name、volume 0–100、pitch 50–150、pan -100–100。clear 仅清空名称，保留音量等参数和扩展字段。
- 图像和音频文件名不含扩展名。当前不验证素材存在性，不保证插件覆盖后的显示／播放行为。

窗口色调 RGB 为 -255–255，灰度 0–255。`window_tone`、`get()` 返回副本，修改使用属性或 set 方法。清空不删除必需 JSON 字段；没有通用 remove 字段接口。新建角色并加入队伍、修改 Types 与 System 可以一次提交。初始队伍与出生点主要用于新游戏，不改已有存档。

## System 2 对应设置

仍通过 `db.system` 访问：

```python
s.menu_commands.set('skill', False)
s.item_categories.set('weapon', False)
print(s.menu_commands.list())
print(db.types.skill_types.list())
s.magic_skills.add(1)  # 使用实际技能类型编号，不是技能编号
print(s.attack_motions.list())
s.attack_motions.set(1, motion='swing', weapon_image_id=1)
s.tile_size = 48
s.icon_size = 32
s.face_size = 144
s.editor.message_width_normal = 60
s.editor.message_width_with_face = 47
s.editor.json_format_level = 1
s.advanced.screen_width = 1920
s.advanced.screen_height = 1080
s.advanced.ui_area_width = 1920
s.advanced.ui_area_height = 1080
s.advanced.screen_scale = 1
s.advanced.main_font_filename = 'main.ttf'
```

- menu_commands：get/set/list，名称 item、skill、equip、status、formation、save。
- item_categories：get/set/list，名称 item、weapon、armor、key_item。
- magic_skills：get/list/set/add/remove/clear，编号查 `db.types.skill_types`。
- attack_motions：get/list/set/clear。武器类型 ID 查 `db.types.weapon_types`，0 为徒手；motion 为 thrust/swing/missile。weapon_image_id 0 为无图，1–30 对应引擎 Weapons 图集编号，不是武器数据库 ID。clear 重置为 thrust、无图片。新增武器类型可用 set 补齐其动作行。
- tile_size：48/32/24/16；icon_size：32/24/16/12/8；face_size：144/96/48/40/32。变更尺寸须配套素材，本接口不重采样图片。
- editor：message_width_normal、message_width_with_face、json_format_level；通过 describe/get 查询。
- advanced：game_id、screen_width、screen_height、ui_area_width、ui_area_height、screen_scale、main_font_filename、number_font_filename、fallback_fonts、font_size、window_opacity、pictures_upper_limit；通过 describe/get 查询。

screen_scale 为正数，window_opacity 0–255，其余尺寸及数量为正整数。字体文件名包含扩展名。修改 game_id 可能影响存档识别；分辨率与 UI 尺寸需结合插件及游戏实际测试。未知字段保留；缺失版本专属设置不提供默认值，读取会报错。JSON 格式设置不触发本工具重排文件。
