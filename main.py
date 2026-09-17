from flask import Flask, render_template_string, request, jsonify
import collections
from datetime import datetime

app = Flask(__name__)

MAX_DISPLAYS = 6

# Vytvořit fronty a hodnoty pro 6 displejů (Displej_01 až Displej_06)
display_ids = [f"Displej_0{i}" for i in range(1, MAX_DISPLAYS + 1)]

display_queues = {d: collections.deque() for d in display_ids}
current_binary_data = {d: "00000000" for d in display_ids}

# Počet viditelných displejů na webu (1 až 6)
visible_count = 1

# Ukládání obsahu pro Text Wall z klávesnice
text_wall_content = ""

# Logy zpráv
logs = collections.deque(maxlen=30)

def add_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    logs.appendleft(f"[{timestamp}] {message}")

add_log("Multidisplejový server spuštěn.")

# --- VYLEPŠENÝ PREVODNÍK 8-BIT -> ZNAK ---
def custom_binary_to_text(binary_str):
    if len(binary_str) != 8 or not all(c in '01' for c in binary_str):
        return f"[{binary_str}]"
    
    # 1. Zkouška standardní ASCII binárky (převod z desítkové soustavy)
    ascii_val = int(binary_str, 2)
    if 32 <= ascii_val <= 126:
        return chr(ascii_val)

    # 2. Zkouška custom 8bit logiky (Shift + Space + 6bit index)
    is_shift = binary_str[0] == "1"
    is_space = binary_str[1] == "1"
    
    if is_space:
        return " "
        
    char_index = int(binary_str[2:], 2)
    
    if 1 <= char_index <= 26:
        char = chr(ord('a') + char_index - 1)
        return char.upper() if is_shift else char
    elif 27 <= char_index <= 36:
        return str(char_index - 27)
    
    # Pokud kód neodpovídá ničemu, zobrazí se přímo binárka
    return f"[{binary_str}]"
