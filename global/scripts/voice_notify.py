"""
Antigravity Stop Hook (Global)
Instant Offline Voice Notification via Piper Neural TTS
Written in Python for ultra-low latency, zero UI-blocking, and unified runtime.
Connects to resident Voice Daemon (127.0.0.1:54321) for 0.18s in-memory synthesis.
Auto-spawns daemon if inactive, with graceful fallback.
Guaranteed 100% hidden background execution: no black console window flicker.
"""

import os
import sys
import json
import re
import time
import tempfile
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

# Đường dẫn thư mục
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(CURRENT_DIR, 'voice_notify.log')
MODELS_DIR = os.path.join(os.path.expanduser('~'), '.gemini', 'models', 'piper')

DAEMON_HOST = '127.0.0.1'
DAEMON_PORT = 54321
DAEMON_URL = f'http://{DAEMON_HOST}:{DAEMON_PORT}'

# Danh bạ giọng đọc theo tên dự án
WORKSPACE_VOICES = {
    'csa-cms-bangiaohuongso2': 'ngochuyennew',
    'csa-cms': 'minhquang',
    'lms-html-kit': 'duyoryx',
    'chat': 'taian'
}

DEFAULT_VOICE = 'minhquang'


def get_pythonw_executable():
    if sys.platform == 'win32':
        pyw = sys.executable.replace('python.exe', 'pythonw.exe')
        if os.path.exists(pyw):
            return pyw
    return sys.executable


def get_win32_hidden_args():
    creation_flags = 0
    startupinfo = None
    if sys.platform == 'win32':
        creation_flags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
    return creation_flags, startupinfo


def log(msg):
    try:
        now_str = datetime.now().strftime('%H:%M:%S %d/%m/%Y')
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f'[{now_str}] {msg}\n')
    except Exception:
        pass


def get_workspace_key(workspace_name):
    if not workspace_name:
        return 'default'
    return re.sub(r'[^a-z0-9]', '_', workspace_name.lower())


def kill_previous_speech(ws_key):
    pid_file = os.path.join(CURRENT_DIR, f'speech_{ws_key}.pid')
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r', encoding='utf-8') as f:
                pid_str = f.read().strip()
            if pid_str.isdigit():
                pid = int(pid_str)
                if sys.platform == 'win32':
                    flags, si = get_win32_hidden_args()
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=flags,
                        startupinfo=si
                    )
                else:
                    try:
                        os.kill(pid, 9)
                    except Exception:
                        pass
                log(f'[{ws_key}] Killed previous speech PID: {pid}')
        except Exception as e:
            log(f'[{ws_key}] Error killing previous speech: {e}')

        try:
            os.remove(pid_file)
        except Exception:
            pass

    temp_wav = os.path.join(tempfile.gettempdir(), f'voice_{ws_key}.wav')
    if os.path.exists(temp_wav):
        try:
            os.remove(temp_wav)
        except Exception:
            pass


def resolve_voice_model(workspace_path, workspace_name):
    chosen_voice = ''

    # 1. Đọc cấu hình riêng từ .vscode/settings.json
    if workspace_path and os.path.exists(workspace_path):
        settings_file = os.path.join(workspace_path, '.vscode', 'settings.json')
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    if 'antigravity.voice' in settings and settings['antigravity.voice']:
                        chosen_voice = settings['antigravity.voice'].strip()
                        log(f'[{workspace_name}] Read voice setting from workspace: {chosen_voice}')
            except Exception:
                pass

    # 2. Tra cứu theo danh bạ dự án
    if not chosen_voice and workspace_name:
        ws_lower = re.sub(r'[_-]', '', workspace_name.lower())
        for key, voice in WORKSPACE_VOICES.items():
            key_lower = re.sub(r'[_-]', '', key.lower())
            if ws_lower == key_lower or key_lower in ws_lower:
                chosen_voice = voice
                break

    if not chosen_voice:
        chosen_voice = DEFAULT_VOICE

    voice_file_name = chosen_voice
    if chosen_voice in ('ngochuyen', 'ngoc_huyen'):
        standard_path = os.path.join(MODELS_DIR, 'ngochuyen.onnx')
        if not os.path.exists(standard_path):
            voice_file_name = 'ngochuyennew'

    target_path = os.path.join(MODELS_DIR, f'{voice_file_name}.onnx')
    if os.path.exists(target_path):
        log(f'[{workspace_name}] Resolved model: {chosen_voice} ({target_path})')
        return target_path

    default_path = os.path.join(MODELS_DIR, f'{DEFAULT_VOICE}.onnx')
    if os.path.exists(default_path):
        return default_path

    try:
        if os.path.exists(MODELS_DIR):
            for file in os.listdir(MODELS_DIR):
                if file.endswith('.onnx'):
                    return os.path.join(MODELS_DIR, file)
    except Exception:
        pass

    return None


