from flask import Flask, render_template_string, request, jsonify
import collections
from datetime import datetime

app = Flask(__name__)

# Fronta pro postupné odesílání znaků (FIFO)
char_queue = collections.deque()

# Poslední stav poslaný do Robloxu
current_binary_data = "00000000"

# Historie logů (ukládáme posledních 20 událostí)
logs = collections.deque(maxlen=20)

def add_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    logs.appendleft(f"[{timestamp}] {message}")

add_log("Server byl úspěšně spuštěn.")

# --- PREVODNÍK PRO TVŮJ DISPLEJ (6 bitů znak + 1 bit Shift + 1 bit 0) ---
def text_to_custom_binary(char):
    is_shift = 1 if char.isupper() else 0
    clean_char = char.lower()
    
    if 'a' <= clean_char <= 'z':
        # a=1, b=2, c=3 ... z=26
        char_index = ord(clean_char) - ord('a') + 1  
    elif '0' <= clean_char <= '9':
        # 0=27, 1=28 ... 9=36
        char_index = int(clean_char) + 27            
    elif clean_char == ' ':
        char_index = 0                               
    else:
        char_index = 0
        
    bit_unused = "0"
    bit_shift = str(is_shift)
    bits_data = format(char_index, '06b') # 6 bitů na kód
    
    return bit_unused + bit_shift + bits_data

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Build Logic - Advanced Transmitter</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background: #121212; color: #e0e0e0; max-width: 800px; margin: 0 auto; }
        h1, h2 { color: #00ff88; text-align: center; }
        .card { background: #1e1e1e; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        input[type=text] { padding: 12px; font-size: 16px; width: calc(100% - 26px); background: #2b2b2b; border: 1px solid #444; color: #fff; border-radius: 4px; margin-bottom: 10px; }
        button { padding: 12px 20px; font-size: 16px; cursor: pointer; background: #00ff88; color: #000; font-weight: bold; border: none; border-radius: 4px; width: 100%; transition: 0.2s; }
        button:hover { background: #00cc6a; }
        .btn-clear { background: #ff4444; color: #fff; margin-top: 5px; }
        .btn-clear:hover { background: #cc0000; }
        .status { font-weight: bold; color: #00ff88; font-size: 18px; text-align: center; margin-top: 10px; }
        .log-box { background: #000; color: #00ff00; font-family: monospace; padding: 15px; border-radius: 4px; height: 200px; overflow-y: auto; border: 1px solid #333; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } }
    </style>
    <script>
        setInterval(async () => {
            let res = await fetch('/api/status');
            let data = await res.json();
            document.getElementById('current-val').innerText = data.current_val;
            document.getElementById('queue-len').innerText = data.queue_len;
            
            let logBox = document.getElementById('log-box');
            logBox.innerHTML = data.logs.join('<br>');
        }, 500);
    </script>
</head>
<body>
    <h1>📟 Build Logic HTTP Panel</h1>

    <div class="card">
        <div class="status">
            Aktuální výstup: <span id="current-val">{{ current_val }}</span><br>
            <small style="color: #aaa; font-size: 14px;">Znaků ve frontě: <span id="queue-len">{{ queue_len }}</span></small>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h2>1. Rychlé vysílání (1 znak / 8-bit)</h2>
            <form method="POST" action="/send_single">
                <input type="text" name="single_input" maxlength="8" placeholder="např. A nebo 00000001" required>
                <button type="submit">Odeslat ihned</button>
            </form>
        </div>

        <div class="card">
            <h2>2. Postupné vysílání textu</h2>
            <form method="POST" action="/send_text">
                <input type="text" name="text_input" placeholder="Ahoj Roblox!" required>
                <button type="submit">Zařadit text do fronty</button>
            </form>
            <form method="POST" action="/clear_queue">
                <button type="submit" class="btn-clear">Vymazat frontu</button>
            </form>
        </div>
    </div>

    <div class="card">
        <h2>📜 Živé logy komunikace</h2>
        <div id="log-box" class="log-box">
            {% for log in logs %}
                {{ log }}<br>
            {% endfor %}
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
        queue_len=len(char_queue), 
        logs=logs
    )

@app.route('/send_single', methods=['POST'])
def send_single():
    global current_binary_data
    char_queue.clear()
    user_input = request.form.get('single_input', '').strip()

    if len(user_input) == 8 and all(c in '01' for c in user_input):
        current_binary_data = user_input
        add_log(f"Ručně nastaven 8-bit: {user_input}")
    elif len(user_input) > 0:
        current_binary_data = text_to_custom_binary(user_input[0])
        add_log(f"Ručně nastaven znak: '{user_input[0]}' -> {current_binary_data}")

    return home()

@app.route('/send_text', methods=['POST'])
def send_text():
    text = request.form.get('text_input', '')
    if text:
        for char in text:
            binary_char = text_to_custom_binary(char)
            # Vložíme znak A ZÁROVEŇ pauzu (nulový kód) pro spolehlivou synchronizaci
            char_queue.append((char, binary_char))
            char_queue.append(('PAUZA', '00000000'))
        add_log(f"Přidán text do fronty s pauzami: '{text}' ({len(text)} znaků)")
    return home()

@app.route('/clear_queue', methods=['POST'])
def clear_queue():
    global current_binary_data
    char_queue.clear()
    current_binary_data = "00000000"
    add_log("Fronta odesílání byla vymazána.")
    return home()

@app.route('/get_signal', methods=['GET'])
def get_signal():
    global current_binary_data
    
    if char_queue:
        char, binary_val = char_queue.popleft()
        current_binary_data = binary_val
        if char != 'PAUZA':
            add_log(f"Roblox načetl znak '{char}' ({binary_val}). Zbývá znaků: {len(char_queue)//2}")
    
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
