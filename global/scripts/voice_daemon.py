"""
Antigravity Voice Daemon (Resident In-Memory Piper TTS Service)
Maintains up to 3 recently used voices in RAM (LRU Cache) for instantaneous speech (~0.18s).
Features:
- Global FIFO playback queue: workspaces speak in turns, never overlapping.
- WinRT SMTC (Windows Media Control) Integration: directly pauses and reliably resumes background media (YouTube on Chrome/Edge, Spotify, VLC).
- Smooth audio fade-out & pause: dims volume in 350ms, pauses all playing sessions, and restores speech volume.
- Seamless resume & fade-in: cleanly unfreezes playback and restores original volume smoothly when notifications complete without toggle conflicts.
- Zero-blocking HTTP interface and auto-sleep after 15 minutes of inactivity.
"""

import os
import sys
import gc
import json
import time
import wave
import queue
import tempfile
import threading
import subprocess
import traceback
from datetime import datetime
from collections import OrderedDict
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import ctypes
from ctypes import HRESULT, POINTER, Structure, c_float, c_int, c_void_p, byref, cast
from ctypes.wintypes import DWORD, BOOL

HOST = '127.0.0.1'
PORT = 54321
MAX_CACHED_VOICES = 3
IDLE_TIMEOUT_SECONDS = 900  # 15 phút không có yêu cầu -> tự động tắt giải phóng RAM

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(CURRENT_DIR, 'voice_daemon.log')


def log(msg):
    try:
        now_str = datetime.now().strftime('%H:%M:%S %d/%m/%Y')
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f'[{now_str}] {msg}\n')
            f.flush()
    except Exception:
        pass


# ==============================================================================
# BỘ ĐIỀU KHIỂN ÂM THANH WINDOWS (WASAPI + WINRT SMTC MEDIA CONTROLLER)
# ==============================================================================

HWND_BROADCAST = 0xFFFF
WM_APPCOMMAND = 0x0319
APPCOMMAND_MEDIA_PAUSE = 47
APPCOMMAND_MEDIA_PLAY = 46

VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_PAUSE = 0xB2


class GUID(Structure):
    _fields_ = [
        ("Data1", DWORD),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8)
    ]

    def __init__(self, l, w1, w2, b1, b2, b3, b4, b5, b6, b7, b8):
        self.Data1 = l
        self.Data2 = w1
        self.Data3 = w2
        self.Data4 = (ctypes.c_ubyte * 8)(b1, b2, b3, b4, b5, b6, b7, b8)


CLSID_MMDeviceEnumerator = GUID(0xBCDE0395, 0xE52F, 0x467C, 0x8E, 0x3D, 0xC4, 0x57, 0x92, 0x91, 0x69, 0x2E)
IID_IMMDeviceEnumerator = GUID(0xA95664D2, 0x9614, 0x4F35, 0xA7, 0x46, 0xDE, 0x8D, 0xB6, 0x36, 0x17, 0xE6)
IID_IAudioEndpointVolume = GUID(0x5CDF2C82, 0x841E, 0x4546, 0x97, 0x22, 0x0C, 0xF7, 0x40, 0x78, 0x22, 0x9A)


class IAudioEndpointVolumeVtbl(Structure):
    _fields_ = [
        ('QueryInterface', c_void_p),
        ('AddRef', c_void_p),
        ('Release', c_void_p),
        ('RegisterControlChangeNotify', c_void_p),
        ('UnregisterControlChangeNotify', c_void_p),
        ('GetChannelCount', c_void_p),
        ('SetMasterVolumeLevel', c_void_p),
        ('SetMasterVolumeLevelScalar', ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_float, c_void_p)),
        ('GetMasterVolumeLevel', c_void_p),
        ('GetMasterVolumeLevelScalar', ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_float))),
        ('SetChannelVolumeLevel', c_void_p),
        ('SetChannelVolumeLevelScalar', c_void_p),
        ('GetChannelVolumeLevel', c_void_p),
        ('GetChannelVolumeLevelScalar', c_void_p),
        ('SetMute', ctypes.WINFUNCTYPE(HRESULT, c_void_p, BOOL, c_void_p)),
        ('GetMute', ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(BOOL))),
    ]


class IAudioEndpointVolume(Structure):
    _fields_ = [('lpVtbl', POINTER(IAudioEndpointVolumeVtbl))]


