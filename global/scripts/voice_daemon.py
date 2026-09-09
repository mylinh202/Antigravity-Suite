"""
Antigravity Voice Daemon (Resident In-Memory Piper TTS Service)
Maintains up to 3 recently used voices in RAM (LRU Cache) for instantaneous speech (~0.18s).
Strict memory management: automatic eviction beyond 3 voices, auto-sleep after 15 minutes idle.
Uses ThreadingHTTPServer and asynchronous processing queue for zero-blocking HTTP responses.
"""

import os
import sys
import gc
import json
import time
import wave
import tempfile
import threading
import subprocess
from datetime import datetime
from collections import OrderedDict
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

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
    except Exception:
        pass


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

            # Nếu vượt quá số lượng tối đa: loại bỏ giọng ít dùng nhất
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
PLAYERS_LOCK = threading.Lock()
LAST_ACTIVITY_TIME = time.time()


def stop_previous_playback(ws_key):
    """Dừng âm thanh cũ của cùng workspace nếu đang phát."""
    with PLAYERS_LOCK:
        pid_file = os.path.join(CURRENT_DIR, f'speech_{ws_key}.pid')
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r', encoding='utf-8') as f:
                    pid_str = f.read().strip()
                if pid_str.isdigit():
                    pid = int(pid_str)
                    if sys.platform == 'win32':
                        subprocess.run(
                            ['taskkill', '/F', '/T', '/PID', str(pid)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                        )
                    else:
                        try:
                            os.kill(pid, 9)
                        except Exception:
                            pass
                    log(f"[{ws_key}] Daemon stopped previous speech PID: {pid}")
            except Exception:
                pass
            try:
                os.remove(pid_file)
            except Exception:
                pass


def play_audio_file(temp_wav, ws_key):
    """Phát âm thanh trong tiến trình con độc lập và dọn dẹp file tạm."""
    pid_file = os.path.join(CURRENT_DIR, f'speech_{ws_key}.pid')
    play_script = [
        "import sys, os",
        f"wav = {json.dumps(temp_wav)}",
        f"pid_file = {json.dumps(pid_file)}",
        "try:",
        "    if sys.platform == 'win32':",
        "        import winsound",
        "        winsound.PlaySound(wav, winsound.SND_FILENAME)",
        "    elif sys.platform == 'darwin':",
        "        import subprocess; subprocess.run(['afplay', wav])",
        "    else:",
        "        import subprocess; subprocess.run(['aplay', wav])",
        "finally:",
        "    try:",
        "        if os.path.exists(wav): os.remove(wav)",
        "    except Exception: pass",
        "    try:",
        "        if os.path.exists(pid_file): os.remove(pid_file)",
        "    except Exception: pass"
    ]

    pyw = sys.executable.replace('python.exe', 'pythonw.exe')
    if not os.path.exists(pyw):
        pyw = sys.executable

    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
    si = None
    if sys.platform == 'win32':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0

    proc = subprocess.Popen(
        [pyw, '-c', '\n'.join(play_script)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
        startupinfo=si,
        close_fds=True
    )

    if proc.pid:
        try:
            with open(pid_file, 'w', encoding='utf-8') as f:
                f.write(str(proc.pid))
            log(f"[{ws_key}] Started audio player PID: {proc.pid}")
        except Exception:
            pass


def process_speech_worker(text, model_path, ws_key):
    """Xử lý tổng hợp và phát âm thanh trong luồng riêng biệt."""
    try:
        stop_previous_playback(ws_key)

        voice = VOICE_CACHE.get(model_path)
        if voice:
            temp_wav = os.path.join(tempfile.gettempdir(), f'voice_{ws_key}.wav')
            t0 = time.perf_counter()
            with wave.open(temp_wav, 'wb') as wav_file:
                voice.synthesize_wav(text, wav_file)
            synth_time = (time.perf_counter() - t0) * 1000
            log(f"[{ws_key}] Synthesized {len(text)} chars in {synth_time:.1f}ms! Starting playback...")
            play_audio_file(temp_wav, ws_key)
        else:
            log(f"[{ws_key}] Could not retrieve voice model for: {model_path}")
    except Exception as e:
        log(f"[{ws_key}] Error in process_speech_worker: {e}")


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
                'max_voices': MAX_CACHED_VOICES
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

                # Phản hồi 200 OK ngay cho client trong 1ms
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "processing"}')

                # Bắn việc xử lý sang luồng nền độc lập để không block bất kỳ request nào
                worker = threading.Thread(
                    target=process_speech_worker,
                    args=(text, model_path, ws_key),
                    daemon=True
                )
                worker.start()

            except Exception as e:
                log(f"Error handling /speak: {e}")
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
        if idle_duration >= IDLE_TIMEOUT_SECONDS:
            log(f"Daemon has been idle for {int(idle_duration)}s (>= {IDLE_TIMEOUT_SECONDS}s). Exiting to free all RAM.")
            os._exit(0)


def main():
    log(f"Starting Voice Daemon on {HOST}:{PORT} (Max {MAX_CACHED_VOICES} cached voices, Threaded)...")
    
    monitor_thread = threading.Thread(target=idle_monitor, daemon=True)
    monitor_thread.start()

    server = ThreadingHTTPServer((HOST, PORT), DaemonHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        log("Voice Daemon stopped.")


if __name__ == '__main__':
    main()
