import os
import asyncio
import edge_tts
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# 網頁前端介面 (HTML + 簡易 JS 請求 + 語速選擇)
HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python P仔雲端聽書神器</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f4f6f9; color: #333; }
        .card { background: white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-top: 10px; }
        h1 { color: #1a73e8; font-size: 22px; margin-top: 0; text-align: center; }
        label { font-weight: bold; display: block; margin-top: 15px; margin-bottom: 5px; font-size: 14px; color: #555; }
        textarea { width: 100%; height: 140px; padding: 12px; border: 1px solid #ddd; border-radius: 10px; font-size: 16px; box-sizing: border-box; resize: vertical; }
        select { width: 100%; padding: 10px; border-radius: 10px; border: 1px solid #ddd; font-size: 16px; box-sizing: border-box; background: #fff; margin-bottom: 10px; }
        .btn { width: 100%; background: #1a73e8; color: white; border: none; padding: 15px; font-size: 18px; font-weight: bold; border-radius: 10px; cursor: pointer; text-align: center; margin-top: 20px; }
        .btn:active { transform: scale(0.98); opacity: 0.9; }
        #status { text-align: center; margin-top: 15px; font-weight: bold; color: #28a745; min-height: 24px; }
        audio { width: 100%; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🎧 Python × Edge-TTS 雲端聽書神器</h1>
        
        <label>請隨時貼上或修改稿件 / 文字：</label>
        <textarea id="textInput" placeholder="請在此輸入要讀出嚟嘅廣東話文字...">喺耶和華上帝所造嘅各種動物中……蛇最狡猾嘅……</textarea>
        
        <label>選擇微軟雲端索索聲線：</label>
        <select id="voiceSelect">
            <option value="zh-HK-WanLungNeural">P仔 (WanLung - 雲龍男聲)</option>
            <option value="zh-HK-HiuMaanNeural">P女 (HiuMaan - 曉曼女聲)</option>
        </select>

        <label>選擇朗讀語速：</label>
        <select id="rateSelect">
            <option value="-20%" selected>0.8x 經典極慢速 (黃金慢讀 -20%)</option>
            <option value="-10%">0.9x 標準口語速 (-10%)</option>
            <option value="+0%">1.0x 原速 (+0%)</option>
        </select>

        <button class="btn" onclick="generateAudio()">🚀 雲端 AI 即時合成語音</button>
        <div id="status"></div>
        <audio id="audioPlayer" controls style="display:none;"></audio>
    </div>

    <script>
        async function generateAudio() {
            let text = document.getElementById('textInput').value;
            let voice = document.getElementById('voiceSelect').value;
            let rate = document.getElementById('rateSelect').value;
            let statusDiv = document.getElementById('status');
            let player = document.getElementById('audioPlayer');

            if (!text.trim()) {
                alert('請先輸入文字！');
                return;
            }

            statusDiv.innerText = '⏳ 正在呼叫微軟雲端 AI 產生靚聲中...';
            player.style.display = 'none';

            try {
                let response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'text=' + encodeURIComponent(text) + '&voice=' + encodeURIComponent(voice) + '&rate=' + encodeURIComponent(rate)
                });

                if (response.ok) {
                    let blob = await response.blob();
                    let audioUrl = URL.createObjectURL(blob);
                    player.src = audioUrl;
                    player.style.display = 'block';
                    player.play();
                    statusDiv.innerText = '✅ 雲端 AI 朗讀音訊合成完畢！';
                } else {
                    statusDiv.innerText = '⚠️ 合成失敗，請檢查後端日誌。';
                }
            } catch (err) {
                statusDiv.innerText = '⚠️ 連線發生錯誤：' + err;
            }
        }
    </script>
</body>
</html>
"""

class TTSHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

    def do_POST(self):
        if self.path == '/generate':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
            
            text = params.get('text', [''])[0]
            voice = params.get('voice', ['zh-HK-WanLungNeural'])[0]
            rate = params.get('rate', ['-20%'])[0] # 接收前端傳嚟嘅語速（預設 -20%）
            
            output_filename = "temp_web_audio.mp3"
            
            # 使用 edge_tts 非同步生成音檔，代入明仔要嘅語速
            async def run_tts():
                communicate = edge_tts.Communicate(text, voice, rate=rate)
                await communicate.save(output_filename)

            asyncio.run(run_tts())
            
            # 回傳生成的 mp3 畀前端網頁播放
            if os.path.exists(output_filename):
                self.send_response(200)
                self.send_header("Content-type", "audio/mpeg")
                self.end_headers()
                with open(output_filename, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(500)
                self.end_headers()

def run(server_class=HTTPServer, handler_class=TTSHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"🚀 P仔 Python 聽書網頁伺服器已啟動！")
    print(f"🔗 請在瀏覽器打開網址：http://localhost:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
