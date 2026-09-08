const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const os = require('os');
const readline = require('readline');

let statusBarItem;
let intervalTimer;

const CYCLE_TARGET_KB = 500;        // Chu kỳ context lý tưởng (500KB)
const ALERT_THRESHOLD_KB = 380;     // Mốc cảnh báo 75% (~380KB)

function activate(context) {
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'antigravityContext.showDetails';
    context.subscriptions.push(statusBarItem);

    const showDetailsCommand = vscode.commands.registerCommand('antigravityContext.showDetails', async () => {
        const stats = await getActiveContextStats();
        const pct = stats.percent;
        const activeKB = stats.activeKB;
        const totalKB = stats.totalKB;
        const wsName = stats.workspaceName || 'Không xác định';

        let msg = `[Workspace: ${wsName}]\nContext Active: ${activeKB} KB (~${pct}% chu kỳ, ~${stats.tokens} tokens).\nTổng lịch sử phiên: ${totalKB} KB (Cách Checkpoint gần nhất: ${stats.stepsSinceCheckpoint} steps).`;
        if (pct >= 75) {
            msg += `\n\n⚠️ CẢNH BÁO: Đã đạt ${pct}% (${activeKB}KB) chu kỳ! Khuyến nghị Compact hoặc New Chat để giữ vững trọng tâm 9 luật cốt lõi.`;
        } else {
            msg += `\n\n✅ Trạng thái: An toàn, model phản hồi ở độ nhạy bén cao nhất.`;
        }

        const choice = await vscode.window.showInformationMessage(
            msg,
            'Mở phiên mới (New Chat)',
            'Xem file transcript',
            'Đóng'
        );

        if (choice === 'Mở phiên mới (New Chat)') {
            vscode.commands.executeCommand('workbench.action.chat.newChat');
        } else if (choice === 'Xem file transcript' && stats.filePath) {
            const doc = await vscode.workspace.openTextDocument(stats.filePath);
            await vscode.window.showTextDocument(doc);
        }
    });
    context.subscriptions.push(showDetailsCommand);

    updateContextStatus();
    intervalTimer = setInterval(updateContextStatus, 3000);

    statusBarItem.show();
}

/**
 * Kiểm tra xem 4KB đầu của file transcript có thuộc về workspace đang mở hay không
 */
function isTranscriptBelongsToWorkspace(filePath, workspacePath, workspaceName) {
    try {
        const fd = fs.openSync(filePath, 'r');
        const buffer = Buffer.alloc(4096);
        const bytesRead = fs.readSync(fd, buffer, 0, 4096, 0);
        fs.closeSync(fd);

        const headerText = buffer.toString('utf8', 0, bytesRead).toLowerCase();
        const wsPathNorm = workspacePath ? workspacePath.toLowerCase().replace(/\\/g, '/') : null;
        const wsNameNorm = workspaceName ? workspaceName.toLowerCase() : null;

        if (wsPathNorm && headerText.includes(wsPathNorm)) return true;
        if (workspacePath && headerText.includes(workspacePath.toLowerCase())) return true;
        if (wsNameNorm && headerText.includes(wsNameNorm)) return true;

        return false;
    } catch (e) {
        return false;
    }
}

/**
 * Tính Active Context chính xác từ CHECKPOINT gần nhất (dựa trên type: "CHECKPOINT")
 */
async function calculateActiveContextBytes(filePath) {
    let activeBytes = 0;
    let totalBytes = 0;
    let stepsSinceCheckpoint = 0;

    try {
        const fileStream = fs.createReadStream(filePath);
        const rl = readline.createInterface({ input: fileStream, crlfDelay: Infinity });

        for await (const line of rl) {
            if (!line.trim()) continue;
            const lineBytes = Buffer.byteLength(line, 'utf8');
            totalBytes += lineBytes;

            // Chỉ match đúng định dạng JSON type CHECKPOINT của hệ thống Antigravity
            if (line.includes('"type":"CHECKPOINT"') || line.includes('"type": "CHECKPOINT"')) {
                activeBytes = lineBytes;
                stepsSinceCheckpoint = 0;
            } else {
                activeBytes += lineBytes;
                stepsSinceCheckpoint++;
            }
        }
        return { activeBytes, totalBytes, stepsSinceCheckpoint };
    } catch (e) {
        const fallbackSize = fs.existsSync(filePath) ? fs.statSync(filePath).size : 0;
        return { activeBytes: fallbackSize, totalBytes: fallbackSize, stepsSinceCheckpoint: 0 };
    }
}

