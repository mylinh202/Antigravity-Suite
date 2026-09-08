/**
 * Antigravity Stop Hook (Global)
 * Instant Offline Voice Notification via Piper Neural TTS
 * Completely isolated per workspace: no shared PID, no shared WAV, auto-clean temporary files.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn, spawnSync } = require('child_process');

const LOG_FILE = path.join(__dirname, 'voice_notify.log');
const MODELS_DIR = path.join(os.homedir(), '.gemini', 'models', 'piper');

// =========================================================================
// DANH BẠ GIỌNG ĐỌC THEO TÊN DỰ ÁN (PHƯƠNG ÁN 2)
// Danh sách voice key:
// - Đã có trên máy: minhquang, ngochuyennew, duyoryx, taian, thientam, ngocngan
// - Kho trực tuyến: banmai, minhthu, vietthao3886, tranthanh3870, manhdung, maiphuong, phuongtrang, mytam2794, deepman3909
// =========================================================================
const WORKSPACE_VOICES = {
  'csa-cms-bangiaohuongso2': 'ngochuyennew',
  'CSA-CMS': 'minhquang',
  'lms-html-kit': 'duyoryx',
  'Chat': 'taian'
};

const DEFAULT_VOICE = 'minhquang';

function log(msg) {
  try {
    const time = new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
    fs.appendFileSync(LOG_FILE, `[${time}] ${msg}\n`, 'utf-8');
  } catch (e) {}
}

function getWorkspaceKey(workspaceName) {
  return workspaceName ? workspaceName.toLowerCase().replace(/[^a-z0-9]/g, '_') : 'default';
}

function killPreviousSpeech(wsKey) {
  const pidFile = path.join(__dirname, `speech_${wsKey}.pid`);
  if (fs.existsSync(pidFile)) {
    try {
      const pid = parseInt(fs.readFileSync(pidFile, 'utf-8').trim(), 10);
      if (pid && !isNaN(pid)) {
        if (process.platform === 'win32') {
          spawnSync('taskkill', ['/F', '/T', '/PID', pid.toString()], {
            stdio: 'ignore',
            windowsHide: true
          });
        } else {
          try {
            process.kill(-pid, 'SIGKILL');
          } catch (e) {
            try { process.kill(pid, 'SIGKILL'); } catch (e2) {}
          }
        }
        log(`[${wsKey}] Killed previous speech PID: ${pid}`);
      }
    } catch (e) {}
    try {
      fs.unlinkSync(pidFile);
    } catch (e) {}
  }

  // Xóa tệp âm thanh tạm cũ nếu có
  const tempWav = path.join(os.tmpdir(), `voice_${wsKey}.wav`);
  if (fs.existsSync(tempWav)) {
    try { fs.unlinkSync(tempWav); } catch (e) {}
  }
}

function resolveVoiceModel(workspacePath, workspaceName) {
  let chosenVoice = '';

  // 1. Ưu tiên đọc cấu hình riêng của workspace (.vscode/settings.json)
  if (workspacePath && fs.existsSync(workspacePath)) {
    const settingsFile = path.join(workspacePath, '.vscode', 'settings.json');
    if (fs.existsSync(settingsFile)) {
      try {
        const settings = JSON.parse(fs.readFileSync(settingsFile, 'utf8'));
        if (settings['antigravity.voice']) {
          chosenVoice = settings['antigravity.voice'].trim();
          log(`[${workspaceName}] Read voice setting from workspace: ${chosenVoice}`);
        }
      } catch (e) {}
    }
  }

  // 2. Tra cứu theo danh bạ dự án
  if (!chosenVoice && workspaceName) {
    const wsLower = workspaceName.toLowerCase().replace(/[_-]/g, '');
    for (const [key, voice] of Object.entries(WORKSPACE_VOICES)) {
      const keyLower = key.toLowerCase().replace(/[_-]/g, '');
      if (wsLower === keyLower || wsLower.includes(keyLower)) {
        chosenVoice = voice;
        break;
      }
    }
  }

  if (!chosenVoice) {
    chosenVoice = DEFAULT_VOICE;
  }

  let voiceFileName = chosenVoice;
  if ((chosenVoice === 'ngochuyen' || chosenVoice === 'ngoc_huyen') && !fs.existsSync(path.join(MODELS_DIR, 'ngochuyen.onnx'))) {
    voiceFileName = 'ngochuyennew';
  }

  const targetPath = path.join(MODELS_DIR, `${voiceFileName}.onnx`);
  if (fs.existsSync(targetPath)) {
    log(`[${workspaceName}] Resolved model: ${chosenVoice} (${targetPath})`);
    return targetPath;
  }

  // Fallback về default voice
  const defaultPath = path.join(MODELS_DIR, `${DEFAULT_VOICE}.onnx`);
  if (fs.existsSync(defaultPath)) {
    return defaultPath;
  }

  // Fallback về bất kỳ file onnx nào có sẵn
  try {
    if (fs.existsSync(MODELS_DIR)) {
      const files = fs.readdirSync(MODELS_DIR);
      const onnx = files.find(f => f.endsWith('.onnx'));
      if (onnx) {
        return path.join(MODELS_DIR, onnx);
      }
    }
  } catch (e) {}

  return null;
}

function cleanForSpeech(raw) {
  if (!raw) return '';
  return raw
    .replace(/^[>*-]\s*/gm, '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/https?:\/\/\S+/gi, ' ')
    .replace(/file:\/\/\S+/gi, ' ')
    .replace(/[a-zA-Z]:\\[^\s]+/g, ' ')
    .replace(/[a-zA-Z]:\/[^\s]+/g, ' ')
    .replace(/\b\S+\.(js|ts|tsx|jsx|json|md|wav|html|css|py|sh|log)\b/gi, ' ')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/[#*_~>|{}\[\]()=+\\@$%^&/]/g, ' ')
    .replace(/---+/g, ' ')
    .replace(/[:\-–—]/g, ', ')
    .replace(/\r?\n+/g, '. ')
    .replace(/\bAPI\b/gi, 'A P I')
    .replace(/\bIDE\b/gi, 'I D E')
    .replace(/\bUI\b/gi, 'giao diện')
    .replace(/\bDB\b/gi, 'cơ sở dữ liệu')
    .replace(/\bFE\b/gi, 'phía người dùng')
    .replace(/\bBE\b/gi, 'phía máy chủ')
    .replace(/\bBug\b/gi, 'lỗi')
    .replace(/\bTest\b/gi, 'kiểm tra')
    .replace(/\bHook\b/gi, 'bộ kích hoạt')
    .replace(/\bCode\b/gi, 'mã nguồn')
    .replace(/\s+/g, ' ')
    .replace(/\s+([.,!?])/g, '$1')
    .replace(/([.,!?])\1+/g, '$1')
    .replace(/,\s*\./g, '.')
    .replace(/\.\s*\./g, '.')
    .replace(/^[,.\s]+/, '')
    .trim();
}

