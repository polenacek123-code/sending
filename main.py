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

# Logy zpráv
logs = collections.deque(maxlen=30)

def add_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    logs.appendleft(f"[{timestamp}] {message}")

add_log("Multidisplejový server spuštěn (Aktivní 1 displej).")

# --- PREVODNÍK NA 8-BIT ---
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
    <title>Build Logic - Dynamic Multi-Display Control</title>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background-color: #0b0f19; color: #c9d1d9; padding: 25px 15px; }
        .container { max-width: 950px; margin: 0 auto; }
        header { text-align: center; margin-bottom: 25px; }
        header h1 { font-size: 26px; color: #58a6ff; font-weight: 700; letter-spacing: 1px; }
        header p { color: #8b949e; font-size: 14px; margin-top: 5px; }
        
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }

        .displays-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; margin-bottom: 15px; }
        .status-display { text-align: center; padding: 15px; background: #0d1117; border-radius: 8px; border: 1px solid #21262d; transition: all 0.3s; }
        .disp-title { font-size: 14px; color: #58a6ff; font-weight: 600; margin-bottom: 5px; }
        .binary-out { font-family: 'Fira Code', monospace; font-size: 22px; color: #3fb950; letter-spacing: 2px; font-weight: 600; }

        .controls-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px; }
        .controls-header h2 { font-size: 16px; color: #f0f6fc; text-transform: uppercase; letter-spacing: 0.5px; }
        .btn-group { display: flex; gap: 8px; }

        h2 { font-size: 16px; color: #f0f6fc; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 0.5px; }
        
        select, input[type=text] { width: 100%; padding: 12px 15px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #f0f6fc; font-family: 'Fira Code', monospace; font-size: 15px; margin-bottom: 12px; }
        select { font-family: 'Inter', sans-serif; cursor: pointer; }
        select:focus, input[type=text]:focus { border-color: #58a6ff; outline: none; }

        button { width: 100%; padding: 12px; border-radius: 6px; border: none; font-weight: 600; font-size: 14px; cursor: pointer; transition: 0.2s; background: #238636; color: #ffffff; }
        button:hover { background: #2ea043; }
        .btn-add { background: #1f6beb; }
        .btn-add:hover { background: #388bfd; }
        .btn-remove { background: #21262d; border: 1px solid #30363d; color: #c9d1d9; }
        .btn-remove:hover { background: #30363d; color: #f0f6fc; }
        .btn-danger { background: #da3633; color: #fff; margin-top: 8px; }
        .btn-danger:hover { background: #f85149; }

        .log-container { background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 12px; height: 180px; overflow-y: auto; font-family: 'Fira Code', monospace; font-size: 13px; color: #8b949e; line-height: 1.6; }
        .log-entry { margin-bottom: 4px; }
        .log-highlight { color: #58a6ff; }
        .log-target { color: #f2cc60; }
    </style>
    <script>
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
                
                let logBox = document.getElementById('log-box');
                logBox.innerHTML = data.logs.map(l => `<div class="log-entry">${l}</div>`).join('');
            } catch(e) {}
        }, 400);
    </script>
</head>
<body>
    <div class="container">
        <header>
            <h1>🖥️ Dynamic Multi-Display Hub</h1>
            <p>Správa až 6 nezávislých obrazovek v Robloxu přes Headers</p>
        </header>

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

        <!-- Logy -->
        <div class="card">
            <h2>📜 Živý výpis zpráv</h2>
            <div id="log-box" class="log-container">
                {% for log in logs %}
                    <div class="log-entry">{{ log }}</div>
                {% endfor %}
            </div>
        </div>
    </div>
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

@app.route('/api/status', methods=['GET'])
def api_status():
    q_lengths = {d: len(display_queues[d]) // 2 for d in display_ids}
    return jsonify({
        "current_val": current_binary_data,
        "queue_len": q_lengths,
        "logs": list(logs)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