class IMMDeviceVtbl(Structure):
    _fields_ = [
        ('QueryInterface', c_void_p),
        ('AddRef', c_void_p),
        ('Release', c_void_p),
        ('Activate', ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), DWORD, c_void_p, POINTER(c_void_p))),
    ]


class IMMDevice(Structure):
    _fields_ = [('lpVtbl', POINTER(IMMDeviceVtbl))]


class IMMDeviceEnumeratorVtbl(Structure):
    _fields_ = [
        ('QueryInterface', c_void_p),
        ('AddRef', c_void_p),
        ('Release', c_void_p),
        ('EnumAudioEndpoints', c_void_p),
        ('GetDefaultAudioEndpoint', ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_int, c_int, POINTER(POINTER(IMMDevice)))),
    ]


class IMMDeviceEnumerator(Structure):
    _fields_ = [('lpVtbl', POINTER(IMMDeviceEnumeratorVtbl))]


def smtc_pause_all_media():
    """Tạm dừng chính xác tất cả các phiên media đang phát (YouTube, Chrome, Edge, Spotify) qua WinRT API."""
    if sys.platform != 'win32':
        return False
    ps_script = (
        "[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType = WindowsRuntime] | Out-Null; "
        "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
        "$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }; "
        "function AwaitTask($t, $r) { $at = $asTaskGeneric.MakeGenericMethod($r); $nt = $at.Invoke($null, @($t)); $nt.Wait(800) | Out-Null; return $nt.Result }; "
        "$mgr = AwaitTask ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]); "
        "$didPause = $false; "
        "if ($mgr) { "
        "  $sessions = $mgr.GetSessions(); "
        "  foreach ($s in $sessions) { "
        "    if ($s.GetPlaybackInfo().PlaybackStatus -eq 'Playing') { "
        "      $res = AwaitTask ($s.TryPauseAsync()) ([System.Boolean]); "
        "      if ($res) { $didPause = $true; Write-Output ($s.SourceAppUserModelId + ' PAUSED') } "
        "    } "
        "  } "
        "}; "
        "if ($didPause) { Write-Output 'SMTC_PAUSED_OK' }"
    )
    try:
        flags = subprocess.CREATE_NO_WINDOW
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        proc = subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-Command', ps_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
            startupinfo=si,
            timeout=2.0
        )
        out = proc.stdout.decode('utf-8', errors='ignore')
        if 'SMTC_PAUSED_OK' in out:
            log(f"WinRT SMTC successfully paused active media: {out.strip()}")
            return True
    except Exception as e:
        log(f"Error in smtc_pause_all_media: {e}")
    return False


def smtc_resume_all_media():
    """Phát tiếp các phiên media vừa bị tạm dừng qua WinRT API với cơ chế dự phòng hai lớp."""
    if sys.platform != 'win32':
        return False
    ps_script = (
        "[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType = WindowsRuntime] | Out-Null; "
        "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
        "$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }; "
        "function AwaitTask($t, $r) { $at = $asTaskGeneric.MakeGenericMethod($r); $nt = $at.Invoke($null, @($t)); $nt.Wait(800) | Out-Null; return $nt.Result }; "
        "$mgr = AwaitTask ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]); "
        "$didResume = $false; "
        "if ($mgr) { "
        "  $sessions = $mgr.GetSessions(); "
        "  foreach ($s in $sessions) { "
        "    $status = $s.GetPlaybackInfo().PlaybackStatus; "
        "    if ($status -eq 'Paused' -or $status -eq 'Stopped') { "
        "      $res = AwaitTask ($s.TryPlayAsync()) ([System.Boolean]); "
        "      if (-not $res) { "
        "        $res = AwaitTask ($s.TryTogglePlayPauseAsync()) ([System.Boolean]); "
        "      }; "
        "      if ($res) { $didResume = $true; Write-Output ($s.SourceAppUserModelId + ' RESUMED') } "
        "    } "
        "  } "
        "}; "
        "if ($didResume) { Write-Output 'SMTC_RESUMED_OK' }"
    )
    try:
        flags = subprocess.CREATE_NO_WINDOW
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        proc = subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-Command', ps_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
            startupinfo=si,
            timeout=2.0
        )
        out = proc.stdout.decode('utf-8', errors='ignore')
        log(f"WinRT SMTC resumed media result: {out.strip()}")
        return 'SMTC_RESUMED_OK' in out or 'RESUMED' in out
    except Exception as e:
        log(f"Error in smtc_resume_all_media: {e}")
    return False