# --- PREVODNÍK ZNAK -> 8-BIT ---
def text_to_custom_binary(char):
    if char == ' ':
        return "01000000"
    
    is_shift = "1" if char.isupper() else "0"
    is_space = "0"
    clean_char = char.lower()
    
    if 'a' <= clean_char <= 'z':
        char_index = ord(clean_char) - ord('a') + 1  
    elif '0' <= clean_char <= '9':
        char_index = int(clean_char) + 27            
    else:
        char_index = 0

    bits_data = format(char_index, '06b')
    return is_shift + is_space + bits_data

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Build Logic - Multi-Display Hub</title>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background-color: #0b0f19; color: #c9d1d9; padding: 25px 15px; }
        .container { max-width: 950px; margin: 0 auto; }
        header { text-align: center; margin-bottom: 20px; }
        header h1 { font-size: 26px; color: #58a6ff; font-weight: 700; letter-spacing: 1px; }
        header p { color: #8b949e; font-size: 14px; margin-top: 5px; }
        
        /* Záložky (Tabs) */
        .nav-tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 1px solid #30363d; padding-bottom: 10px; justify-content: center; flex-wrap: wrap; }
        .tab-btn { background: #161b22; color: #8b949e; border: 1px solid #30363d; padding: 10px 18px; font-weight: 600; font-size: 14px; border-radius: 8px; cursor: pointer; transition: 0.2s; }
        .tab-btn:hover { background: #21262d; color: #f0f6fc; }
        .tab-btn.active { background: #1f6beb; color: #ffffff; border-color: #388bfd; }

        /* Zvýraznění pro Logy a Set-up */
        .tab-btn.tab-logs { border-color: #d29922; color: #d29922; }
        .tab-btn.tab-logs:hover { background: #272115; color: #f2cc60; }
        .tab-btn.tab-logs.active { background: #d29922; color: #0d1117; border-color: #f2cc60; font-weight: 700; }

        .tab-btn.tab-setup { border-color: #a371f7; color: #a371f7; }
        .tab-btn.tab-setup:hover { background: #251e38; color: #d2a8ff; }
        .tab-btn.tab-setup.active { background: #8957e5; color: #ffffff; border-color: #d2a8ff; font-weight: 700; }

        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        .card-logs { border-color: #d29922; }
        .card-setup { border-color: #8957e5; }

        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }

        .displays-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; margin-bottom: 15px; }
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
        .log-highlight { color: #58a6ff; }
        .log-target { color: #f2cc60; }

        /* Text Wall */
        .text-wall { width: 100%; height: 280px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px; font-family: 'Fira Code', monospace; color: #3fb950; font-size: 16px; resize: vertical; margin-bottom: 15px; word-break: break-all; }
        .wall-actions { display: flex; gap: 10px; }

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
                
                for (let i = 1; i <= 6; i++) {
                    let key = 'Displej_0' + i;
                    let binEl = document.getElementById('bin-d' + i);
                    let qEl = document.getElementById('queue-d' + i);
                    if (binEl) binEl.innerText = data.current_val[key] || "00000000";
                    if (qEl) qEl.innerText = data.queue_len[key] || 0;
                }
                
                let wall = document.getElementById('text-wall-area');
                if (wall && document.activeElement !== wall) {
                    wall.value = data.text_wall;
                }

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
            <h1>📡 Build Logic Control Hub</h1>
            <p>Řízení Roblox logických obvodů a displejů v reálném čase</p>
        </header>

        <!-- Přepínač záložek -->
        <div class="nav-tabs">
            <button class="tab-btn active" onclick="openTab('tab-kontrola')">🎮 Kontrolovat</button>
            <button class="tab-btn" onclick="openTab('tab-textwall')">🧱 Text Wall</button>
            <button class="tab-btn tab-logs" onclick="openTab('tab-logs')">📜 Logy</button>
            <button class="tab-btn tab-setup" onclick="openTab('tab-setup')">⚙️ Set-up & Návod</button>
        </div>

        <!-- 1. ZÁLOŽKA: KONTROLOVAT -->
        <div id="tab-kontrola" class="tab-content active">
            <!-- Přehled stavu displejů -->
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
                <!-- Rychlé odeslání -->
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

                <!-- Postupné odeslání textu -->
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

        <!-- 3. ZÁLOŽKA: LOGY (Zvýrazněná předposlední záložka) -->
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

        <!-- 4. ZÁLOŽKA: SET-UP (Zvýrazněná poslední záložka) -->
        <div id="tab-setup" class="tab-content">
            <!-- URL pro HTTP Transmitter (Displeje) -->
            <div class="card card-setup">
                <h2 style="color: #d2a8ff;">📺 URL pro Displeje (GET)</h2>
                <p style="font-size: 14px; color: #8b949e; margin-bottom: 12px;">
                    Tuto adresu vlož do pole <b>URL</b> u HTTP Transmitteru připojeného k displeji:
                </p>
                <div class="url-box">
                    <input type="text" id="server-url-display" value="" readonly>
                    <button type="button" class="copy-btn" onclick="copyUrl('server-url-display')">📋 Kopírovat</button>
                </div>
            </div>

            <!-- URL pro Klávesnici (POST / Text Wall) -->
            <div class="card card-setup">
                <h2 style="color: #d2a8ff;">⌨️ URL pro Klávesnici / Odesílání na Text Wall (POST)</h2>
                <p style="font-size: 14px; color: #8b949e; margin-bottom: 12px;">
                    Tuto adresu vlož do pole <b>URL</b> u HTTP Transmitteru, který odesílá stisknuté klávesy z Robloxu:
                </p>
                <div class="url-box">
                    <input type="text" id="server-url-wall" value="" readonly>
                    <button type="button" class="copy-btn" onclick="copyUrl('server-url-wall')">📋 Kopírovat</button>
                </div>
            </div>

            <!-- Headers pro Klávesnici -->
            <div class="card card-setup">
                <h2 style="color: #d2a8ff;">🏷️ Headers pro Klávesnici (Data-Type)</h2>
                <p style="font-size: 14px; color: #8b949e; margin-bottom: 12px;">
                    V nastavení HTTP Transmitteru u klávesnice přidej do pole <b>Headers</b> jeden z těchto režimů:
                </p>
                <table>
                    <thead>
                        <tr>
                            <th>Požadovaný režim</th>
                            <th>Co napsat do pole Headers v Robloxu</th>
                            <th>Popis</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><b>Surová Binárka</b></td>
                            <td><code>Data-Type: binary</code></td>
                            <td>Uloží na Text Wall přesně odeslaný 8bitový kód (např. <code>00001101</code>) bez jakéhokoliv převodu.</td>
                        </tr>
                        <tr>
                            <td><b>Převod binárky na znak</b></td>
                            <td><code>Data-Type: decode</code></td>
                            <td>Klávesnice posílá 8bitový kód (např. <code>00001101</code>), web ho automaticky převede na znak (<code>m</code>) a přidá na Text Wall.</td>
                        </tr>
                        <tr>
                            <td><b>Přímé symboly / text</b></td>
                            <td><code>Data-Type: symbol</code></td>
                            <td>Klávesnice posílá přímo text nebo symbol, web ho zapíše přímo na Text Wall.</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- Headers pro nastavení displejů -->
            <div class="card card-setup">
                <h2 style="color: #d2a8ff;">📑 Headers pro Displeje (Displej-ID)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Název v panelu</th>
                            <th>Co napsat do pole Headers v Robloxu</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for i in range(1, max_displays + 1) %}
                        <tr>
                            <td><b>Displej_0{{ i }}</b></td>
                            <td><code>Displej-ID: Displej_0{{ i }}</code></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('server-url-display').value = window.location.origin + '/get_signal';
        document.getElementById('server-url-wall').value = window.location.origin + '/api/receive_data';
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    q_lengths = {d: len(display_queues[d]) // 2 for d in display_ids}
    return render_template_string(
        HTML_TEMPLATE, 
        current_val=current_binary_data, 
        queue_len=q_lengths, 
        visible_count=visible_count,
        max_displays=MAX_DISPLAYS,
        text_wall=text_wall_content,
        logs=logs
    )

@app.route('/add_display', methods=['POST'])
def add_display():
    global visible_count
    if visible_count < MAX_DISPLAYS:
        visible_count += 1
        add_log(f"Přidán displej: <span class='log-target'>Displej_0{visible_count}</span>")
    return home()

@app.route('/remove_display', methods=['POST'])
def remove_display():
    global visible_count
    if visible_count > 1:
        add_log(f"Schován displej: <span class='log-target'>Displej_0{visible_count}</span>")
        visible_count -= 1
    return home()

@app.route('/clear_wall', methods=['POST'])
def clear_wall():
    global text_wall_content
    text_wall_content = ""
    add_log("Text Wall byla vymazána.")
    return home()

@app.route('/send_single', methods=['POST'])
def send_single():
    target = request.form.get('target_display', 'Displej_01')
    user_input = request.form.get('single_input', '').strip()

    if target in display_queues:
        display_queues[target].clear()

        if len(user_input) == 8 and all(c in '01' for c in user_input):
            current_binary_data[target] = user_input
            add_log(f"<b>[{target}]</b> Raw 8-bit: <span class='log-highlight'>{user_input}</span>")
        elif len(user_input) > 0:
            current_binary_data[target] = text_to_custom_binary(user_input[0])
            add_log(f"<b>[{target}]</b> Znak: '<span class='log-highlight'>{user_input[0]}</span>' -> {current_binary_data[target]}")

    return home()

@app.route('/send_text', methods=['POST'])
def send_text():
    target = request.form.get('target_display', 'Displej_01')
    text = request.form.get('text_input', '')

    if target in display_queues and text:
        for char in text:
            binary_char = text_to_custom_binary(char)
            display_queues[target].append((char, binary_char))
            display_queues[target].append(('PAUZA', '00000000'))
        add_log(f"<span class='log-target'>[{target}]</span> Text zařazen: '<span class='log-highlight'>{text}</span>'")
    return home()

@app.route('/clear_queue', methods=['POST'])
def clear_queue():
    for d in display_ids:
        display_queues[d].clear()
        current_binary_data[d] = "00000000"
    add_log("Všechny fronty byly vymazány.")
    return home()

@app.route('/get_signal', methods=['GET'])
def get_signal():
    display_id = request.headers.get('Displej-ID', 'Displej_01').strip()
    
    if display_id in display_queues:
        if display_queues[display_id]:
            char, binary_val = display_queues[display_id].popleft()
            current_binary_data[display_id] = binary_val
            if char != 'PAUZA':
                add_log(f"<span class='log-target'>[{display_id}]</span> Načten znak: '<span class='log-highlight'>{char}</span>'")
        return jsonify({"value": current_binary_data[display_id]})

    return jsonify({"value": "00000000"})

# --- PŘESNÝ ENDPOINT PRO TEXT WALL ---
@app.route('/api/receive_data', methods=['POST'])
def receive_data():
    global text_wall_content
    
    data_type = request.headers.get('Data-Type', 'binary').lower().strip()
    
    # 1. Získání surovaného textu z požadavku
    raw_text = request.get_data(as_text=True).strip()
    incoming_val = ""

    # 2. Vyčištění dat z Robloxu (JSON, value=... nebo raw)
    if request.is_json:
        data = request.get_json(silent=True) or {}
        incoming_val = str(data.get('value', ''))
    elif 'value' in raw_text:
        import re
        match = re.search(r'[01]{8}', raw_text)
        if match:
            incoming_val = match.group(0)
        else:
            incoming_val = raw_text.split('value')[-1].replace('=', '').replace(':', '').replace('}', '').replace('"', '').strip()
    else:
        incoming_val = raw_text.replace('{"value":"', '').replace('"}', '').strip()

    if not incoming_val:
        return jsonify({"value": "ERROR"}), 400

    # 3. Zpracování podle Headeru
    if data_type == 'binary':
        # Nepřevádí na znak! Zapíše přímo čitelnou binárku
        clean_binary = ''.join(c for c in incoming_val if c in '01')
        text_wall_content += clean_binary + " "
        add_log(f"⌨️ <b>Klávesnice (Surová Binárka):</b> <span class='log-highlight'>{clean_binary}</span>")
        
    elif data_type == 'decode':
        # Převede binárku na znak (např. 00001101 -> m)
        clean_binary = ''.join(c for c in incoming_val if c in '01')
        decoded_char = custom_binary_to_text(clean_binary)
        text_wall_content += decoded_char
        add_log(f"⌨️ <b>Klávesnice (Převod na Znak):</b> {clean_binary} -> '<span class='log-highlight'>{decoded_char}</span>'")
        
    else:
        # Symbol / Text
        text_wall_content += incoming_val
        add_log(f"⌨️ <b>Klávesnice (Symbol):</b> '<span class='log-highlight'>{incoming_val}</span>'")

    return jsonify({"value": "OK", "status": "success"}), 200
@app.route('/api/status', methods=['GET'])
def api_status():
    q_lengths = {d: len(display_queues[d]) // 2 for d in display_ids}
    return jsonify({
        "current_val": current_binary_data,
        "queue_len": q_lengths,
        "text_wall": text_wall_content,
        "logs": list(logs)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