def clean_for_speech(raw):
    if not raw:
        return ''

    text = raw
    text = re.sub(r'^[>*-]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```[\s\S]*?```', ' ', text)
    text = re.sub(r'https?://\S+', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'file://\S+', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'[a-zA-Z]:\\[^\s]+', ' ', text)
    text = re.sub(r'[a-zA-Z]:/[^\s]+', ' ', text)
    text = re.sub(r'\b\S+\.(js|ts|tsx|jsx|json|md|wav|html|css|py|sh|log)\b', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'[#*_~>|{}\[\]()=+\\@$%^&/]', ' ', text)
    text = re.sub(r'---+', ' ', text)
    text = re.sub(r'[:\-–—]', ', ', text)
    text = re.sub(r'\r?\n+', '. ', text)

    replacements = [
        (r'\bAPI\b', 'A P I'),
        (r'\bIDE\b', 'I D E'),
        (r'\bUI\b', 'giao diện'),
        (r'\bDB\b', 'cơ sở dữ liệu'),
        (r'\bFE\b', 'phía người dùng'),
        (r'\bBE\b', 'phía máy chủ'),
        (r'\bBug\b', 'lỗi'),
        (r'\bTest\b', 'kiểm tra'),
        (r'\bHook\b', 'bộ kích hoạt'),
        (r'\bCode\b', 'mã nguồn')
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([.,!?])', r'\1', text)
    text = re.sub(r'([.,!?])\1+', r'\1', text)
    text = re.sub(r',\s*\.', '.', text)
    text = re.sub(r'\.\s*\.', '.', text)
    text = re.sub(r'^[,.\s]+', '', text)
    return text.strip()


def extract_summary_block(content):
    default_msg = 'Em đã hoàn thành xong công việc rồi ạ!'
    if not content:
        return default_msg

    trimmed = content.strip()
    if trimmed.startswith('>'):
        lines = trimmed.split('\n')
        quote_lines = []
        for line in lines:
            l = line.strip()
            if l.startswith('>'):
                text = re.sub(r'^>\s*', '', l).strip()
                if text and 'tóm tắt nội dung' not in text.lower():
                    quote_lines.append(text)
            elif l == '':
                if len(quote_lines) > 0:
                    break
            else:
                break

        if quote_lines:
            combined = '. '.join(quote_lines)
            cleaned = clean_for_speech(combined)
            if len(cleaned) > 10:
                log(f'Extracted leading blockquote ({len(cleaned)} chars, {len(quote_lines)} lines)')
                return cleaned

    regex = r'(?:>|#|\*)*\s*Tóm tắt[^\n]*\n((?:>?[^\n]+\n?){1,6})'
    match = re.search(regex, content, flags=re.IGNORECASE)
    if match and match.group(1):
        raw_lines = [
            re.sub(r'^>\s*', '', l).strip()
            for l in match.group(1).split('\n')
            if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('---')
        ]
        combined = '. '.join(raw_lines)
        cleaned = clean_for_speech(combined)
        if len(cleaned) > 15:
            log(f'Extracted structured summary ({len(cleaned)} chars)')
            return cleaned

    general_clean = clean_for_speech(content)
    if general_clean:
        first_sentence = re.match(r'^[^.!?\n]+[.!?]', general_clean)
        fallback = first_sentence.group(0) if first_sentence else general_clean[:150]
        log(f'Fallback summary ({len(fallback)} chars)')
        return fallback

    return default_msg


def extract_content_from_transcript(transcript_path):
    default_msg = 'Em đã hoàn thành xong công việc rồi ạ!'
    if not transcript_path or not os.path.exists(transcript_path):
        return default_msg

    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in reversed(lines):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                item = json.loads(line_str)
                if (
                    item.get('source') == 'MODEL' and
                    item.get('type') == 'PLANNER_RESPONSE' and
                    not item.get('tool_calls') and
                    item.get('content') and
                    isinstance(item['content'], str)
                ):
                    return extract_summary_block(item['content'])
            except Exception:
                pass
    except Exception as err:
        log(f'Error reading transcript: {err}')

    return default_msg


def start_daemon_process():
    """Khởi động tiến trình daemon chạy ngầm hoàn toàn độc lập với Process Tree của Hook."""
    daemon_script = os.path.join(CURRENT_DIR, 'voice_daemon.py')
    if not os.path.exists(daemon_script):
        log(f"Daemon script not found at {daemon_script}")
        return False

    try:
        log(f"Spawning detached Voice Daemon...")
        if sys.platform == 'win32':
            ps_cmd = f"Start-Process pythonw -ArgumentList '\"{daemon_script}\"'"
            flags, si = get_win32_hidden_args()
            subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
                startupinfo=si
            )
        else:
            subprocess.Popen(
                [sys.executable, daemon_script],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True
            )

        # Đợi daemon bind port
        for _ in range(20):
            time.sleep(0.08)
            try:
                req = urllib.request.Request(f"{DAEMON_URL}/ping", method='GET')
                with urllib.request.urlopen(req, timeout=0.5) as resp:
                    if resp.status == 200:
                        log("Voice Daemon is online and ready!")
                        return True
            except Exception:
                pass
    except Exception as e:
        log(f"Failed to start Voice Daemon: {e}")

    return False