function extractSummaryBlock(content) {
  if (!content) return 'Em đã hoàn thành xong công việc rồi ạ!';

  // 1. Quét toàn bộ khối trích dẫn mở đầu bắt đầu bằng dấu >
  const trimmed = content.trim();
  if (trimmed.startsWith('>')) {
    const lines = trimmed.split('\n');
    const quoteLines = [];
    for (const line of lines) {
      const l = line.trim();
      if (l.startsWith('>')) {
        const text = l.replace(/^>\s*/, '').trim();
        if (text && !text.toLowerCase().includes('tóm tắt nội dung')) {
          quoteLines.push(text);
        }
      } else if (l === '') {
        if (quoteLines.length > 0) break;
      } else {
        break;
      }
    }

    if (quoteLines.length > 0) {
      const combined = quoteLines.join('. ');
      const cleaned = cleanForSpeech(combined);
      if (cleaned.length > 10) {
        log(`Extracted leading blockquote (${cleaned.length} chars, ${quoteLines.length} lines)`);
        return cleaned;
      }
    }
  }

  // 2. Dự phòng: Tìm khối Tóm tắt nếu có
  const regex = /(?:>|#|\*)*\s*Tóm tắt[^\n]*\n((?:>?[^\n]+\n?){1,6})/i;
  const match = content.match(regex);
  if (match && match[1]) {
    const rawLines = match[1].split('\n')
      .map(l => l.replace(/^>\s*/, '').trim())
      .filter(l => l && !l.startsWith('#') && !l.startsWith('---'));
    const combined = rawLines.join('. ');
    const cleaned = cleanForSpeech(combined);
    if (cleaned.length > 15) {
      log(`Extracted structured summary (${cleaned.length} chars)`);
      return cleaned;
    }
  }

  // 3. Dự phòng: Câu đầu tiên
  const generalClean = cleanForSpeech(content);
  if (generalClean.length > 0) {
    const firstSentence = generalClean.match(/^[^.!?\n]+[.!?]/);
    const fallback = firstSentence ? firstSentence[0] : generalClean.slice(0, 150);
    log(`Fallback summary (${fallback.length} chars)`);
    return fallback;
  }

  return 'Em đã hoàn thành xong công việc rồi ạ!';
}

function extractContentFromTranscript(transcriptPath) {
  const defaultMessage = 'Em đã hoàn thành xong công việc rồi ạ!';
  if (!transcriptPath || !fs.existsSync(transcriptPath)) {
    return defaultMessage;
  }

  try {
    const content = fs.readFileSync(transcriptPath, 'utf-8');
    const lines = content.trim().split('\n');
    
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i].trim();
      if (!line) continue;
      try {
        const item = JSON.parse(line);
        if (
          item.source === 'MODEL' &&
          item.type === 'PLANNER_RESPONSE' &&
          (!item.tool_calls || item.tool_calls.length === 0) &&
          item.content &&
          typeof item.content === 'string'
        ) {
          return extractSummaryBlock(item.content);
        }
      } catch (e) {}
    }
  } catch (err) {
    log(`Error reading transcript: ${err.message}`);
  }

  return defaultMessage;
}

