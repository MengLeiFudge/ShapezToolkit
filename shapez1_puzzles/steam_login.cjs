/* 使用游戏自带的 Electron Node 模式和 Greenworks 获取一代谜题 token。 */
"use strict";

const https = require("https");
const path = require("path");

const PREFIX = "SHAPEZ_AUTH_RESULT ";
const API_KEY = "d5c54aaa491f200709afff082c153ef2";
let finished = false;

/** 输出一次结构化结果；退出子进程以结束 Steam 会话和原生回调。 */
function finish(result) {
    if (finished) return;
    finished = true;
    clearTimeout(deadline);
    process.stdout.write(PREFIX + JSON.stringify(result) + "\n", () => {
        process.exit(result.ok ? 0 : 1);
    });
}

const deadline = setTimeout(() => {
    finish({ ok: false, error: "认证超过 45 秒，请检查 Steam 登录状态和网络。" });
}, 45000);

/** 在 Steam 票据仍有效时完成服务器登录，不将票据写入文件或日志。 */
function exchangeTicket(ticket) {
    const body = JSON.stringify({ token: ticket.toString("hex") });
    const request = https.request("https://api.shapez.io/v1/public/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(body),
            "x-api-key": API_KEY,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ShapezToolkit/1.0",
        },
    }, response => {
        const chunks = [];
        let size = 0;
        response.on("data", chunk => {
            size += chunk.length;
            if (size > 1024 * 1024) {
                response.destroy();
                finish({ ok: false, error: "认证响应超过大小限制。" });
                return;
            }
            chunks.push(chunk);
        });
        response.on("error", () => {
            finish({ ok: false, error: "认证响应接收失败，请检查网络。" });
        });
        response.on("end", () => {
            if (response.statusCode !== 200) {
                finish({ ok: false, error: `认证服务器返回 HTTP ${response.statusCode}。` });
                return;
            }
            let result;
            try {
                result = JSON.parse(Buffer.concat(chunks).toString("utf8"));
            } catch (_) {
                finish({ ok: false, error: "认证服务器没有返回有效 JSON。" });
                return;
            }
            if (!result || result.error || typeof result.token !== "string" || !result.token.trim()) {
                finish({ ok: false, error: "服务器未签发 token，请确认 Steam 账号拥有一代谜题 DLC。" });
                return;
            }
            finish({ ok: true, token: result.token.trim() });
        });
    });
    request.setTimeout(25000, () => {
        request.destroy();
        finish({ ok: false, error: "连接认证服务器超时，请检查网络。" });
    });
    request.on("error", () => {
        finish({ ok: false, error: "无法连接认证服务器，请检查网络。" });
    });
    request.end(body);
}

try {
    // 必须由游戏自带的 Electron 执行，以匹配 Greenworks 原生模块的 ABI。
    const greenworks = require(path.join(process.cwd(),
        "resources/app.asar.unpacked/node_modules/shapez.io-private-artifacts/steam/greenworks.js"));
    if (!greenworks.init()) {
        finish({ ok: false, error: "Steam 初始化失败，请先登录 Steam。" });
    } else {
        greenworks.getAuthSessionTicket(result => {
            if (!result || !Buffer.isBuffer(result.ticket) || result.ticket.length === 0) {
                finish({ ok: false, error: "Steam 未返回有效认证票据。" });
                return;
            }
            exchangeTicket(result.ticket);
        }, () => {
            finish({ ok: false, error: "Steam 认证票据获取失败，请检查账号和连接状态。" });
        });
    }
} catch (_) {
    finish({ ok: false, error: "无法加载或初始化游戏的 Steam 组件，请确认游戏安装完整且 Steam 已登录。" });
}