def send_to_daemon(text, model_path, ws_key):
    """Gửi yêu cầu phát âm thanh tới Voice Daemon."""
    payload = json.dumps({
        'text': text,
        'modelPath': model_path,
        'wsKey': ws_key
    }).encode('utf-8')

    # Thử gửi tới daemon
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                f"{DAEMON_URL}/speak",
                data=payload,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    log(f"[{ws_key}] Successfully dispatched to Voice Daemon!")
                    return True
        except (urllib.error.URLError, ConnectionRefusedError, TimeoutError):
            if attempt == 0:
                log(f"[{ws_key}] Daemon not responding, starting daemon...")
                if not start_daemon_process():
                    break
            else:
                log(f"[{ws_key}] Failed to communicate with Daemon after restart attempt.")

    return False


def fallback_launch_background_speech(text, model_path, ws_key):
    """Phương án dự phòng nếu daemon không hoạt động: chạy tiến trình con độc lập."""
    if not model_path or not os.path.exists(model_path):
        return

    temp_wav = os.path.join(tempfile.gettempdir(), f'voice_{ws_key}.wav')
    pid_file = os.path.join(CURRENT_DIR, f'speech_{ws_key}.pid')
    model_name = os.path.basename(model_path)
    pythonw_bin = get_pythonw_executable()

    log(f'[{ws_key}] Fallback: Spawning background synthesis for model {model_name}...')

    worker_script = [
        "import sys, os, subprocess",
        f"text = {json.dumps(text, ensure_ascii=False)}",
        f"model_path = {json.dumps(model_path)}",
        f"temp_wav = {json.dumps(temp_wav)}",
        f"pid_file = {json.dumps(pid_file)}",
        "try:",
        "    env = os.environ.copy()",
        "    env['PYTHONUTF8'] = '1'",
        "    env['PYTHONIOENCODING'] = 'utf-8'",
        "    flags = 0",
        "    si = None",
        "    if sys.platform == 'win32':",
        "        flags = subprocess.CREATE_NO_WINDOW",
        "        si = subprocess.STARTUPINFO()",
        "        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW",
        "        si.wShowWindow = 0",
        "    res = subprocess.run([",
        "        sys.executable, '-m', 'piper',",
        "        '-m', model_path,",
        "        '--output_file', temp_wav",
        "    ], input=text.encode('utf-8'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, timeout=30, creationflags=flags, startupinfo=si)",
        "    if res.returncode == 0 and os.path.exists(temp_wav):",
        "        if sys.platform == 'win32':",
        "            import winsound",
        "            winsound.PlaySound(temp_wav, winsound.SND_FILENAME)",
        "        elif sys.platform == 'darwin':",
        "            subprocess.run(['afplay', temp_wav])",
        "        else:",
        "            subprocess.run(['aplay', temp_wav])",
        "finally:",
        "    try:",
        "        if os.path.exists(temp_wav): os.remove(temp_wav)",
        "    except Exception: pass",
        "    try:",
        "        if os.path.exists(pid_file): os.remove(pid_file)",
        "    except Exception: pass"
    ]

    worker_code = '\n'.join(worker_script)
    creation_flags, startupinfo = get_win32_hidden_args()

    proc = subprocess.Popen(
        [pythonw_bin, '-c', worker_code],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
        startupinfo=startupinfo,
        close_fds=True
    )

    if proc.pid:
        try:
            with open(pid_file, 'w', encoding='utf-8') as f:
                f.write(str(proc.pid))
        except Exception:
            pass