function speakWithPiper(text, modelPath, wsKey) {
  if (!modelPath || !fs.existsSync(modelPath)) {
    log(`[${wsKey}] Model not found: ${modelPath}`);
    return;
  }

  // Tệp âm thanh tạm cố định riêng cho từng workspace (chỉ 1 tệp duy nhất, tự dọn dẹp sau khi phát)
  const tempWav = path.join(os.tmpdir(), `voice_${wsKey}.wav`);
  const pidFile = path.join(__dirname, `speech_${wsKey}.pid`);

  log(`[${wsKey}] Synthesizing with model ${path.basename(modelPath)}: ${text.slice(0, 80)}...`);

  const res = spawnSync('python', [
    '-m', 'piper',
    '-m', modelPath,
    '--output_file', tempWav
  ], {
    input: text,
    encoding: 'utf-8',
    env: {
      ...process.env,
      PYTHONUTF8: '1',
      PYTHONIOENCODING: 'utf-8'
    },
    timeout: 15000,
    windowsHide: true
  });

  if (res.status !== 0 || !fs.existsSync(tempWav)) {
    log(`[${wsKey}] Piper synthesis failed with status: ${res.status}`);
    return;
  }

  log(`[${wsKey}] Playing in background and auto-cleaning files when done...`);

  // Phát âm thanh nền tương thích đa nền tảng (tự động xóa tệp WAV và PID sau khi phát xong)
  let player;
  if (process.platform === 'win32') {
    const playPyCode = [
      "import winsound, os",
      `wav = r'${tempWav}'`,
      `pid_f = r'${pidFile}'`,
      "try:",
      "    winsound.PlaySound(wav, winsound.SND_FILENAME)",
      "finally:",
      "    try: os.remove(wav)",
      "    except: pass",
      "    try: os.remove(pid_f)",
      "    except: pass"
    ].join('\n');

    player = spawn('python', ['-c', playPyCode], {
      detached: true,
      stdio: 'ignore',
      windowsHide: true
    });
  } else if (process.platform === 'darwin') {
    // macOS: afplay có sẵn trong hệ thống
    const playSh = `afplay "${tempWav}"; rm -f "${tempWav}" "${pidFile}"`;
    player = spawn('sh', ['-c', playSh], {
      detached: true,
      stdio: 'ignore'
    });
  } else {
    // Linux: paplay hoặc aplay
    const playSh = `(which paplay >/dev/null 2>&1 && paplay "${tempWav}" || aplay "${tempWav}"); rm -f "${tempWav}" "${pidFile}"`;
    player = spawn('sh', ['-c', playSh], {
      detached: true,
      stdio: 'ignore'
    });
  }

  if (player.pid) {
    fs.writeFileSync(pidFile, player.pid.toString(), 'utf-8');
    log(`[${wsKey}] Started player PID: ${player.pid}`);
  }
  player.unref();
}

function main() {
  let transcriptPath = '';
  let workspaceName = '';
  let workspacePath = '';

  try {
    if (!process.stdin.isTTY) {
      const rawInput = fs.readFileSync(0, 'utf-8');
      if (rawInput) {
        try {
          const payload = JSON.parse(rawInput);
          transcriptPath = payload.transcriptPath || '';
          
          if (payload.workspacePaths && Array.isArray(payload.workspacePaths) && payload.workspacePaths.length > 0) {
            workspacePath = payload.workspacePaths[0];
            workspaceName = path.basename(workspacePath);
          } else if (payload.cwd) {
            workspacePath = payload.cwd;
            workspaceName = path.basename(workspacePath);
          }
        } catch (e) {}
      }
    }
  } catch (err) {}

  if (!workspaceName) {
    workspaceName = path.basename(process.cwd());
  }

  const wsKey = getWorkspaceKey(workspaceName);
  log(`[${wsKey}] Stop hook triggered for workspace: ${workspaceName}`);

  killPreviousSpeech(wsKey);

  const modelPath = resolveVoiceModel(workspacePath, workspaceName);
  const textToSpeak = extractContentFromTranscript(transcriptPath);

  log(`[${wsKey}] Final text to speak: ${textToSpeak}`);
  speakWithPiper(textToSpeak, modelPath, wsKey);
}

try {
  main();
} catch (err) {
  log(`Main execution error: ${err.message}`);
} finally {
  process.stdout.write(JSON.stringify({ decision: "approve" }));
}