class WindowsAudioController:
    """Quản lý âm lượng và điều khiển phát sóng tạm dừng/phát tiếp toàn bộ ứng dụng hệ thống."""
    def __init__(self):
        self.is_paused = False
        self.media_was_playing = False
        self.saved_volume = 1.0
        self.lock = threading.Lock()

    def _get_endpoint_volume(self):
        if sys.platform != 'win32':
            return None
        try:
            ctypes.windll.ole32.CoInitialize(None)
            enumerator = POINTER(IMMDeviceEnumerator)()
            hr = ctypes.windll.ole32.CoCreateInstance(
                byref(CLSID_MMDeviceEnumerator),
                None,
                1,  # CLSCTX_INPROC_SERVER
                byref(IID_IMMDeviceEnumerator),
                byref(enumerator)
            )
            if hr != 0 or not enumerator:
                return None

            device = POINTER(IMMDevice)()
            hr = enumerator.contents.lpVtbl.contents.GetDefaultAudioEndpoint(enumerator, 0, 1, byref(device))
            if hr != 0 or not device:
                return None

            pv = c_void_p()
            hr = device.contents.lpVtbl.contents.Activate(
                device,
                byref(IID_IAudioEndpointVolume),
                1,  # CLSCTX_INPROC_SERVER
                None,
                byref(pv)
            )
            if hr != 0 or not pv:
                return None

            return cast(pv, POINTER(IAudioEndpointVolume))
        except Exception as e:
            log(f"Error getting audio endpoint volume: {e}")
            return None

    def get_volume(self):
        if sys.platform != 'win32':
            return 1.0
        try:
            epv = self._get_endpoint_volume()
            if not epv:
                return 1.0
            vol = c_float()
            epv.contents.lpVtbl.contents.GetMasterVolumeLevelScalar(epv, byref(vol))
            return float(vol.value)
        except Exception:
            return 1.0

    def set_volume(self, target_vol):
        if sys.platform != 'win32':
            return
        try:
            epv = self._get_endpoint_volume()
            if not epv:
                return
            clamped = max(0.0, min(1.0, float(target_vol)))
            epv.contents.lpVtbl.contents.SetMasterVolumeLevelScalar(epv, c_float(clamped), None)
        except Exception as e:
            log(f"Error setting master volume: {e}")

    def broadcast_app_command(self, cmd):
        """Phát sóng lệnh đa phương tiện có chủ đích tới TẤT CẢ các cửa sổ ứng dụng."""
        if sys.platform == 'win32':
            try:
                lParam = cmd << 16
                ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_APPCOMMAND, 0, lParam)
            except Exception as e:
                log(f"Error broadcasting WM_APPCOMMAND {cmd}: {e}")

    def fade_out_and_pause(self, duration=0.35, steps=15):
        """Kiểm tra và chỉ fade/pause nếu thực sự có nhạc đang phát; nếu không thì giữ nguyên volume cho giọng đọc."""
        with self.lock:
            current_vol = self.get_volume()
            self.saved_volume = current_vol

            # 1. Thử tạm dừng qua WinRT SMTC để xác định xem có media nào đang phát hay không
            paused_any = smtc_pause_all_media()
            self.media_was_playing = paused_any
            self.is_paused = True

            if not paused_any:
                log("No active media playing detected. Skipping volume fade-out and keeping speech volume.")
                return

            log(f"Media Fade-Out initiated. Current volume: {current_vol:.2f}")
            if current_vol > 0.05:
                step_delay = duration / steps
                vol_step = current_vol / steps
                curr = current_vol
                for _ in range(steps):
                    curr -= vol_step
                    self.set_volume(curr)
                    time.sleep(step_delay)
                self.set_volume(0.0)

            # Phát sóng thêm lệnh PAUSE định hướng
            self.broadcast_app_command(APPCOMMAND_MEDIA_PAUSE)

            # Đợi ngắn cho media ổn định rồi phục hồi âm lượng chuẩn cho giọng đọc
            time.sleep(0.08)
            self.set_volume(self.saved_volume)
            log("Active media paused & volume restored for speech.")

    def resume_and_fade_in(self, duration=0.35, steps=15):
        """Chỉ tiếp tục phát media và fade-in nếu trước đó thực sự có nhạc đang chạy."""
        with self.lock:
            if not self.is_paused:
                return

            self.is_paused = False

            if not self.media_was_playing:
                log("No media was playing prior to speech. Skipping resume & fade-in.")
                return

            self.media_was_playing = False
            log(f"Media Fade-In initiated. Restoring volume to: {self.saved_volume:.2f}")

            # Đưa volume về 0 trước khi gửi lệnh tiếp tục phát
            self.set_volume(0.0)
            time.sleep(0.03)

            # 1. Phát tiếp qua WinRT SMTC
            resumed = smtc_resume_all_media()

            # 2. Phát sóng thêm lệnh PLAY định hướng (tuyệt đối không gửi phím Toggle)
            if not resumed:
                self.broadcast_app_command(APPCOMMAND_MEDIA_PLAY)

            # 3. Tăng dần âm lượng từ 0 lên mức ban đầu
            target_vol = max(0.1, self.saved_volume)
            step_delay = duration / steps
            vol_step = target_vol / steps
            curr = 0.0
            for _ in range(steps):
                curr += vol_step
                self.set_volume(curr)
                time.sleep(step_delay)
            self.set_volume(target_vol)
            log(f"System Media Resumed cleanly and volume fully restored to {target_vol:.2f}.")


