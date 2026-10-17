"""Loopback-only desktop host. All assets are bundled and available offline."""
import argparse
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import secrets
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit

from desktop.backend import Backend
from desktop import VERSION
from desktop.music import byte_range
from desktop.runtime import default_data_dir, webview_gui


def create_server(data_dir):
    backend = Backend(Path(data_dir))
    token = secrets.token_urlsafe(32)
    assets = Path(__file__).resolve().parent / "web"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def reply(self, status, body, kind="application/json; charset=utf-8", cookie=False):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob: https: http:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
            if cookie:
                self.send_header("Set-Cookie", f"mystery_{self.server.server_port}={token}; HttpOnly; SameSite=Strict; Path=/")
            self.end_headers()
            if self.command!='HEAD':self.wfile.write(body)

        def audio(self,identity,head=False):
            try:
                path,kind=backend.music.resolve(identity)
                with path.open('rb') as stream:
                    size=os.fstat(stream.fileno()).st_size
                    try:start,end,partial=byte_range(self.headers.get('Range'),size)
                    except ValueError:
                        self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return
                    self.send_response(206 if partial else 200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(max(0,end-start+1)));self.send_header('Accept-Ranges','bytes');self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cross-Origin-Resource-Policy','same-origin')
                    if partial:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                    self.end_headers()
                    if head:return
                    stream.seek(start);remaining=end-start+1
                    while remaining>0:
                        chunk=stream.read(min(1024*1024,remaining))
                        if not chunk:break
                        self.wfile.write(chunk);remaining-=len(chunk)
            except (FileNotFoundError,PermissionError):self.reply(404,{'error':'音频文件不可用'})
            except (BrokenPipeError,ConnectionResetError):pass

        def do_HEAD(self):
            if not self.valid_host() or not self.authorized():return self.reply(403,{'error':'会话校验失败'})
            parsed=urlsplit(self.path)
            if parsed.path.startswith('/media/'):return self.audio(parsed.path[7:],True)
            self.send_response(404);self.send_header('Content-Length','0');self.end_headers()

        def authorized(self):
            cookie = SimpleCookie()
            try: cookie.load(self.headers.get("Cookie", ""))
            except Exception: return False
            value = cookie.get(f"mystery_{self.server.server_port}")
            return bool(value and secrets.compare_digest(value.value, token))

        def valid_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, {"error": "无效主机"})
            parsed = urlsplit(self.path)
            entry = parse_qs(parsed.query).get("session", [""])[0]
            initial = parsed.path == "/" and secrets.compare_digest(entry, token)
            if not (initial or self.authorized()):
                return self.reply(403, {"error": "请从桌面应用进入"})
            if parsed.path.startswith('/media/'):return self.audio(parsed.path[7:])
            path = (assets / (parsed.path.lstrip("/") or "index.html")).resolve()
            if not path.is_relative_to(assets.resolve()) or not path.is_file():
                return self.reply(404, {"error": "文件不存在"})
            body = path.read_bytes()
            if path.name == "index.html": body = body.replace(b"__MYSTERY_TOKEN__", token.encode())
            kind = {".js": "text/javascript", ".css": "text/css", ".html": "text/html; charset=utf-8"}.get(path.suffix, mimetypes.guess_type(str(path))[0] or "application/octet-stream")
            self.reply(200, body, kind, cookie=initial)

        def do_POST(self):
            if not self.valid_host() or not self.authorized() or not secrets.compare_digest(self.headers.get("X-Mystery-Token", ""), token):
                return self.reply(403, {"error": "会话校验失败"})
            origin = self.headers.get("Origin")
            if origin and origin != f"http://127.0.0.1:{self.server.server_port}":
                return self.reply(403, {"error": "跨来源请求被拒绝"})
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 4_000_000: raise ValueError("请求大小超出限制")
                p = json.loads(self.rfile.read(length))
                if not isinstance(p, dict): raise ValueError("请求格式错误")
                result = backend.dispatch(self.path.removeprefix("/api/"), p)
                self.reply(200, {"ok": True, "data": result})
            except Exception as error:
                self.reply(400, {"ok": False, "error": str(error)[:1200]})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    url = f"http://127.0.0.1:{server.server_port}/?session={token}"
    return server, backend, url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", help="仅供开发预览")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--ready-file", type=Path)
    parser.add_argument("--self-test", type=Path, help="离线打包自检，写入 JSON 后退出")
    parser.add_argument("--ui-test", type=Path, help="验证内嵌 WebView 与 WebGL 初始化后退出")
    args = parser.parse_args()
    data = args.data_dir or default_data_dir()
    data = data.resolve()
    server, backend, url = create_server(data)
    backend.ui_testing=bool(args.ui_test)
    if args.self_test:
        report = {}
        for module in ("bazi", "ziwei", "astro", "jyotish", "liuyao", "meihua", "tarot", "lenormand", "answers", "solar"):
            try:
                p = {"module": module, "datetime": "2000-08-16T04:00", "first": 34, "second": 43, "third": 1}
                if module in ("tarot", "lenormand"):
                    p.update(backend.shuffle(p))
                record = backend.calculate(p)
                report[module] = {"ok": True, "id": record["id"]}
            except Exception as error:
                report[module] = {"ok": False, "error": str(error)}
        try:
            person = backend.save_birthday({"name": "打包自检", "datetime": "2000-08-16T04:00"})
            assert Backend(data).birthday(person["id"]) == person
            person = backend.save_birthday({**person, "name": "打包自检修改"})
            assert Backend(data).birthdays("自检修改") == [person]
            backend.delete_birthday(person["id"])
            assert not Backend(data).birthdays("自检修改")
            report["birthday_book"] = {"ok": True, "create_update_search_delete_persist": True}
        except Exception as error:
            report["birthday_book"] = {"ok": False, "error": str(error)}
        try:
            for module, total in (("liuyao", 6), ("meihua", 3), ("answers", 1)):
                info = backend.start_ritual({"module": module, "datetime": "2000-08-16T04:00", "first": 34, "second": 43})
                for step in range(1, total + 1):
                    partial = backend.ritual_step({**info, "step": step})
                    if module == "liuyao": assert len(partial["tosses"]) == step
                record = backend.finish_ritual(info)
                assert backend.replay(record["id"])["verified"]
            report["rituals"] = {"ok": True, "staged_results_and_replay": True}
        except Exception as error:
            report["rituals"] = {"ok": False, "error": str(error)}
        try:
            from desktop.places import search, resolve, nearby
            assert search('New York')[0]['tz_name'] == 'America/New_York'
            assert resolve(139.69, 35.69)['tz_name'] == 'Asia/Tokyo'
            assert nearby(-74.006,40.7143)[0]['tz_name'] == 'America/New_York'
            report['geography'] = {'ok': True, 'offline_search_and_geographic_timezone': True, 'named_map_candidates': True}
        except Exception as error:
            report['geography'] = {'ok': False, 'error': str(error)}
        try:
            from tempfile import TemporaryDirectory
            from desktop.music import MusicLibrary
            import wave
            with TemporaryDirectory() as folder:
                library=MusicLibrary(folder);songs=Path(folder)/'songs';songs.mkdir()
                with wave.open(str(songs/'silence.wav'),'wb') as audio:
                    audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(8000);audio.writeframes(bytes(1600))
                library.folder_picker=lambda:songs
                track=library.choose()['tracks'][0]
                assert library.resolve(track['id'])[0].is_file()
                assert byte_range('bytes=10-19',100)==(10,19,True)
            person=backend.save_birthday({'name':'环境功能打包自检','datetime':'2000-06-21T04:00','tz_name':'Asia/Shanghai','current_place':'Tokyo','current_longitude':139.69,'current_latitude':35.69})
            person=backend.save_birthday_note({'id':person['id'],'notes':'本机备注自检'})
            assert person['notes']=='本机备注自检'
            reminders=backend.dispatch('birthday-reminders',{'viewer_zone':'Asia/Shanghai','now':'2026-06-20T15:30:00Z'})
            assert next(p for p in reminders['items'] if p['id']==person['id'])['days']==0
            backend.delete_birthday(person['id'])
            report['ambient']={'ok':True,'local_audio_library_and_ranges':True,'notes_and_residence_reminders':True}
        except Exception as error:
            report['ambient']={'ok':False,'error':str(error)}
        args.self_test.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        server.server_close()
        return
    if args.ready_file:
        args.ready_file.write_text(json.dumps({"url": url, "pid": os.getpid()}), encoding="utf-8")
    if args.serve:
        print(url, flush=True)
        server.serve_forever()
        return
    threading.Thread(target=server.serve_forever, daemon=True).start()
    import webview
    webview.settings["ALLOW_DOWNLOADS"] = True
    window = webview.create_window(f"Mystery {VERSION} · 星云之间", url, width=1440, height=940,
                                  min_size=(1000, 700), background_color="#080b13")
    def choose_music_folder():
        # HTTP handlers run on fresh worker threads; the Windows shell picker
        # requires a COM single-threaded apartment on the calling thread.
        ole=None
        if os.name=='nt':
            import ctypes
            ole=ctypes.OleDLL('ole32')
            ole.OleInitialize.argtypes=[ctypes.c_void_p]
            ole.OleUninitialize.restype=None
            ole.OleInitialize(None)
        try:
            selected=window.create_file_dialog(webview.FileDialog.FOLDER,directory=backend.music.options.get('folder',''))
            return selected[0] if selected else None
        finally:
            if ole:ole.OleUninitialize()
    backend.music.folder_picker=choose_music_folder
    window.events.closed += lambda: server.shutdown()
    if args.ui_test:
        import logging
        logging.getLogger("pywebview").addHandler(logging.FileHandler(data / "webview-test.log", encoding="utf-8"))
        def verify_ui():
            report = {"ok": False, "error": "WebView 初始化超时"}
            try:
                for _ in range(75):
                    time.sleep(.4)
                    status = window.evaluate_js("({version:document.body.dataset.appVersion,title:document.title,ready:document.body.dataset.sceneReady||'',art:document.body.dataset.nebulaArt||'',fallback:!!document.querySelector('.scene-fallback'),width:innerWidth,height:innerHeight,nodes:document.querySelectorAll('.scene-node').length,canvas:!!document.querySelector('#universe'),onboarding:!!document.querySelector('#scroll-invitation'),returnShortcut:!!document.querySelector('#return-nebula'),transitionCanvas:!!document.querySelector('#transition-surface'),starTrails:Number(document.body.dataset.starTrails||0),starTrailsMotion:document.body.dataset.starTrailsMotion||'',planetNodes:Number(document.body.dataset.planetNodes||0),boundOrbits:Number(document.body.dataset.boundOrbits||0),nodeAppearance:document.body.dataset.nodeAppearance||'',birthdayBook:!!document.querySelector('#birthday-book-button'),birthdayNav:!!document.querySelector('[data-nav=birthdays]'),birthPrompt:!!document.querySelector('#birth-editor'),centralStar:document.body.dataset.centralStar||'',centralStarMotion:document.body.dataset.centralStarMotion||'',centralStarAppearance:document.body.dataset.centralStarAppearance||'',quality:document.body.dataset.sceneQuality||'',dustParticles:Number(document.body.dataset.dustParticles||0),controlsTheme:document.body.dataset.controlsTheme||'',musicPlayer:!!document.querySelector('#background-audio'),focusReady:!!document.querySelector('#focus-root'),remindersReady:!!document.querySelector('.reminder-panel'),customControls:document.querySelectorAll('.select-trigger').length,reduced:document.body.classList.contains('reduced'),scrollAnimation:getComputedStyle(document.querySelector('.scroll-chevron')).animationName})")
                    if status.get("ready") and (status.get("art") or status.get("fallback")) and status.get("customControls", 0) >= 1:
                        report = {"ok": status.get("version") == VERSION and status["ready"] == "true" and not status["fallback"] and status["nodes"] == 12 and status["art"] == "loaded" and status["onboarding"] and status["returnShortcut"] and status["transitionCanvas"] and status["starTrails"] == 12 and status["planetNodes"] == 12 and status["boundOrbits"] == 12 and status["nodeAppearance"] == "white-hollow" and status["birthdayBook"] and status["birthdayNav"] and status["centralStar"] == "birthday-book" and status["centralStarAppearance"] == "volume-glow" and status["centralStarMotion"] == "flowing" and status["quality"] == "high" and status["dustParticles"] == 19000 and status["controlsTheme"] == "nebula" and status["customControls"] >= 1 and status["musicPlayer"] and status["focusReady"] and status["remindersReady"] and not status["reduced"], **status}
                        break
            except Exception as error:
                report = {"ok": False, "error": str(error)}
            finally:
                args.ui_test.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                window.destroy()
    webview.start(verify_ui if args.ui_test else None, gui=webview_gui(), debug=False,
                  icon=str(Path(__file__).parent / "web/assets/mystery-logo.ico"),
                  private_mode=True, storage_path=str(data / "webview-profile"))


if __name__ == "__main__":
    main()
