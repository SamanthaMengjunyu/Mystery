"""User-selected local audio library; only opaque, indexed audio IDs are served."""
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import stat
import threading

AUDIO_TYPES={'.mp3':'audio/mpeg','.wav':'audio/wav','.flac':'audio/flac','.ogg':'audio/ogg','.oga':'audio/ogg','.opus':'audio/ogg','.m4a':'audio/mp4','.aac':'audio/aac','.wma':'audio/x-ms-wma','.aif':'audio/aiff','.aiff':'audio/aiff','.mp4':'audio/mp4','.webm':'audio/webm'}


def byte_range(value,size):
    if not value:return (0,size-1,False)
    try:
        if not value.startswith('bytes=') or ',' in value:raise ValueError
        first,last=value[6:].split('-',1)
        if not first:
            length=int(last)
            if length<=0:raise ValueError
            start,end=max(0,size-length),size-1
        else:
            start=int(first);end=min(int(last) if last else size-1,size-1)
        if start<0 or start>=size or end<start:raise ValueError
        return start,end,True
    except (ValueError,TypeError):raise ValueError('音频范围无效') from None


class MusicLibrary:
    def __init__(self,data_dir):
        self.path=Path(data_dir)/'music.json';self.lock=threading.RLock();self.folder_picker=None;self.files={};self.secret=secrets.token_bytes(16)
        try:self.options=json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError,ValueError):self.options={}
        if not isinstance(self.options,dict):self.options={}
        self.options={k:v for k,v in self.options.items() if k in ('folder','recursive','volume','mode')}
        self.options.setdefault('volume',.45);self.options.setdefault('mode','list');self.options.setdefault('recursive',True)

    @staticmethod
    def audio_paths(root,recursive):
        if not recursive:
            yield from root.iterdir();return
        for current,directories,files in os.walk(root,followlinks=False):
            directories[:]=[name for name in directories if not (Path(current)/name).is_symlink() and not (getattr((Path(current)/name).lstat(), 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)) and (Path(current)/name).resolve().is_relative_to(root)]
            for name in files:yield Path(current)/name

    def save(self,p):
        with self.lock:
            options=dict(self.options)
            if 'volume' in p:
                volume=float(p['volume'])
                if not math.isfinite(volume) or not 0<=volume<=1:raise ValueError('音量须在 0～100% 之间')
                options['volume']=volume
            if 'mode' in p:
                if p['mode'] not in ('list','single','shuffle'):raise ValueError('播放模式无效')
                options['mode']=p['mode']
            if 'recursive' in p:
                if not isinstance(p['recursive'],bool):raise ValueError('子文件夹选项无效')
                options['recursive']=p['recursive']
            self.options=options;self._persist()
            return {k:v for k,v in self.options.items() if k!='folder'}

    def _persist(self):
        temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(self.options,ensure_ascii=False),encoding='utf-8');temp.replace(self.path)

    def choose(self):
        if not self.folder_picker:return {'native':False}
        folder=self.folder_picker()
        if not folder:return {'native':True,'cancelled':True}
        root=Path(folder).resolve()
        if not root.is_dir():raise ValueError('所选音乐文件夹不存在')
        with self.lock:self.options['folder']=str(root);self._persist()
        return {'native':True,**self.library()}

    def library(self):
        with self.lock:
            self.files={};tracks=[];root=Path(self.options['folder']) if self.options.get('folder') else None;message=''
            if root and root.is_dir():
                root=root.resolve();iterator=self.audio_paths(root,self.options['recursive'])
                try:
                    for visited,path in enumerate(iterator):
                        if visited>=100000:message='所选范围较大，已读取部分音频，可选择更具体的文件夹。';break
                        if path.suffix.lower() not in AUDIO_TYPES or not path.is_file():continue
                        resolved=path.resolve()
                        if not resolved.is_relative_to(root):continue
                        identity=hashlib.sha256(self.secret+str(resolved).encode()).hexdigest()[:32];self.files[identity]=resolved
                        tracks.append({'id':identity,'name':path.stem,'relative':str(path.relative_to(root)),'mime':AUDIO_TYPES[path.suffix.lower()]})
                        if len(tracks)>=5000:message='已读取前 5000 首音频，可选择更具体的文件夹。';break
                except OSError:message='部分子文件夹无法读取，其余可用音频已列出。'
            elif root:message='之前的音乐文件夹不可用，请重新选择。'
            tracks.sort(key=lambda t:t['relative'].casefold())
            return {'folder':str(root) if root else '', 'tracks':tracks,'message':message,'native_dialogs':bool(self.folder_picker),'settings':{k:v for k,v in self.options.items() if k!='folder'}}

    def resolve(self,identity):
        with self.lock:
            path=self.files.get(identity)
            root=Path(self.options.get('folder','')).resolve()
            if path is None or not path.resolve().is_relative_to(root) or path.suffix.lower() not in AUDIO_TYPES or not path.is_file():raise FileNotFoundError('此音频已移动或不在所选文件夹中')
            return path,AUDIO_TYPES[path.suffix.lower()]
