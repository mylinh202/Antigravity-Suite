const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');

let statusBarItem;

const MODELS_DIR = path.join(os.homedir(), '.gemini', 'models', 'piper');

const VOICE_NAMES = {
  'minhquang': 'Minh Quang',
  'ngochuyennew': 'Ngọc Huyền',
  'ngochuyen': 'Ngọc Huyền',
  'duyoryx': 'Duy Oryx',
  'duyoryx3175': 'Duy Oryx',
  'taian': 'Tài An',
  'taian4': 'Tài An',
  'taian2': 'Tài An',
  'thientam': 'Thiện Tâm',
  'ngocngan': 'Ngọc Ngạn',
  'ngocngan3701': 'Ngọc Ngạn',
  'banmai': 'Ban Mai',
  'minhthu': 'Minh Thu',
  'vietthao': 'Việt Thảo',
  'vietthao3886': 'Việt Thảo',
  'tranthanh': 'Trấn Thành',
  'tranthanh3870': 'Trấn Thành',
  'manhdung': 'Mạnh Dũng',
  'maiphuong': 'Mai Phương',
  'phuongtrang': 'Phương Trang',
  'mytam': 'Mỹ Tâm',
  'mytam2794': 'Mỹ Tâm',
  'deepman3909': 'Nam Trầm',
  'yannew': 'Yan'
};

const CLOUD_VOICES = [
  { key: 'banmai', file: 'banmai.onnx', label: 'Ban Mai', desc: 'Nữ miền Bắc nhẹ nhàng, thanh lịch' },
  { key: 'minhthu', file: 'minhthu.onnx', label: 'Minh Thu', desc: 'Nữ dịu dàng, trong sáng' },
  { key: 'vietthao3886', file: 'vietthao3886.onnx', label: 'Việt Thảo', desc: 'Nam phong cách người dẫn chương trình' },
  { key: 'tranthanh3870', file: 'tranthanh3870.onnx', label: 'Trấn Thành', desc: 'Nam biểu cảm sinh động' },
  { key: 'manhdung', file: 'manhdung.onnx', label: 'Mạnh Dũng', desc: 'Nam trung niên chững chạc' },
  { key: 'maiphuong', file: 'maiphuong.onnx', label: 'Mai Phương', desc: 'Nữ ngọt ngào, truyền cảm' },
  { key: 'phuongtrang', file: 'phuongtrang.onnx', label: 'Phương Trang', desc: 'Nữ ấm áp, rõ ràng' },
  { key: 'mytam2794', file: 'mytam2794.onnx', label: 'Mỹ Tâm', desc: 'Nữ tươi sáng' },
  { key: 'deepman3909', file: 'deepman3909.onnx', label: 'Nam Trầm', desc: 'Nam âm vực dày dặn' },
  { key: 'yannew', file: 'yannew.onnx', label: 'Yan mới', desc: 'Nữ trẻ trung, hiện đại' }
];

function getDownloadedVoices() {
  const voices = [];
  try {
    if (fs.existsSync(MODELS_DIR)) {
      const files = fs.readdirSync(MODELS_DIR);
      for (const file of files) {
        if (file.endsWith('.onnx')) {
          const key = file.replace('.onnx', '');
          const label = VOICE_NAMES[key] || key;
          if (!voices.some(v => v.label === label)) {
            voices.push({ key, label, file });
          }
        }
      }
    }
  } catch (e) {}

  if (voices.length === 0) {
    voices.push({ key: 'minhquang', label: 'Minh Quang', file: 'minhquang.onnx' });
  }
  return voices;
}

function getWorkspaceSettingsPath() {
  const folders = vscode.workspace.workspaceFolders;
  if (folders && folders.length > 0) {
    return path.join(folders[0].uri.fsPath, '.vscode', 'settings.json');
  }
  return null;
}

function getVoiceEnabled() {
  const settingsPath = getWorkspaceSettingsPath();
  if (settingsPath && fs.existsSync(settingsPath)) {
    try {
      const raw = fs.readFileSync(settingsPath, 'utf8');
      const settings = JSON.parse(raw);
      if (settings['antigravity.voiceEnabled'] !== undefined) {
        return Boolean(settings['antigravity.voiceEnabled']);
      }
    } catch (e) {}
  }
  return true;
}

function setVoiceEnabled(enabled) {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) return;

  const vscodeDir = path.join(folders[0].uri.fsPath, '.vscode');
  if (!fs.existsSync(vscodeDir)) {
    fs.mkdirSync(vscodeDir, { recursive: true });
  }

  const settingsPath = path.join(vscodeDir, 'settings.json');
  let settings = {};
  if (fs.existsSync(settingsPath)) {
    try {
      settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
    } catch (e) {
      settings = {};
    }
  }

  settings['antigravity.voiceEnabled'] = Boolean(enabled);
  fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2), 'utf8');
}

