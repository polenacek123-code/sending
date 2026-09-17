from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Sem se ukládá aktuální zpráva v binární podobě (8 bitů)
current_binary_data = "00000000"

# HTML vzhled jednoduché stránky
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Build Logic Controller</title>
    <style>
        body { font-family: sans-serif; padding: 30px; background: #222; color: #fff; }
        input[type=text] { padding: 10px; font-size: 16px; width: 250px; }
        button { padding: 10px 20px; font-size: 16px; cursor: pointer; }
        .status { margin-top: 20px; font-weight: bold; color: #00ff88; }
    </style>
</head>
<body>
    <h1>Build Logic - Odesílač zpráv</h1>
    <form method="POST" action="/send">
        <label>Zadej 1 znak (nebo 8bit binární kód):</label><br><br>
        <input type="text" name="text_input" maxlength="8" required placeholder="např. A nebo 01000001">
        <button type="submit">Odeslat do hra</button>
    </form>
    <div class="status">
        Aktualní binární hodnota pro Roblox: {{ current_val }}
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, current_val=current_binary_data)

@app.route('/send', methods=['POST'])
def send_data():
    global current_binary_data
    user_input = request.form.get('text_input', '')

    # Pokud uživatel zadal přesně 8 bitů (0 a 1), uložíme přímo
    if len(user_input) == 8 and all(c in '01' for c in user_input):
        current_binary_data = user_input
    elif len(user_input) > 0:
        # Převod prvního znaku na 8-bitový binární kód (ASCII)
        char_code = ord(user_input[0])
        current_binary_data = format(char_code, '08b')

    return render_template_string(HTML_TEMPLATE, current_val=current_binary_data)

# Toto rozhraní volá HTTP Transmitter z Robloxu (GET požadavek)
@app.route('/get_signal', methods=['GET'])
def get_signal():
    return jsonify({"value": current_binary_data})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