async function getActiveContextStats() {
    const userProfile = os.homedir();
    const brainDir = path.join(userProfile, '.gemini', 'antigravity-ide', 'brain');

    const firstFolder = vscode.workspace.workspaceFolders?.[0];
    const currentWorkspacePath = firstFolder?.uri.fsPath || null;
    const currentWorkspaceName = firstFolder?.name || (currentWorkspacePath ? path.basename(currentWorkspacePath) : null);

    let targetTranscript = null;
    let maxMtime = 0;

    try {
        if (fs.existsSync(brainDir)) {
            const convs = fs.readdirSync(brainDir);
            
            // 1. Quét tìm các transcript khớp với workspace hiện tại
            for (const conv of convs) {
                const transcriptFile = path.join(brainDir, conv, '.system_generated', 'logs', 'transcript.jsonl');
                if (fs.existsSync(transcriptFile)) {
                    const stat = fs.statSync(transcriptFile);
                    
                    if (currentWorkspacePath) {
                        if (isTranscriptBelongsToWorkspace(transcriptFile, currentWorkspacePath, currentWorkspaceName)) {
                            if (stat.mtimeMs > maxMtime) {
                                maxMtime = stat.mtimeMs;
                                targetTranscript = transcriptFile;
                            }
                        }
                    } else {
                        if (stat.mtimeMs > maxMtime) {
                            maxMtime = stat.mtimeMs;
                            targetTranscript = transcriptFile;
                        }
                    }
                }
            }

            // 2. Dự phòng: Nếu chưa khớp được transcript nào, lấy file mới nhất
            if (!targetTranscript && convs.length > 0) {
                for (const conv of convs) {
                    const transcriptFile = path.join(brainDir, conv, '.system_generated', 'logs', 'transcript.jsonl');
                    if (fs.existsSync(transcriptFile)) {
                        const stat = fs.statSync(transcriptFile);
                        if (stat.mtimeMs > maxMtime) {
                            maxMtime = stat.mtimeMs;
                            targetTranscript = transcriptFile;
                        }
                    }
                }
            }
        }
    } catch (e) {}

    if (!targetTranscript || !fs.existsSync(targetTranscript)) {
        return { activeKB: 0, totalKB: 0, percent: 0, tokens: 0, stepsSinceCheckpoint: 0, workspaceName: currentWorkspaceName, filePath: null };
    }

    const { activeBytes, totalBytes, stepsSinceCheckpoint } = await calculateActiveContextBytes(targetTranscript);
    const activeKB = Math.round(activeBytes / 1024);
    const totalKB = Math.round(totalBytes / 1024);
    const tokens = Math.round(activeBytes / 3.5);
    const percent = Math.min(Math.round((activeKB / CYCLE_TARGET_KB) * 100), 100);

    return {
        activeKB,
        totalKB,
        percent,
        tokens,
        stepsSinceCheckpoint,
        workspaceName: currentWorkspaceName,
        filePath: targetTranscript
    };
}

async function updateContextStatus() {
    if (!statusBarItem) return;

    const stats = await getActiveContextStats();
    const pct = stats.percent;
    const activeKB = stats.activeKB;

    if (pct >= 75) {
        statusBarItem.text = `$(flame) Context: ${activeKB}KB [${pct}%]`;
        statusBarItem.color = '#ff4d4f';
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
        statusBarItem.tooltip = `⚠️ [${stats.workspaceName || 'Workspace'}] CẢNH BÁO CONTEXT 75% (${activeKB}KB)! Khuyến nghị Compact hoặc New Chat để giữ đúng trọng tâm Global Rule.`;
    } else if (pct >= 60) {
        statusBarItem.text = `$(warning) Context: ${activeKB}KB [${pct}%]`;
        statusBarItem.color = '#faad14';
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        statusBarItem.tooltip = `[${stats.workspaceName || 'Workspace'}] Context đang ở mức ${pct}% (${activeKB}KB). Sắp chạm mốc 75%.`;
    } else {
        statusBarItem.text = `$(database) Context: ${activeKB}KB [${pct}%]`;
        statusBarItem.color = undefined;
        statusBarItem.backgroundColor = undefined;
        statusBarItem.tooltip = `[${stats.workspaceName || 'Workspace'}] Context an toàn: ${activeKB}KB (${pct}%, ~${stats.tokens} tokens). Nhấp để xem chi tiết.`;
    }
}

function deactivate() {
    if (intervalTimer) clearInterval(intervalTimer);
    if (statusBarItem) statusBarItem.dispose();
}

module.exports = { activate, deactivate };
