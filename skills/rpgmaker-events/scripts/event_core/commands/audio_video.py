"""Audio & Video（音频与视频）指令。"""
from dataclasses import dataclass
from typing import ClassVar
from ..base import Command
from .. import compiler as core


@dataclass(eq=False)
class _PlayAudio(Command):
    name: str
    volume: int = 90
    pitch: int = 100
    pan: int = 0
    kind: ClassVar[str]

    def to_spec(self):
        return {'type':self.kind,'name':self.name,'volume':self.volume,'pitch':self.pitch,'pan':self.pan}


class PlayBGM(_PlayAudio):
    """Play BGM（播放背景音乐），name 为 audio/bgm 下不含扩展名的文件名。

    volume 0–100、pitch 50–150、pan -100–100；默认 90/100/0。
    循环播放，不等待；name="" 停止当前 BGM。
    """
    kind = 'play_bgm'


class PlayBGS(_PlayAudio):
    """Play BGS（播放背景音），name 为 audio/bgs 下不含扩展名的文件名。

    volume 0–100、pitch 50–150、pan -100–100；默认 90/100/0。
    循环播放，不等待；name="" 停止当前 BGS。
    """
    kind = 'play_bgs'


class PlayME(_PlayAudio):
    """Play ME（播放音乐效果），name 为 audio/me 下不含扩展名的文件名。

    volume 0–100、pitch 50–150、pan -100–100；默认 90/100/0。
    播放一次，不等待；引擎暂停 BGM，ME 结束后恢复。空名称停止 ME。
    """
    kind = 'play_me'


class PlaySE(_PlayAudio):
    """Play SE（播放音效），name 为 audio/se 下不含扩展名的文件名。

    volume 0–100、pitch 50–150、pan -100–100；默认 90/100/0。
    播放一次，可叠加，不等待；空名称不播放。
    """
    kind = 'play_se'


@dataclass(eq=False)
class _FadeAudio(Command):
    seconds: int = 10
    kind: ClassVar[str]

    def to_spec(self):
        return {'type':self.kind,'seconds':self.seconds}


class FadeoutBGM(_FadeAudio):
    """Fadeout BGM（淡出背景音乐），seconds 为非负整数秒，不是帧；不等待淡出完成。"""
    kind = 'fadeout_bgm'


class FadeoutBGS(_FadeAudio):
    """Fadeout BGS（淡出背景音），seconds 为非负整数秒，不是帧；不等待淡出完成。"""
    kind = 'fadeout_bgs'


class SaveBGM(Command):
    """Save BGM（保存背景音乐），记住当前 BGM 和播放位置，供 ReplayBGM 使用；不是游戏存档。"""
    def to_spec(self):
        return {'type':'save_bgm'}


class ReplayBGM(Command):
    """Replay BGM（重播背景音乐），恢复 SaveBGM 保存的音乐及播放位置；没有记录时不生效。"""
    def to_spec(self):
        return {'type':'replay_bgm'}


class StopSE(Command):
    """Stop SE（停止音效），停止所有当前 SE，不影响 BGM/BGS/ME。"""
    def to_spec(self):
        return {'type':'stop_se'}


@dataclass(eq=False)
class PlayMovie(Command):
    """Play Movie（播放影片），name 为 movies 下不含扩展名的文件名，可含子目录。

    引擎选择 webm 或 mp4，并等待播放结束；空名称不播放。资源需适配运行平台。
    """
    name: str

    def to_spec(self):
        return {'type':'play_movie','name':self.name}


AUDIO = {'play_bgm':(241,PlayBGM),'play_bgs':(245,PlayBGS),'play_me':(249,PlayME),'play_se':(250,PlaySE)}
FADES = {'fadeout_bgm':(242,FadeoutBGM),'fadeout_bgs':(246,FadeoutBGS)}
SIMPLE = {'save_bgm':(243,SaveBGM),'replay_bgm':(244,ReplayBGM),'stop_se':(251,StopSE)}


def compile_audio_video(node, indent):
    kind=node['type']
    if kind in AUDIO:
        core.fields(node,{'type','name','volume','pitch','pan'})
        audio={'name':core.string(node['name']),'volume':core.integer(node['volume'],0,100),
               'pitch':core.integer(node['pitch'],50,150),'pan':core.integer(node['pan'],-100,100)}
        return [core.command(AUDIO[kind][0],indent,[audio])]
    if kind in FADES:
        core.fields(node,{'type','seconds'})
        return [core.command(FADES[kind][0],indent,[core.integer(node['seconds'])])]
    if kind in SIMPLE:
        core.fields(node,{'type'})
        return [core.command(SIMPLE[kind][0],indent)]
    core.require(kind=='play_movie','Unknown audio/video command')
    core.fields(node,{'type','name'})
    return [core.command(261,indent,[core.string(node['name'])])]


def decode_audio_video(code,p):
    for value,cls in AUDIO.values():
        if value==code:
            core.require(len(p)==1 and isinstance(p[0],dict),'Expected audio settings')
            core.fields(p[0],{'name','volume','pitch','pan'})
            return cls(**p[0])
    for value,cls in FADES.values():
        if value==code:
            core.require(len(p)==1,'Expected seconds')
            return cls(p[0])
    for value,cls in SIMPLE.values():
        if value==code:
            core.require(p==[],'Unexpected audio parameters')
            return cls()
    core.require(code==261 and len(p)==1,'Expected movie name')
    return PlayMovie(p[0])
