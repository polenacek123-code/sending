from flask import Flask, render_template_string, request, jsonify
import collections
from datetime import datetime

app = Flask(__name__)

# Fronta pro postupné odesílání znaků
char_queue = collections.deque()

# Poslední stav poslaný do Robloxu
current_binary_data = "00000000"

# Historie logů
logs = collections.deque(maxlen=25)

def add_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    logs.appendleft(f"[{timestamp}] {message}")

add_log("Vysílač spuštěn a připraven.")

# --- PREVODNÍK PODLE TVÉ SPECIFIKACE ---
# Bit 1 (vlevo): Shift (1 / 0)
# Bit 2: Mezera (1 / 0)
# Bity 3-8 (6 bitů): Písmeno/Kód (0-63)
def text_to_custom_binary(char):
    if char == ' ':
        # Mezera -> Shift=0, Space=1, Písmeno=000000 -> 01000000
        return "01000000"
    
    is_shift = "1" if char.isupper() else "0"
    is_space = "0"
    
    clean_char = char.lower()
    
    if 'a' <= clean_char <= 'z':
        # a=1, b=2 ... z=26
        char_index = ord(clean_char) - ord('a') + 1  
    elif '0' <= clean_char <= '9':
        # 0=27, 1=28 ... 9=36
        char_index = int(clean_char) + 27            
    else:
        char_index = 0

    bits_data = format(char_index, '06b') # 6 bitů na znak
    
    # Sestavení finálního 8-bitu: Shift + Space + 6-bit kód
    return is_shift + is_space + bits_data

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Build Logic - Terminal Control</title>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background-color: #0b0f19; color: #c9d1d9; padding: 25px 15px; }
        .container { max-width: 900px; margin: 0 auto; }
        header { text-align: center; margin-bottom: 25px; }
        header h1 { font-size: 26px; color: #58a6ff; font-weight: 700; letter-spacing: 1px; }
        header p { color: #8b949e; font-size: 14px; margin-top: 5px; }
        
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }

        .status-display { text-align: center; padding: 15px; background: #0d1117; border-radius: 8px; border: 1px solid #21262d; }
        .binary-out { font-family: 'Fira Code', monospace; font-size: 32px; color: #3fb950; letter-spacing: 4px; font-weight: 600; margin: 10px 0; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; background: #238636; color: #fff; }

        h2 { font-size: 16px; color: #f0f6fc; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; gap: 8px; }
        
        input[type=text] { width: 100%; padding: 12px 15px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #f0f6fc; font-family: 'Fira Code', monospace; font-size: 15px; margin-bottom: 12px; transition: 0.2s; }
        input[type=text]:focus { border-color: #58a6ff; outline: none; box-shadow: 0 0 0 3px rgba(88,166,255,0.15); }

        button { width: 100%; padding: 12px; border-radius: 6px; border: none; font-weight: 600; font-size: 14px; cursor: pointer; transition: 0.2s; background: #238636; color: #ffffff; }
        button:hover { background: #2ea043; transform: translateY(-1px); }
        .btn-secondary { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; }
        .btn-secondary:hover { background: #30363d; color: #f0f6fc; }
        .btn-danger { background: #da3633; color: #fff; margin-top: 8px; }
        .btn-danger:hover { background: #f85149; }

        .quick-actions { display: flex; gap: 8px; margin-top: 10px; }
        .quick-actions button { padding: 8px; font-size: 12px; }

        .log-container { background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 12px; height: 180px; overflow-y: auto; font-family: 'Fira Code', monospace; font-size: 13px; color: #8b949e; line-height: 1.6; }
        .log-entry { margin-bottom: 4px; }
        .log-highlight { color: #58a6ff; }
    </style>
    <script>
        setInterval(async () => {
            try {
                let res = await fetch('/api/status');
                let data = await res.json();
                document.getElementById('binary-val').innerText = data.current_val;
                document.getElementById('queue-count').innerText = data.queue_len;
                
                let logBox = document.getElementById('log-box');
                logBox.innerHTML = data.logs.map(l => `<div class="log-entry">${l}</div>`).join('');
            } catch(e) {}
        }, 400);
    </script>
</head>
<body>
    <div class="container">
        <header>
            <h1>📡 Build Logic Transmitter Panel</h1>
            <p>Propojení webového rozhraní s Roblox logickými obvody</p>
        </header>

        <!-- Status Panel -->
        <div class="card">
            <div class="status-display">
                <span class="badge">ONLINE</span>
                <div class="binary-out" id="binary-val">{{ current_val }}</div>
                <div style="font-size: 13px; color: #8b949e;">
                    Zbývá v pořadníku: <strong id="queue-count" style="color: #58a6ff;">{{ queue_len }}</strong> znaků
                </div>
            </div>
        </div>

        <div class="grid">
            <!-- 1. Přímé nastavení -->
            <div class="card">
                <h2>⚡ Rychlé odeslání (1 Znak / Raw 8-bit)</h2>
                <form method="POST" action="/send_single">
                    <input type="text" name="single_input" maxlength="8" placeholder="např. A nebo 10000001" required autocomplete="off">
                    <button type="submit">Odeslat do hry</button>
                </form>
            </div>

            <!-- 2. Textová sekvence -->
            <div class="card">
                <h2>📝 Postupné vysílání textu</h2>
                <form method="POST" action="/send_text">
                    <input type="text" name="text_input" placeholder="Ahoj Boblox!" required autocomplete="off">
                    <button type="submit">Zařadit text do fronty</button>
                </form>
                
                <div class="quick-actions">
                    <form method="POST" action="/send_text" style="flex: 1;">
                        <input type="hidden" name="text_input" value="Ahoj Roblox!">
                        <button type="submit" class="btn-secondary">Test: Ahoj</button>
                    </form>
                    <form method="POST" action="/clear_queue" style="flex: 1;">
                        <button type="submit" class="btn-danger">Vymazat frontu</button>
                    </form>
                </div>
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
    return render_template_string(
        HTML_TEMPLATE, 
        current_val=current_binary_data, 
        queue_len=len(char_queue) // 2, 
        logs=logs
    )

@app.route('/send_single', methods=['POST'])
def send_single():
    global current_binary_data
    char_queue.clear()
    user_input = request.form.get('single_input', '').strip()

    if len(user_input) == 8 and all(c in '01' for c in user_input):
        current_binary_data = user_input
        add_log(f"Ručně nastaven Raw 8-bit: <span class='log-highlight'>{user_input}</span>")
    elif len(user_input) > 0:
        current_binary_data = text_to_custom_binary(user_input[0])
        add_log(f"Odeslán znak: '<span class='log-highlight'>{user_input[0]}</span>' -> {current_binary_data}")

    return home()

@app.route('/send_text', methods=['POST'])
def send_text():
    text = request.form.get('text_input', '')
    if text:
        for char in text:
            binary_char = text_to_custom_binary(char)
            # Vložíme znak + pauzu pro synchronizaci displeje
            char_queue.append((char, binary_char))
            char_queue.append(('PAUZA', '00000000'))
        add_log(f"Text zařazen do fronty: '<span class='log-highlight'>{text}</span>'")
    return home()

@app.route('/clear_queue', methods=['POST'])
def clear_queue():
    global current_binary_data
    char_queue.clear()
    current_binary_data = "00000000"
    add_log("Fronta byla vymazána.")
    return home()

@app.route('/get_signal', methods=['GET'])
def get_signal():
    global current_binary_data
    
    if char_queue:
        char, binary_val = char_queue.popleft()
        current_binary_data = binary_val
        if char != 'PAUZA':
            add_log(f"Roblox přijal znak: '<span class='log-highlight'>{char}</span>' ({binary_val})")
    
    return jsonify({"value": current_binary_data})

@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify({
        "current_val": current_binary_data,
        "queue_len": len(char_queue) // 2,
        "logs": list(logs)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
