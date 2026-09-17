from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# --- KONFIGURACE A DATOVÉ STRUKTURY ---
MAX_DISPLAYS = 6
MAX_CROSS_CHANNELS = 10

# Stavy pro běžné displeje (1. záložka)
visible_count = 3
display_queues = {f"Displej_0{i}": [] for i in range(1, MAX_DISPLAYS + 1)}
display_current = {f"Displej_0{i}": "00000000" for i in range(1, MAX_DISPLAYS + 1)}

# Stavy pro Text Wall (2. záložka)
text_wall_data = ""

# Stavy pro Cross-Server Hub (3. záložka)
# Uchovává aktuální poslano/přijato a počítadlo správně přenesených paketů pro ID 01 až 10
cross_channels = {
    f"{i:02d}": {
        "send_val": "00000000",
        "recv_val": "00000000",
        "last_status": "IDLE",
        "packets_count": 0
    } for i in range(1, MAX_CROSS_CHANNELS + 1)
}

# Logy (4. záložka)
logs = ["🚀 Server spuštěn a připraven pro Roblox spojení."]

def add_log(msg):
    global logs
    logs.insert(0, msg)
    if len(logs) > 50:
        logs.pop()

def char_to_binary(char):
    if len(char) == 1:
        return format(ord(char), '08b')
    return "00000000"