def main():
    transcript_path = ''
    workspace_name = ''
    workspace_path = ''

    # 1. Đọc dữ liệu từ stdin
    try:
        if not sys.stdin.isatty():
            raw_input = sys.stdin.read()
            if raw_input:
                try:
                    payload = json.loads(raw_input)
                    transcript_path = payload.get('transcriptPath', '')
                    paths = payload.get('workspacePaths', [])
                    if paths and isinstance(paths, list):
                        workspace_path = paths[0]
                        workspace_name = os.path.basename(workspace_path)
                    elif payload.get('cwd'):
                        workspace_path = payload['cwd']
                        workspace_name = os.path.basename(workspace_path)
                except Exception:
                    pass
    except Exception:
        pass

    # 2. PHẢN HỒI APPROVE NGAY LẬP TỨC (0ms Blocking)
    try:
        sys.stdout.write(json.dumps({"decision": "approve"}) + "\n")
        sys.stdout.flush()
    except Exception:
        pass

    if not workspace_name:
        workspace_name = os.path.basename(os.getcwd())

    ws_key = get_workspace_key(workspace_name)
    log(f'[{ws_key}] Python Stop hook triggered for workspace: {workspace_name}')

    # Xác định mô hình và bóc tách nội dung
    model_path = resolve_voice_model(workspace_path, workspace_name)
    text_to_speak = extract_content_from_transcript(transcript_path)

    log(f'[{ws_key}] Final text to speak: {text_to_speak}')

    # 3. Gửi sang Voice Daemon (In-Memory LRU Cache) để phát tức thì trong 0.18s
    success = send_to_daemon(text_to_speak, model_path, ws_key)
    if not success:
        log(f"[{ws_key}] Daemon unavailable, running fallback background speech.")
        kill_previous_speech(ws_key)
        fallback_launch_background_speech(text_to_speak, model_path, ws_key)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log(f'Main execution error: {e}')
        try:
            sys.stdout.write(json.dumps({"decision": "approve"}) + "\n")
            sys.stdout.flush()
        except Exception:
            pass
