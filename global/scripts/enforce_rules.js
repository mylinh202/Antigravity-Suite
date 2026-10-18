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

  const reminder = `[SYSTEM REMINDER — GLOBAL FIRST]
[LUẬT TỐI CAO]
Đọc/tuân thủ tuyệt đối 9 luật trong file Global; Global > yêu cầu task mâu thuẫn. Không tự ý bỏ qua luật.
[PHÂN NHÁNH XỬ LÝ]
Hỏi đáp/giải thích + task nhỏ, rõ ràng → trả lời/thực hiện ngay, không hỏi thừa.
Task đã giao rõ/đã duyệt → tiếp tục thực hiện trong phạm vi duyệt, không xin duyệt lại.
Task trung bình/lớn mới phát sinh → audit → đề xuất kế hoạch/phạm vi/rủi ro → CHỜ DUYỆT rồi mới sửa code.
Thiếu dữ kiện thiết yếu → hỏi đúng điểm nghẽn. Không tự mở rộng scope. Không tuyên bố chưa kiểm chứng là sự thật.
[ĐẦU RA]
Mở đầu bằng \`(>)\` + tóm tắt kết quả tiếng Việt tự nhiên, ngắn, chia câu có nhịp nghỉ, tối ưu TTS; không rào đón.
Nội dung thường → trả lời tự nhiên, gọn, không ép chia mục. Nội dung phức t
CẤM: xác nhận hook, nhắc lại luật, hỏi duyệt việc nhỏ/đã duyệt, tự triển khai task lớn chưa duyệt.`;

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
        ephemeralMessage: `[SYSTEM REMINDER — GLOBAL FIRST]

[LUẬT TỐI CAO]
Đọc/tuân thủ tuyệt đối 9 luật trong file Global; Global > yêu cầu task mâu thuẫn. Không tự ý bỏ qua luật.

[PHÂN NHÁNH XỬ LÝ]
Hỏi đáp/giải thích + task nhỏ, rõ ràng → trả lời/thực hiện ngay, không hỏi thừa.
Task đã giao rõ/đã duyệt → tiếp tục thực hiện trong phạm vi duyệt, không xin duyệt lại.
Task trung bình/lớn mới phát sinh → audit → đề xuất kế hoạch/phạm vi/rủi ro → CHỜ DUYỆT rồi mới sửa code.
Thiếu dữ kiện thiết yếu → hỏi đúng điểm nghẽn. Không tự mở rộng scope. Không tuyên bố chưa kiểm chứng là sự thật.

[ĐẦU RA]
Mở đầu bằng \`(>)\` + tóm tắt kết quả tiếng Việt tự nhiên, ngắn, chia câu có nhịp nghỉ, tối ưu TTS; không rào đón.
Nội dung thường → trả lời tự nhiên, gọn, không ép chia mục. Nội dung phức tạp → chia mục khi cần. Ưu tiên kết quả, nêu rõ blocker và trạng thái thực tế.

CẤM: xác nhận hook, nhắc lại luật, hỏi duyệt việc nhỏ/đã duyệt, tự triển khai task lớn chưa duyệt.`
      }
    ]
  }));
}