# --- HTML ŠABLONA ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Build Logic - Control & Cross Hub</title>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background-color: #0b0f19; color: #c9d1d9; padding: 25px 15px; }
        .container { max-width: 1000px; margin: 0 auto; }
        header { text-align: center; margin-bottom: 20px; }
        header h1 { font-size: 26px; color: #58a6ff; font-weight: 700; letter-spacing: 1px; }
        header p { color: #8b949e; font-size: 14px; margin-top: 5px; }
        
        /* Záložky (Tabs) */
        .nav-tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 1px solid #30363d; padding-bottom: 10px; justify-content: center; flex-wrap: wrap; }
        .tab-btn { background: #161b22; color: #8b949e; border: 1px solid #30363d; padding: 10px 18px; font-weight: 600; font-size: 14px; border-radius: 8px; cursor: pointer; transition: 0.2s; }
        .tab-btn:hover { background: #21262d; color: #f0f6fc; }
        .tab-btn.active { background: #1f6beb; color: #ffffff; border-color: #388bfd; }

        /* Specifické barvy záložek */
        .tab-btn.tab-hub { border-color: #39c5bb; color: #39c5bb; }
        .tab-btn.tab-hub:hover { background: #162c2b; color: #56edf3; }
        .tab-btn.tab-hub.active { background: #1b7c77; color: #ffffff; border-color: #56edf3; font-weight: 700; }

        .tab-btn.tab-logs { border-color: #d29922; color: #d29922; }
        .tab-btn.tab-logs:hover { background: #272115; color: #f2cc60; }
        .tab-btn.tab-logs.active { background: #d29922; color: #0d1117; border-color: #f2cc60; font-weight: 700; }

        .tab-btn.tab-setup { border-color: #a371f7; color: #a371f7; }
        .tab-btn.tab-setup:hover { background: #251e38; color: #d2a8ff; }
        .tab-btn.tab-setup.active { background: #8957e5; color: #ffffff; border-color: #d2a8ff; font-weight: 700; }

        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        .card-hub { border-color: #1b7c77; }
        .card-logs { border-color: #d29922; }
        .card-setup { border-color: #8957e5; }

        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }

        .displays-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 15px; }
        .status-display { text-align: center; padding: 15px; background: #0d1117; border-radius: 8px; border: 1px solid #21262d; }
        .disp-title { font-size: 14px; color: #58a6ff; font-weight: 600; margin-bottom: 5px; }
        .binary-out { font-family: 'Fira Code', monospace; font-size: 22px; color: #3fb950; letter-spacing: 2px; font-weight: 600; }

        .controls-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px; }
        .controls-header h2 { font-size: 16px; color: #f0f6fc; text-transform: uppercase; letter-spacing: 0.5px; }
        .btn-group { display: flex; gap: 8px; }

        h2 { font-size: 16px; color: #f0f6fc; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 0.5px; }
        
        select, input[type=text], textarea { width: 100%; padding: 12px 15px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #f0f6fc; font-family: 'Fira Code', monospace; font-size: 15px; margin-bottom: 12px; }
        select { font-family: 'Inter', sans-serif; cursor: pointer; }
        select:focus, input[type=text]:focus, textarea:focus { border-color: #58a6ff; outline: none; }

        button { width: 100%; padding: 12px; border-radius: 6px; border: none; font-weight: 600; font-size: 14px; cursor: pointer; transition: 0.2s; background: #238636; color: #ffffff; }
        button:hover { background: #2ea043; }
        .btn-add { background: #1f6beb; }
        .btn-add:hover { background: #388bfd; }
        .btn-remove { background: #21262d; border: 1px solid #30363d; color: #c9d1d9; }
        .btn-remove:hover { background: #30363d; color: #f0f6fc; }
        .btn-danger { background: #da3633; color: #fff; margin-top: 8px; }
        .btn-danger:hover { background: #f85149; }

        .log-container { background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 12px; height: 380px; overflow-y: auto; font-family: 'Fira Code', monospace; font-size: 13px; color: #8b949e; line-height: 1.6; }
        .log-entry { margin-bottom: 6px; border-bottom: 1px solid #161b22; padding-bottom: 4px; }

        /* Text Wall */
        .text-wall { width: 100%; height: 280px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px; font-family: 'Fira Code', monospace; color: #3fb950; font-size: 16px; resize: vertical; margin-bottom: 15px; word-break: break-all; }
        .wall-actions { display: flex; gap: 10px; }

        /* Cross-Server Hub Cards */
        .hub-card { background: #0d1117; border: 1px solid #21262d; border-radius: 10px; padding: 15px; margin-bottom: 15px; transition: 0.2s; }
        .hub-card:hover { border-color: #39c5bb; }
        .hub-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #161b22; padding-bottom: 8px; margin-bottom: 10px; font-size: 14px; font-weight: 600; color: #f0f6fc; }
        .hub-channel-tag { background: #1b7c77; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-family: 'Fira Code', monospace; }
        
        .hub-flow { display: flex; justify-content: space-between; align-items: center; gap: 10px; text-align: center; }
        .hub-node { flex: 1; background: #161b22; padding: 10px; border-radius: 6px; border: 1px solid #30363d; }
        .hub-node-title { font-size: 12px; color: #8b949e; margin-bottom: 4px; }
        .hub-arrow { color: #39c5bb; font-size: 18px; font-weight: bold; display: flex; flex-direction: column; align-items: center; gap: 2px; }
        .hub-arrow-status { font-size: 10px; color: #3fb950; text-transform: uppercase; letter-spacing: 0.5px; }

        /* Style pro Set-up záložku */
        .url-box { display: flex; gap: 10px; margin-bottom: 15px; }
        .url-box input { margin-bottom: 0; font-family: 'Fira Code', monospace; color: #3fb950; font-weight: 600; }
        .copy-btn { width: auto; padding: 0 20px; white-space: nowrap; background: #21262d; border: 1px solid #30363d; }
        .copy-btn:hover { background: #30363d; }

        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { text-align: left; padding: 10px; border-bottom: 1px solid #21262d; font-size: 14px; }
        th { color: #58a6ff; }
        code { font-family: 'Fira Code', monospace; background: #0d1117; padding: 2px 6px; border-radius: 4px; color: #f2cc60; border: 1px solid #30363d; }
    </style>
    <script>
        function openTab(tabName) {
            let tabs = document.getElementsByClassName('tab-content');
            let btns = document.getElementsByClassName('tab-btn');
            for (let t of tabs) t.classList.remove('active');
            for (let b of btns) b.classList.remove('active');
            
            document.getElementById(tabName).classList.add('active');
            event.currentTarget.classList.add('active');
        }

        function copyUrl(elementId) {
            let urlInput = document.getElementById(elementId);
            urlInput.select();
            document.execCommand('copy');
            alert('Adresa byla zkopírována do schránky!');
        }

        function copyTextWall() {
            let wall = document.getElementById('text-wall-area');
            wall.select();
            document.execCommand('copy');
            alert('Obsah Text Wall byl zkopírován!');
        }

        setInterval(async () => {
            try {
                let res = await fetch('/api/status');
                let data = await res.json();
                
                // 1. Aktualizace běžných displejů
                for (let i = 1; i <= 6; i++) {
                    let key = 'Displej_0' + i;
                    let binEl = document.getElementById('bin-d' + i);
                    let qEl = document.getElementById('queue-d' + i);
                    if (binEl) binEl.innerText = data.current_val[key] || "00000000";
                    if (qEl) qEl.innerText = data.queue_len[key] || 0;
                }
                
                // 2. Aktualizace Text Wall
                let wall = document.getElementById('text-wall-area');
                if (wall && document.activeElement !== wall) {
                    wall.value = data.text_wall;
                }

                // 3. Aktualizace Cross-Server Hubu
                for (let i = 1; i <= 10; i++) {
                    let idStr = (i < 10 ? '0' : '') + i;
                    let ch = data.cross_channels[idStr];
                    if (ch) {
                        let sendEl = document.getElementById('hub-send-' + idStr);
                        let recvEl = document.getElementById('hub-recv-' + idStr);
                        let countEl = document.getElementById('hub-count-' + idStr);
                        if (sendEl) sendEl.innerText = ch.send_val;
                        if (recvEl) recvEl.innerText = ch.recv_val;
                        if (countEl) countEl.innerText = ch.packets_count;
                    }
                }

                // 4. Aktualizace Logů
                let logBox = document.getElementById('log-box');
                if(logBox) {
                    logBox.innerHTML = data.logs.map(l => `<div class="log-entry">${l}</div>`).join('');
                }
            } catch(e) {}
        }, 400);
    </script>
</head>
<body>
    <div class="container">
        <header>
            <h1>📡 Build Logic Control & Routing Hub</h1>
            <p>Správa displejů, převod dat a Cross-Server propojení v Robloxu</p>
        </header>

        <!-- Přepínač záložek -->
        <div class="nav-tabs">
            <button class="tab-btn active" onclick="openTab('tab-kontrola')">🎮 Kontrolovat</button>
            <button class="tab-btn" onclick="openTab('tab-textwall')">🧱 Text Wall</button>
            <button class="tab-btn tab-hub" onclick="openTab('tab-hub')">🌐 Cross-Server Hub</button>
            <button class="tab-btn tab-logs" onclick="openTab('tab-logs')">📜 Logy</button>
            <button class="tab-btn tab-setup" onclick="openTab('tab-setup')">⚙️ Set-up & Návody</button>
        </div>

        <!-- 1. ZÁLOŽKA: KONTROLOVAT -->
        <div id="tab-kontrola" class="tab-content active">
            <div class="card">
                <div class="controls-header">
                    <h2>Aktivní obrazovky ({{ visible_count }}/{{ max_displays }})</h2>
                    <div class="btn-group">
                        {% if visible_count < max_displays %}
                        <form method="POST" action="/add_display" style="display:inline;">
                            <button type="submit" class="btn-add" style="padding: 8px 14px;">➕ Přidat displej</button>
                        </form>
                        {% endif %}
                        {% if visible_count > 1 %}
                        <form method="POST" action="/remove_display" style="display:inline;">
                            <button type="submit" class="btn-remove" style="padding: 8px 14px;">➖ Odebrat displej</button>
                        </form>
                        {% endif %}
                    </div>
                </div>
                
                <div class="displays-grid">
                    {% for i in range(1, visible_count + 1) %}
                    {% set d_id = "Displej_0" ~ i %}
                    <div class="status-display">
                        <div class="disp-title">{{ d_id }}</div>
                        <div class="binary-out" id="bin-d{{ i }}">{{ current_val[d_id] }}</div>
                        <div style="font-size: 12px; color: #8b949e; margin-top: 4px;">
                            Fronta: <span id="queue-d{{ i }}">{{ queue_len[d_id] }}</span> znaků
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <div class="grid">
                <div class="card">
                    <h2>⚡ Rychlé odeslání (1 Znak / 8-bit)</h2>
                    <form method="POST" action="/send_single">
                        <label style="font-size: 12px; color: #8b949e; display: block; margin-bottom: 4px;">Cílový displej:</label>
                        <select name="target_display">
                            {% for i in range(1, visible_count + 1) %}
                            {% set d_id = "Displej_0" ~ i %}
                            <option value="{{ d_id }}">{{ d_id }}</option>
                            {% endfor %}
                        </select>
                        <input type="text" name="single_input" maxlength="8" placeholder="např. A nebo 10000001" required autocomplete="off">
                        <button type="submit">Odeslat na displej</button>
                    </form>
                </div>

                <div class="card">
                    <h2>📝 Postupné vysílání textu</h2>
                    <form method="POST" action="/send_text">
                        <label style="font-size: 12px; color: #8b949e; display: block; margin-bottom: 4px;">Cílový displej:</label>
                        <select name="target_display">
                            {% for i in range(1, visible_count + 1) %}
                            {% set d_id = "Displej_0" ~ i %}
                            <option value="{{ d_id }}">{{ d_id }}</option>
                            {% endfor %}
                        </select>
                        <input type="text" name="text_input" placeholder="Napiš text..." required autocomplete="off">
                        <button type="submit">Zařadit do fronty</button>
                    </form>
                    <form method="POST" action="/clear_queue">
                        <button type="submit" class="btn-danger">Vymazat všechny fronty</button>
                    </form>
                </div>
            </div>
        </div>

        <!-- 2. ZÁLOŽKA: TEXT WALL -->
        <div id="tab-textwall" class="tab-content">
            <div class="card">
                <h2>🧱 Text Wall (Příjem dat z Roblox klávesnice)</h2>
                <textarea id="text-wall-area" class="text-wall" readonly placeholder="Zde se zobrazí data odeslaná z klávesnice v Robloxu...">{{ text_wall }}</textarea>
                <div class="wall-actions">
                    <button type="button" onclick="copyTextWall()" class="btn-add">📋 Kopírovat text</button>
                    <form method="POST" action="/clear_wall" style="width: 100%;">
                        <button type="submit" class="btn-remove">🗑️ Vymazat Text Wall</button>
                    </form>
                </div>
            </div>
        </div>

        <!-- 3. ZÁLOŽKA: CROSS-SERVER HUB -->
        <div id="tab-hub" class="tab-content">
            <div class="card card-hub">
                <h2 style="color: #56edf3;">🌐 Cross-Server Routing Grid (Kanály 01 až 10)</h2>
                <p style="font-size: 14px; color: #8b949e; margin-bottom: 20px;">
                    Přímé propojení mezi Roblox vysílačem a přijímačem přes společný <b>ID kanál</b>.
                </p>

                {% for i in range(1, max_cross + 1) %}
                {% set id_str = "%02d" % i %}
                <div class="hub-card">
                    <div class="hub-header">
                        <span>🔀 Propojený pár #{{ id_str }}</span>
                        <span class="hub-channel-tag">KANÁL ID: {{ id_str }}</span>
                    </div>
                    <div class="hub-flow">
                        <div class="hub-node">
                            <div class="hub-node-title">📡 Posílač (Send-ID: {{ id_str }})</div>
                            <div class="binary-out" id="hub-send-{{ id_str }}">{{ cross_channels[id_str]["send_val"] }}</div>
                        </div>
                        <div class="hub-arrow">
                            <span>───►</span>
                            <span class="hub-arrow-status">Paketů: <span id="hub-count-{{ id_str }}">{{ cross_channels[id_str]["packets_count"] }}</span></span>
                        </div>
                        <div class="hub-node">
                            <div class="hub-node-title">📺 Získávač (Receive-ID: {{ id_str }})</div>
                            <div class="binary-out" id="hub-recv-{{ id_str }}">{{ cross_channels[id_str]["recv_val"] }}</div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- 4. ZÁLOŽKA: LOGY -->
        <div id="tab-logs" class="tab-content">
            <div class="card card-logs">
                <h2 style="color: #f2cc60;">📜 Živý výpis systémových zpráv</h2>
                <div id="log-box" class="log-container">
                    {% for log in logs %}
                        <div class="log-entry">{{ log }}</div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- 5. ZÁLOŽKA: SET-UP & NÁVODY -->
        <div id="tab-setup" class="tab-content">
            <!-- URL pro Běžné Displeje -->
            <div class="card card-setup">
                <h2 style="color: #d2a8ff;">1️⃣ URL pro Běžné Displeje (GET)</h2>
                <div class="url-box">
                    <input type="text" id="url-display" value="" readonly>
                    <button type="button" class="copy-btn" onclick="copyUrl('url-display')">📋 Kopírovat</button>
                </div>
                <p style="font-size: 13px; color: #8b949e;"><b>Header:</b> <code>Displej-ID: Displej_01</code> (až <code>Displej_06</code>)</p>
            </div>

            <!-- URL pro Klávesnici / Text Wall -->
            <div class="card card-setup">
                <h2 style="color: #d2a8ff;">2️⃣ URL pro Klávesnici / Text Wall (POST)</h2>
                <div class="url-box">
                    <input type="text" id="url-wall" value="" readonly>
                    <button type="button" class="copy-btn" onclick="copyUrl('url-wall')">📋 Kopírovat</button>
                </div>
                <p style="font-size: 13px; color: #8b949e;"><b>Headers (Vyber jeden):</b></p>
                <ul style="font-size: 13px; color: #8b949e; margin-left: 20px; margin-top: 5px;">
                    <li><code>Data-Type: binary</code> (Uloží surovou binárku)</li>
                    <li><code>Data-Type: decode</code> (Převede binárku na znak)</li>
                    <li><code>Data-Type: symbol</code> (Uloží přímý text)</li>
                </ul>
            </div>

            <!-- URL pro Cross-Server Hub -->
            <div class="card card-setup">
                <h2 style="color: #56edf3;">3️⃣ URL pro Cross-Server Hub (Vysílač & Přijímač)</h2>
                <p style="font-size: 14px; color: #8b949e; margin-bottom: 10px;">
                    Oba prvky používají stejné číslo propojení (např. <code>01</code> až <code>10</code>).
                </p>
                
                <label style="font-size: 12px; color: #56edf3; display: block; margin-top: 10px;">📡 Odesílatel (POST):</label>
                <div class="url-box">
                    <input type="text" id="url-cross-send" value="" readonly>
                    <button type="button" class="copy-btn" onclick="copyUrl('url-cross-send')">📋 Kopírovat</button>
                </div>
                <p style="font-size: 13px; color: #8b949e; margin-bottom: 15px;"><b>Header pro odesílatele:</b> <code>Send-ID: 01</code></p>

                <label style="font-size: 12px; color: #56edf3; display: block;">📺 Přijímač (GET):</label>
                <div class="url-box">
                    <input type="text" id="url-cross-recv" value="" readonly>
                    <button type="button" class="copy-btn" onclick="copyUrl('url-cross-recv')">📋 Kopírovat</button>
                </div>
                <p style="font-size: 13px; color: #8b949e;"><b>Header pro přijímače:</b> <code>Receive-ID: 01</code></p>
            </div>
        </div>
    </div>

    <script>
        let origin = window.location.origin;
        document.getElementById('url-display').value = origin + '/get_signal';
        document.getElementById('url-wall').value = origin + '/api/receive_data';
        document.getElementById('url-cross-send').value = origin + '/api/cross_send';
        document.getElementById('url-cross-recv').value = origin + '/api/cross_receive';
    </script>
</body>
</html>
"""

# --- HTTP ENDPOINTY ---

@app.route('/')
def index():
    return render_template_string(
        HTML_TEMPLATE,
        visible_count=visible_count,
        max_displays=MAX_DISPLAYS,
        max_cross=MAX_CROSS_CHANNELS,
        current_val=display_current,
        queue_len={k: len(v) for k, v in display_queues.items()},
        text_wall=text_wall_data,
        cross_channels=cross_channels,
        logs=logs
    )

# 1. Endpointy pro běžné displeje (GET)
@app.route('/get_signal', methods=['GET'])
def get_signal():
    disp_id = request.headers.get('Displej-ID') or request.headers.get('Displej_ID') or "Displej_01"
    
    if disp_id in display_queues and len(display_queues[disp_id]) > 0:
        val = display_queues[disp_id].pop(0)
        display_current[disp_id] = val
        return val, 200, {'Content-Type': 'text/plain'}
    
    return display_current.get(disp_id, "00000000"), 200, {'Content-Type': 'text/plain'}

# 2. Endpoint pro Text Wall (POST z Robloxu)
@app.route('/api/receive_data', methods=['POST'])
def receive_data():
    global text_wall_data
    raw_body = request.get_data(as_text=True).strip()
    data_type = request.headers.get('Data-Type', 'binary').lower()

    if not raw_body:
        return "Empty body", 400

    processed_text = ""
    if data_type == 'binary':
        processed_text = raw_body + " "
    elif data_type == 'decode':
        try:
            clean_bin = raw_body.replace(" ", "")
            char_code = int(clean_bin, 2)
            processed_text = chr(char_code)
        except ValueError:
            processed_text = f"[Chyba dekódování: {raw_body}]"
    elif data_type == 'symbol':
        processed_text = raw_body

    text_wall_data += processed_text
    add_log(f"📥 [Text Wall] Přijata data ({data_type}): {raw_body}")
    return "OK", 200

# 3. ENDPOINTY PRO CROSS-SERVER HUB (Posílač & Získávač)

@app.route('/api/cross_send', methods=['POST'])
def cross_send():
    """Odesílatel z Robloxu pošle data s Headerem: Send-ID: 01 až 10"""
    send_id = request.headers.get('Send-ID') or request.headers.get('Send_ID')
    raw_body = request.get_data(as_text=True).strip()

    if not send_id:
        return "Chybí Send-ID header", 400

    # Úprava ID na 2 cifry (např. '1' -> '01')
    try:
        formatted_id = f"{int(send_id):02d}"
    except ValueError:
        formatted_id = send_id

    if formatted_id in cross_channels:
        cross_channels[formatted_id]["send_val"] = raw_body
        add_log(f"🌐 [Cross-Hub #{formatted_id}] Vysílač poslal: {raw_body}")
        return "Data uložena do kanálu", 200
    
    return "Neplatný Send-ID kanál", 400

@app.route('/api/cross_receive', methods=['GET'])
def cross_receive():
    """Přijímač z Robloxu žádá o data s Headerem: Receive-ID: 01 až 10"""
    recv_id = request.headers.get('Receive-ID') or request.headers.get('Receive_ID')

    if not recv_id:
        return "Chybí Receive-ID header", 400

    try:
        formatted_id = f"{int(recv_id):02d}"
    except ValueError:
        formatted_id = recv_id

    if formatted_id in cross_channels:
        channel = cross_channels[formatted_id]
        # Převrat dat z posílače na získávače
        val_to_send = channel["send_val"]
        channel["recv_val"] = val_to_send
        channel["packets_count"] += 1
        return val_to_send, 200, {'Content-Type': 'text/plain'}

    return "00000000", 400, {'Content-Type': 'text/plain'}

# API stav pro automatický obnovovací skript
@app.route('/api/status')
def api_status():
    return jsonify({
        "current_val": display_current,
        "queue_len": {k: len(v) for k, v in display_queues.items()},
        "text_wall": text_wall_data,
        "cross_channels": cross_channels,
        "logs": logs
    })

# Form akce pro tlačítka na webu
@app.route('/add_display', methods=['POST'])
def add_display():
    global visible_count
    if visible_count < MAX_DISPLAYS:
        visible_count += 1
        add_log(f"➕ Přidán displej Displej_0{visible_count}")
    return render_template_string('<script>window.location.href="/";</script>')

@app.route('/remove_display', methods=['POST'])
def remove_display():
    global visible_count
    if visible_count > 1:
        add_log(f"➖ Odebrán displej Displej_0{visible_count}")
        visible_count -= 1
    return render_template_string('<script>window.location.href="/";</script>')

@app.route('/send_single', methods=['POST'])
def send_single():
    target = request.form.get('target_display')
    val = request.form.get('single_input', '').strip()
    if target and val:
        bin_val = val if (len(val) == 8 and all(c in '01' for c in val)) else char_to_binary(val[0])
        display_current[target] = bin_val
        add_log(f"⚡ Rychlé odeslání na {target}: {bin_val}")
    return render_template_string('<script>window.location.href="/";</script>')

@app.route('/send_text', methods=['POST'])
def send_text():
    target = request.form.get('target_display')
    text = request.form.get('text_input', '')
    if target and text:
        for char in text:
            display_queues[target].append(char_to_binary(char))
        add_log(f"📝 Do fronty {target} přidáno {len(text)} znaků.")
    return render_template_string('<script>window.location.href="/";</script>')

@app.route('/clear_queue', methods=['POST'])
def clear_queue():
    for k in display_queues:
        display_queues[k] = []
    add_log("🗑️ Všechny fronty byly vymazány.")
    return render_template_string('<script>window.location.href="/";</script>')

@app.route('/clear_wall', methods=['POST'])
def clear_wall():
    global text_wall_data
    text_wall_data = ""
    add_log("🗑️ Text Wall byla vymazána.")
    return render_template_string('<script>window.location.href="/";</script>')

if __name__ == '__main__':
    print("==================================================")
    print("🚀 Build Logic Multi-Display & Cross-Hub spuštěn!")
    print("==================================================")
    app.run(host='0.0.0.0', port=5000, debug=True)