function getCurrentVoiceKey(availableVoices) {
  const settingsPath = getWorkspaceSettingsPath();
  if (settingsPath && fs.existsSync(settingsPath)) {
    try {
      const raw = fs.readFileSync(settingsPath, 'utf8');
      const settings = JSON.parse(raw);
      if (settings['antigravity.voice']) {
        return settings['antigravity.voice'];
      }
    } catch (e) {}
  }
  return availableVoices[0].key;
}

function saveVoiceKey(key) {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) return;

  const vscodeDir = path.join(folders[0].uri.fsPath, '.vscode');
  if (!fs.existsSync(vscodeDir)) {
    fs.mkdirSync(vscodeDir, { recursive: true });
  }

  const settingsPath = path.join(vscodeDir, 'settings.json');
  let settings = {};
  if (fs.existsSync(settingsPath)) {
    try {
      settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
    } catch (e) {
      settings = {};
    }
  }

  settings['antigravity.voice'] = key;
  fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2), 'utf8');
}

let statusMuteItem;
let statusVoiceItem;

function updateStatusBar(voice, isEnabled) {
  if (!statusMuteItem) {
    statusMuteItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 106);
    statusMuteItem.command = 'antigravityVoice.toggleVoice';
  }

  if (!statusVoiceItem) {
    statusVoiceItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 105);
    statusVoiceItem.command = 'antigravityVoice.selectVoice';
    statusVoiceItem.tooltip = 'Nhấp chuột để đổi giọng đọc cho dự án này';
  }

  const enabled = (isEnabled !== undefined) ? isEnabled : getVoiceEnabled();
  statusVoiceItem.text = voice.label;

  if (enabled) {
    statusMuteItem.text = `$(unmute)`;
    statusMuteItem.tooltip = `Giọng đọc đang BẬT - Nhấp vào đây để TẮT nhanh`;
    statusVoiceItem.tooltip = `Giọng đọc: ${voice.label} - Nhấp để đổi giọng`;
  } else {
    statusMuteItem.text = `$(mute)`;
    statusMuteItem.tooltip = `Giọng đọc đang TẮT - Nhấp vào đây để BẬT lại`;
    statusVoiceItem.tooltip = `Giọng đọc đang tắt (${voice.label}) - Nhấp để đổi giọng`;
  }

  statusMuteItem.show();
  statusVoiceItem.show();
}

function downloadWithPython(onnxUrl, onnxDest, jsonUrl, jsonDest, onProgress) {
  return new Promise((resolve, reject) => {
    const pyScript = `
import urllib.request, sys, os

def dl(url, dest, is_model=False):
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp, open(dest, 'wb') as f:
        total = int(resp.headers.get('content-length', 0))
        done = 0
        buf = 1024 * 1024
        while True:
            chunk = resp.read(buf)
            if not chunk: break
            f.write(chunk)
            done += len(chunk)
            if is_model and total > 0:
                pct = int((done / total) * 100)
                sys.stdout.write(f"PROGRESS:{pct}\\n")
                sys.stdout.flush()

dl(r"""${jsonUrl}""", r"""${jsonDest}""", False)
dl(r"""${onnxUrl}""", r"""${onnxDest}""", True)
sys.stdout.write("ALL_DONE\\n")
sys.stdout.flush()
`;

    const proc = spawn('python', ['-c', pyScript], {
      windowsHide: true,
      env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' }
    });

    proc.stdout.on('data', (data) => {
      const text = data.toString('utf-8');
      const lines = text.split('\n');
      for (const line of lines) {
        const l = line.trim();
        if (l.startsWith('PROGRESS:')) {
          const pct = parseInt(l.replace('PROGRESS:', ''), 10);
          if (!isNaN(pct)) onProgress(pct);
        }
      }
    });

    proc.on('close', (code) => {
      if (code === 0 && fs.existsSync(onnxDest) && fs.existsSync(jsonDest)) {
        resolve();
      } else {
        reject(new Error(`Mã lỗi tải: ${code}`));
      }
    });

    proc.on('error', reject);
  });
}

async function handleDownloadVoice() {
  const downloaded = getDownloadedVoices();
  const availableToDownload = CLOUD_VOICES.filter(
    cv => !downloaded.some(dv => dv.key === cv.key || dv.label === cv.label)
  );

  if (availableToDownload.length === 0) {
    vscode.window.showInformationMessage('Tất cả các giọng đọc trong kho đều đã được tải về máy!');
    return;
  }

  const items = availableToDownload.map(v => ({
    label: v.label,
    description: v.desc,
    voice: v
  }));

  const chosen = await vscode.window.showQuickPick(items, {
    placeHolder: 'Chọn giọng đọc muốn tải về máy'
  });

  if (!chosen) return;

  const v = chosen.voice;
  const onnxUrl = `https://huggingface.co/doof-ferb/nghitts-copy/resolve/main/piper-tts/${v.file}`;
  const jsonUrl = 'https://huggingface.co/doof-ferb/nghitts-copy/resolve/main/piper-tts/config.json';

  const onnxDest = path.join(MODELS_DIR, v.file);
  const jsonDest = path.join(MODELS_DIR, `${v.file}.json`);

  await vscode.window.withProgress({
    location: vscode.ProgressLocation.Notification,
    title: `Đang tải giọng đọc ${v.label}...`,
    cancellable: false
  }, async (progress) => {
    try {
      progress.report({ message: 'Bắt đầu kết nối...' });
      let lastPct = 0;
      await downloadWithPython(onnxUrl, onnxDest, jsonUrl, jsonDest, (pct) => {
        const inc = pct - lastPct;
        if (inc > 0) {
          progress.report({ increment: inc, message: `Đang tải mô hình: ${pct}%` });
          lastPct = pct;
        }
      });

      saveVoiceKey(v.key);
      updateStatusBar({ key: v.key, label: v.label });
      vscode.window.showInformationMessage(`Đã tải thành công và kích hoạt giọng đọc: ${v.label}!`);
    } catch (err) {
      vscode.window.showErrorMessage(`Lỗi khi tải giọng đọc: ${err.message}`);
    }
  });
}

