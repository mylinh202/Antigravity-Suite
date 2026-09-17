/**
 * Enforce Rules for Antigravity PreInvocation Hook (Global)
 * Runs before each model invocation across ALL projects.
 * Injects core instructions and stops lingering speech playback for the current workspace only.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');

function getWorkspaceKey(rawInput) {
  let wsName = '';
  if (rawInput) {
    try {
      const payload = JSON.parse(rawInput);
      if (payload.workspacePaths && payload.workspacePaths.length > 0) {
        wsName = path.basename(payload.workspacePaths[0]);
      } else if (payload.cwd) {
        wsName = path.basename(payload.cwd);
      }
    } catch (e) {}
  }
  if (!wsName) {
    wsName = path.basename(process.cwd());
  }
  return wsName ? wsName.toLowerCase().replace(/[^a-z0-9]/g, '_') : 'default';
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
      }
    } catch (e) {}
    try {
      fs.unlinkSync(pidFile);
    } catch (e) {}
  }

  // Dọn tệp wav tạm của workspace nếu còn sót
  const tempWav = path.join(os.tmpdir(), `voice_${wsKey}.wav`);
  if (fs.existsSync(tempWav)) {
    try { fs.unlinkSync(tempWav); } catch (e) {}
  }
}

function main() {
  let rawInput = '';
  try {
    if (!process.stdin.isTTY) {
      rawInput = fs.readFileSync(0, 'utf-8');
    }
  } catch (e) {}

  const wsKey = getWorkspaceKey(rawInput);
  killPreviousSpeech(wsKey);

  const reminder = "TRỌNG TÂM: Tuân thủ 9 luật cốt lõi. Trước khi sửa code phải tóm tắt yêu cầu & duyệt kế hoạch. Kiểm chứng trước khi khẳng định, test đỏ trước khi xanh, DB an toàn, không mở chồng port server. Mở đầu bằng khối trích dẫn (>) thuần Việt tự nhiên, đi thẳng vào trọng tâm kỹ thuật (nguyên nhân, tệp/hàm can thiệp, kết quả test, nơi nghiệm thu), không dùng gạch đầu dòng trong (>), không rào đón sáo rỗng. Độ dài linh hoạt theo nội dung thực chất để nghe loa là hiểu ngay. Thân bài dưới bắt buộc dùng (*), đánh số, chia mục trực quan, cấm viết văn xuôi dồn cục. Hạn chế tối đa từ tiếng Anh.";

  const output = {
    injectSteps: [
      {
        ephemeralMessage: reminder
      }
    ]
  };

  process.stdout.write(JSON.stringify(output));
}

try {
  main();
} catch (err) {
  process.stdout.write(JSON.stringify({
    injectSteps: [
      {
        ephemeralMessage: "TRỌNG TÂM: Tuân thủ 9 luật cốt lõi. Trước khi sửa code phải tóm tắt yêu cầu & duyệt kế hoạch. Mở đầu bằng khối trích dẫn (>) thuần Việt tự nhiên, đi thẳng vào dữ kiện kỹ thuật thực chất, không rào đón sáo rỗng."
      }
    ]
  }));
}
