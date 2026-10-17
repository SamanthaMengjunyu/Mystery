import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error

from desktop.backend import Backend
from desktop.app import create_server
from desktop.music import MusicLibrary,byte_range
from desktop.reminders import birthday_reminders


class AmbientTest(unittest.TestCase):
    def test_audio_byte_ranges(self):
        self.assertEqual(byte_range(None,10),(0,9,False))
        for text,expected in [('bytes=2-5',(2,5,True)),('bytes=7-',(7,9,True)),('bytes=-3',(7,9,True)),('bytes=0-99',(0,9,True))]:self.assertEqual(byte_range(text,10),expected)
        for text in ['bytes=10-','bytes=3-1','bytes=-0','bytes=0-1,3-4','items=0-2','bytes=a-b','bytes=-']:
            with self.assertRaises(ValueError):byte_range(text,10)

    def test_audio_folder_scope_recursion_and_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();data=root/'data';data.mkdir();folder=root/'songs';folder.mkdir();(folder/'nested').mkdir()
            (folder/'song.MP3').write_bytes(b'1234567890');(folder/'ignore.txt').write_text('private');(folder/'nested/second.wav').write_bytes(b'wave')
            music=MusicLibrary(data);self.assertEqual(music.choose(),{'native':False});music.folder_picker=lambda:folder
            library=music.choose();self.assertEqual(len(library['tracks']),2);identity=next(t['id'] for t in library['tracks'] if t['name']=='song')
            self.assertEqual(music.resolve(identity)[0],(folder/'song.MP3').resolve())
            for value in ['../ignore.txt','../../secret',str(folder/'ignore.txt')]:
                with self.assertRaises(FileNotFoundError):music.resolve(value)
            music.save({'recursive':False,'volume':.2,'mode':'shuffle','folder':'C:/not-selected'})
            self.assertEqual(len(music.library()['tracks']),1)
            restored=MusicLibrary(data);self.assertEqual(len(restored.library()['tracks']),1);self.assertEqual(restored.options['volume'],.2)
            music.folder_picker=lambda:None;self.assertTrue(music.choose()['cancelled']);self.assertEqual(music.options['folder'],str(folder))
            other=root/'other';other.mkdir();music.options['folder']=str(other)
            with self.assertRaises(FileNotFoundError):music.resolve(identity)

    def test_audio_settings_validation_is_atomic(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=MusicLibrary(tmp)
            for options in [{'volume':float('nan')},{'volume':2},{'volume':.8,'mode':'invalid'},{'recursive':'true'}]:
                with self.assertRaises(ValueError):m.save(options)
            self.assertEqual(m.options['volume'],.45)

    def test_authenticated_stream_seeking_and_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'music';folder.mkdir();content=bytes(range(100));(folder/'track.mp3').write_bytes(content)
            server,backend,url=create_server(root/'data');backend.music.folder_picker=lambda:folder
            identity=backend.music.choose()['tracks'][0]['id'];origin=url.split('/?')[0];threading.Thread(target=server.serve_forever,daemon=True).start()
            try:
                with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(origin+'/media/'+identity)
                response=urllib.request.urlopen(url);cookie=response.headers['Set-Cookie'].split(';')[0];response.close()
                request=urllib.request.Request(origin+'/media/'+identity,headers={'Cookie':cookie,'Range':'bytes=10-19'})
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.status,206);self.assertEqual(response.read(),content[10:20]);self.assertEqual(response.headers['Content-Range'],'bytes 10-19/100')
                request=urllib.request.Request(origin+'/media/'+identity,headers={'Cookie':cookie},method='HEAD')
                with urllib.request.urlopen(request) as response:self.assertEqual(response.read(),b'');self.assertEqual(response.headers['Content-Length'],'100')
                request=urllib.request.Request(origin+'/media/'+identity,headers={'Cookie':cookie,'Range':'bytes=999-'})
                with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request)
                self.assertEqual(error.exception.code,416)
                with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(urllib.request.Request(origin+'/media/not-indexed',headers={'Cookie':cookie}))
            finally:server.shutdown();server.server_close()

    def test_note_update_preserves_birthday_residence_and_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=Backend(Path(tmp));p=b.save_birthday({'name':'朋友','datetime':'2000-08-16T04:00','color':'#8edbcb','current_place':'Tokyo','current_longitude':139.69,'current_latitude':35.69})
            updated=b.save_birthday_note({'id':p['id'],'notes':'  喜欢安静的音乐\n记得买花  '})
            self.assertEqual(updated['notes'],'喜欢安静的音乐\n记得买花')
            for key,value in p.items():
                if key not in ('notes','updated'):self.assertEqual(updated[key],value)
            self.assertEqual(updated['current_tz_name'],'Asia/Tokyo');self.assertEqual(Backend(Path(tmp)).birthday(p['id']),updated)
            for invalid in [{'id':p['id'],'notes':'x'*1001},{'id':'missing','notes':'x'}]:
                with self.assertRaises(ValueError):b.save_birthday_note(invalid)
            cleared=b.save_birthday({**updated,'current_place':'','current_latitude':'','current_longitude':'','current_tz_name':'Asia/Tokyo'})
            self.assertIsNone(cleared['current_tz_name']);self.assertEqual(b.records(),[])

    def person(self,id='a',date='2000-06-21T04:00',zone='Asia/Tokyo',**kw):
        return {'id':id,'name':id,'datetime':date,'tz_name':'Asia/Shanghai','current_tz_name':zone,**kw}

    def test_reminders_follow_residence_local_dates_and_five_day_boundary(self):
        people=[self.person(),self.person('b',zone='America/Los_Angeles'),self.person('c','2000-06-26T04:00'),self.person('d','2000-06-27T04:00')]
        r=birthday_reminders(people,'Asia/Shanghai','2026-06-20T15:30:00Z');items={p['id']:p for p in r['items']}
        self.assertEqual(items['a']['days'],0);self.assertEqual(items['b']['days'],1);self.assertEqual(items['c']['days'],5);self.assertNotIn('d',items)
        self.assertEqual(items['a']['viewer_start'],'2026-06-20T23:00+08:00');self.assertEqual(items['a']['difference_minutes'],60)

    def test_reminders_new_year_leap_day_and_dst(self):
        r=birthday_reminders([self.person(date='2000-01-02T00:00')],'UTC','2026-12-30T16:00:00Z')
        self.assertEqual(r['items'][0]['days'],2);self.assertEqual(r['items'][0]['age'],27)
        for now,date in [('2027-02-23T00:00:00Z','2027-02-28'),('2028-02-24T00:00:00Z','2028-02-29')]:
            p=birthday_reminders([self.person(date='2000-02-29T00:00',zone='UTC')],'UTC',now)['items'][0]
            self.assertEqual(p['days'],5);self.assertEqual(p['birthday_date'],date)
        p=birthday_reminders([self.person(date='2000-03-08T00:00',zone='America/New_York')],'UTC','2026-03-08T12:00:00Z')['items'][0]
        self.assertEqual(p['days'],0);self.assertEqual(p['difference_minutes'],-240)
        self.assertEqual(p['viewer_start'],'2026-03-08T05:00+00:00')

    def test_legacy_residence_and_timezone_fallback(self):
        p=self.person();p.pop('current_tz_name');p.update(current_longitude=139.69,current_latitude=35.69)
        self.assertEqual(birthday_reminders([p],'UTC','2026-06-20T16:00:00Z')['items'][0]['tz_name'],'Asia/Tokyo')
        p.pop('current_longitude');p.pop('current_latitude')
        self.assertEqual(birthday_reminders([p],'UTC','2026-06-20T16:00:00Z')['items'][0]['zone_source'],'birth')
        with self.assertRaises(ValueError):birthday_reminders([p],'UTC','2026-06-20T16:00:00')


if __name__=='__main__':unittest.main()