AUDIO_CONTROLLER = WindowsAudioController()


# ==============================================================================
# BỘ ĐỆM GIỌNG ĐỌC LRU VÀ HÀNG ĐỢI PHÁT TUẦN TỰ
# ==============================================================================

class VoiceLRUCache:
    """Bộ đệm lưu trữ tối đa 3 giọng đọc gần nhất trong RAM."""
    def __init__(self, max_size=MAX_CACHED_VOICES):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.Lock()

    def get(self, model_path):
        with self.lock:
            if model_path in self.cache:
                self.cache.move_to_end(model_path)
                log(f"Cache HIT for model: {os.path.basename(model_path)} (Current RAM cache size: {len(self.cache)})")
                return self.cache[model_path]

            log(f"Cache MISS for model: {os.path.basename(model_path)}. Loading into RAM...")
            t0 = time.perf_counter()
            try:
                from piper.voice import PiperVoice
                voice = PiperVoice.load(model_path)
                elapsed = (time.perf_counter() - t0) * 1000
                log(f"Successfully loaded {os.path.basename(model_path)} into RAM in {elapsed:.1f}ms")
            except Exception as e:
                log(f"Error loading model {model_path}: {e}")
                return None

            self.cache[model_path] = voice

            while len(self.cache) > self.max_size:
                evicted_path, evicted_voice = self.cache.popitem(last=False)
                del evicted_voice
                gc.collect()
                log(f"Evicted oldest model from RAM: {os.path.basename(evicted_path)} to free memory")

            return voice

    def get_cached_names(self):
        with self.lock:
            return [os.path.basename(p) for p in self.cache.keys()]


VOICE_CACHE = VoiceLRUCache(max_size=MAX_CACHED_VOICES)
PLAYBACK_QUEUE = queue.Queue()
LAST_ACTIVITY_TIME = time.time()