function activate(context) {
  const selectVoiceCommand = vscode.commands.registerCommand('antigravityVoice.selectVoice', async () => {
    const availableVoices = getDownloadedVoices();
    const currentKey = getCurrentVoiceKey(availableVoices);
    const isEnabled = getVoiceEnabled();

    const items = [];

    // Tùy chọn Bật / Tắt ở đầu danh sách
    if (isEnabled) {
      items.push({
        label: '$(mute) Tắt giọng đọc (Mute)',
        description: 'Tạm ngưng thông báo giọng nói khi AI hoàn thành',
        action: 'toggle_disable'
      });
    } else {
      items.push({
        label: '$(unmute) Bật lại giọng đọc (Unmute)',
        description: 'Kích hoạt lại giọng đọc thông báo',
        action: 'toggle_enable'
      });
    }

    items.push({
      label: '── Danh sách giọng đọc ──',
      kind: vscode.QuickPickItemKind.Separator
    });

    for (const v of availableVoices) {
      items.push({
        label: v.label,
        description: (v.key === currentKey || (v.label === 'Ngọc Huyền' && currentKey.includes('ngochuyen'))) ? '(Đang chọn)' : '',
        key: v.key,
        action: 'select_voice'
      });
    }

    items.push({
      label: '➕ Tải thêm giọng đọc mới...',
      description: 'Khám phá thêm các giọng đọc có sẵn trên kho',
      key: '__download__',
      action: 'download'
    });

    const currentVoice = availableVoices.find(v => v.key === currentKey) || availableVoices[0];

    const selected = await vscode.window.showQuickPick(items, {
      placeHolder: isEnabled ? `Giọng hiện tại: ${currentVoice.label} (Đang bật)` : 'Giọng đọc đang tắt'
    });

    if (selected) {
      if (selected.action === 'toggle_disable') {
        setVoiceEnabled(false);
        updateStatusBar(currentVoice, false);
        vscode.window.showInformationMessage('Đã tắt giọng đọc thông báo.');
      } else if (selected.action === 'toggle_enable') {
        setVoiceEnabled(true);
        updateStatusBar(currentVoice, true);
        vscode.window.showInformationMessage(`Đã bật lại giọng đọc: ${currentVoice.label}`);
      } else if (selected.action === 'download') {
        await handleDownloadVoice();
      } else if (selected.action === 'select_voice') {
        saveVoiceKey(selected.key);
        updateStatusBar(selected, isEnabled);
        vscode.window.showInformationMessage(`Đã chọn giọng đọc: ${selected.label}`);
      }
    }
  });

  const toggleVoiceCommand = vscode.commands.registerCommand('antigravityVoice.toggleVoice', () => {
    const availableVoices = getDownloadedVoices();
    const currentKey = getCurrentVoiceKey(availableVoices);
    const currentVoice = availableVoices.find(v => v.key === currentKey) || availableVoices[0];
    const isEnabled = getVoiceEnabled();

    const newState = !isEnabled;
    setVoiceEnabled(newState);
    updateStatusBar(currentVoice, newState);

    if (newState) {
      vscode.window.showInformationMessage(`Đã bật giọng đọc thông báo (${currentVoice.label}).`);
    } else {
      vscode.window.showInformationMessage('Đã tắt giọng đọc thông báo.');
    }
  });

  context.subscriptions.push(selectVoiceCommand);
  context.subscriptions.push(toggleVoiceCommand);

  const initialVoices = getDownloadedVoices();
  const currentKey = getCurrentVoiceKey(initialVoices);
  const currentVoice = initialVoices.find(v => v.key === currentKey) || initialVoices[0];
  updateStatusBar(currentVoice);

  if (statusMuteItem) {
    context.subscriptions.push(statusMuteItem);
  }
  if (statusVoiceItem) {
    context.subscriptions.push(statusVoiceItem);
  }
}

function deactivate() {
  if (statusMuteItem) {
    statusMuteItem.dispose();
  }
  if (statusVoiceItem) {
    statusVoiceItem.dispose();
  }
}

module.exports = {
  activate,
  deactivate
};