def playback_worker_loop():
    """Luồng công nhân xử lý hàng đợi phát tuần tự theo lượt."""
    global LAST_ACTIVITY_TIME
    while True:
        try:
            item = PLAYBACK_QUEUE.get()
            if item is None:
                break

            text = item['text']
            model_path = item['model_path']
            ws_key = item['ws_key']

            LAST_ACTIVITY_TIME = time.time()

            # Nếu đây là tác vụ đầu tiên bắt đầu đọc: WinRT Pause & Fade-out
            if not AUDIO_CONTROLLER.is_paused:
                AUDIO_CONTROLLER.fade_out_and_pause()

            # 1. Tổng hợp giọng đọc
            voice = VOICE_CACHE.get(model_path)
            if voice:
                temp_wav = os.path.join(tempfile.gettempdir(), f'voice_{ws_key}_{int(time.time()*1000)}.wav')
                t0 = time.perf_counter()
                with wave.open(temp_wav, 'wb') as wav_file:
                    voice.synthesize_wav(text, wav_file)
                synth_time = (time.perf_counter() - t0) * 1000
                log(f"[{ws_key}] Synthesized {len(text)} chars in {synth_time:.1f}ms. Playing speech...")

                # 2. Phát âm thanh đồng bộ
                try:
                    if sys.platform == 'win32':
                        import winsound
                        winsound.PlaySound(temp_wav, winsound.SND_FILENAME)
                    elif sys.platform == 'darwin':
                        subprocess.run(['afplay', temp_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        subprocess.run(['aplay', temp_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as play_err:
                    log(f"[{ws_key}] Playback error: {play_err}")
                finally:
                    try:
                        if os.path.exists(temp_wav):
                            os.remove(temp_wav)
                    except Exception:
                        pass
                log(f"[{ws_key}] Speech finished.")
            else:
                log(f"[{ws_key}] Could not retrieve voice model for: {model_path}")

            PLAYBACK_QUEUE.task_done()
            LAST_ACTIVITY_TIME = time.time()

            # Nếu đã hết việc trong hàng đợi -> Resume media & Fade-in mượt mà
            if PLAYBACK_QUEUE.empty() and AUDIO_CONTROLLER.is_paused:
                time.sleep(0.2)
                if PLAYBACK_QUEUE.empty():
                    AUDIO_CONTROLLER.resume_and_fade_in()

        except Exception as e:
            log(f"Error in playback worker loop: {e}\n{traceback.format_exc()}")
            time.sleep(0.1)


# ==============================================================================
# HTTP SERVER & REQUEST HANDLER
# ==============================================================================

class DaemonHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global LAST_ACTIVITY_TIME
        LAST_ACTIVITY_TIME = time.time()

        if self.path == '/ping':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            resp = {
                'status': 'ok',
                'cached_voices': VOICE_CACHE.get_cached_names(),
                'max_voices': MAX_CACHED_VOICES,
                'queue_size': PLAYBACK_QUEUE.qsize(),
                'media_paused': AUDIO_CONTROLLER.is_paused
            }
            self.wfile.write(json.dumps(resp).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global LAST_ACTIVITY_TIME
        LAST_ACTIVITY_TIME = time.time()

        if self.path == '/speak':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
                text = data.get('text', '').strip()
                model_path = data.get('modelPath', '')
                ws_key = data.get('wsKey', 'default')

                if not text or not model_path or not os.path.exists(model_path):
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'{"error": "Invalid text or modelPath"}')
                    return

                # Phản hồi 200 OK ngay lập tức (1ms non-blocking)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "queued"}')

                # Đẩy yêu cầu vào hàng đợi phát tuần tự theo lượt
                PLAYBACK_QUEUE.put({
                    'text': text,
                    'model_path': model_path,
                    'ws_key': ws_key
                })
                log(f"[{ws_key}] Queued speech task ({len(text)} chars). Current queue size: {PLAYBACK_QUEUE.qsize()}")

            except Exception as e:
                log(f"Error handling /speak: {e}\n{traceback.format_exc()}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def idle_monitor():
    """Kiểm tra thời gian nhàn rỗi: nếu quá 15 phút không dùng -> tự tắt để trả lại RAM."""
    global LAST_ACTIVITY_TIME
    while True:
        time.sleep(30)
        idle_duration = time.time() - LAST_ACTIVITY_TIME
        if idle_duration >= IDLE_TIMEOUT_SECONDS and PLAYBACK_QUEUE.empty():
            log(f"Daemon has been idle for {int(idle_duration)}s (>= {IDLE_TIMEOUT_SECONDS}s). Exiting to free all RAM.")
            os._exit(0)


def main():
    log(f"Starting Voice Daemon on {HOST}:{PORT} (Sequential Queue + Clean SMTC Resume)...")
    
    # Khởi chạy luồng xử lý hàng đợi
    worker_thread = threading.Thread(target=playback_worker_loop, daemon=True)
    worker_thread.start()

    # Khởi chạy luồng giám sát nhàn rỗi
    monitor_thread = threading.Thread(target=idle_monitor, daemon=True)
    monitor_thread.start()

    try:
        server = ThreadingHTTPServer((HOST, PORT), DaemonHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log(f"Server error: {e}\n{traceback.format_exc()}")
    finally:
        log("Voice Daemon stopped.")


if __name__ == '__main__':
    main()
