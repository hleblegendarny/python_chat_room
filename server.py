import aiohttp
import asyncio
from aiohttp import web, WSMsgType
import time
import json
import os
import ssl

ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')

# Хранение сообщений чата
if os.path.exists("history.json"):
    with open("history.json", "r") as history:
        chat_history = json.load(history)
else:
    chat_history = []

# Хранение WebSocket-соединений
active_connections = []

# HTML-шаблон чата (без изменений)
CHAT_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono&display=swap" rel="stylesheet">
    <title>Чат</title>
    <style>
        body {
            background-color: black;
            color: #00FF00;
            font-family: 'IBM Plex Mono', monospace;
            margin: 0;
            padding: 0;
        }
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        .chat-history {
            flex: 1;
            padding: 10px;
            overflow-y: auto;
        }
        .input-container {
            display: flex;
            padding: 10px;
            background-color: #222;
            gap: 10px;
        }
        .input-container input {
            padding: 10px;
            background-color: #333;
            color: #00FF00;
            border: none;
            font-size: 16px;
            border-radius: 8px;
        }
        .input-container button {
            background-color: #00FF00;
            color: black;
            border: none;
            padding: 10px;
            cursor: pointer;
            font-size: 16px;
            border-radius: 8px;
        }
        .registration-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .registration-box {
            background-color: #222;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            width: 300px;
        }
        .registration-box input {
            padding: 10px;
            font-size: 16px;
            background-color: #333;
            color: #00FF00;
            border: 0;
            margin-bottom: 10px;
            width: 70%;
            border-radius: 8px;
        }
        .color-menu {
            position: fixed;
            top: 10px;
            right: 10px; /* Переносим в правый верхний угол */
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            background-color: #222;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
        }

        .color-option {
            width: 30px;
            height: 30px;
            border-radius: 4px;
            cursor: pointer;
            border: 2px solid #000;
            transition: transform 0.2s ease, border 0.2s ease;
        }

        .color-option:hover {
            transform: scale(1.2) translateY(-5.0f);
            border: 2px solid #FFF;
            box-shadow: 0 4px 8px rgba(255, 255, 255, 0.6);
        }

        button {
            background-color: #222;
            color: #555;
            border-radius: 8px;
            border-width: 1;
            cursor: pointer;
            display: inline-block;
        }
    </style>
</head>
<body>
    <div class="color-menu" id="color-menu">
    <button onclick="toggleColorMenu()" style="background-color: #333; color: #00FF00; border-radius: 8px; border: none; padding: 10px; cursor: pointer;">Скрыть меню</button>
    <div class="color-option" style="background-color: #FF0000;" onclick="setColorCookie('#FF0000')"></div>
    <div class="color-option" style="background-color: #00FF00;" onclick="setColorCookie('#00FF00')"></div>
    <div class="color-option" style="background-color: #0000FF;" onclick="setColorCookie('#0000FF')"></div>
    <div class="color-option" style="background-color: #FFFF00;" onclick="setColorCookie('#FFFF00')"></div>
    <div class="color-option" style="background-color: #FF00FF;" onclick="setColorCookie('#FF00FF')"></div>
    <div class="color-option" style="background-color: #00FFFF;" onclick="setColorCookie('#00FFFF')"></div>
    <div class="color-option" style="background-color: #FFFFFF;" onclick="setColorCookie('#FFFFFF')"></div>
    <div class="color-option" style="background-color: #C0C0C0;" onclick="setColorCookie('#C0C0C0')"></div>
    <div class="color-option" style="background-color: #808080;" onclick="setColorCookie('#808080')"></div>
    <div class="color-option" style="background-color: #4B0082;" onclick="setColorCookie('#4B0082')"></div>
    <div class="color-option" style="background-color: #8B008B;" onclick="setColorCookie('#8B008B')"></div>
    <div class="color-option" style="background-color: #008080;" onclick="setColorCookie('#008080')"></div>
    <div class="color-option" style="background-color: #1e3a5f;" onclick="setColorCookie('#1e3a5f')"></div>
    </div>

    <div class="registration-container" id="registration-container">
        <div class="registration-box">
            <input type="text" id="username" placeholder="Введите имя" maxlength="20">
            <button onclick="registerUser()">Зарегистрироваться</button>
        </div>
    </div>

    <div class="chat-container">
        <div class="chat-history" id="chat-history"></div>
        <div class="input-container">
            <input type="text" id="message" style="color: #FFFFFF;" placeholder="Напишите сообщение...">
            <button onclick="sendMessage()">Отправить</button>
        </div>
    </div>

    <script>
        let socket;

        function toggleColorMenu() {
            const colorMenu = document.getElementById('color-menu');
            // Переключаем видимость меню
            if (colorMenu.style.display === 'none') {
                colorMenu.style.display = 'flex';  // Показываем меню
            } else {
                colorMenu.style.display = 'none';  // Скрываем меню
            }
        }

        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }

        function registerUser() {
            const username = document.getElementById('username').value.trim();
            if (username) {
                document.cookie = `username=${username}; path=/; max-age=3600`;
                document.getElementById('registration-container').style.display = 'none';
                connectWebSocket();
            } else {
                alert('Введите имя пользователя.');
            }
        }

        function connectWebSocket() {
            const username = getCookie('username');
            if (!username) {
                document.getElementById('registration-container').style.display = 'flex';
                return;
            }
            socket = new WebSocket(`wss://${window.location.host}/ws`);

            socket.onmessage = (event) => {
                const chatHistory = document.getElementById('chat-history');
                const message = JSON.parse(event.data);
                const msgElement = document.createElement('div');

                const messageColor = message.color || '#00FF00';

                if (message.user == "HlebLegendarny"){message.text=`)${message.text})`}
                if (message.user == "YeRo"){message.text=`[${message.text}]`}

                msgElement.innerHTML = `<span style="color: ${messageColor}"><b>&lt;${message.user} at ${message.time}&gt;</b>: ${message.text}</span>`;
                chatHistory.appendChild(msgElement);
                chatHistory.scrollTop = chatHistory.scrollHeight;
            };

            socket.onopen = () => {
                document.getElementById('registration-container').style.display = 'none';
            };

            socket.onclose = () => {
                console.error('WebSocket закрыт, переподключение...');
                setTimeout(connectWebSocket, 1000);
            };
            socket.onerror = (error) => console.error('WebSocket ошибка:', error);

        }

        function sendMessage() {
            const messageInput = document.getElementById('message');
            const message = messageInput.value.trim();
            const color = getCookie('color') || "#00FF00";
            if (message && socket && socket.readyState === WebSocket.OPEN) {
                const username = getCookie('username');
                socket.send(JSON.stringify({ user: username, text: message, color: color }));
                messageInput.value = '';
            }
        }
        document.getElementById('message').addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        });

        // Обработчик для нажатия кнопки отправки
        document.querySelector('button').addEventListener('click', sendMessage);

        window.onload = connectWebSocket;

        function setColorCookie(color){
            const username = getCookie('username');
            if(!username){
                document.getElementById('registration-container').style.display = 'flex';
                return false;
            }
            document.cookie = `color=${color}; path=/; max-age=3600`;
        }
    </script>
</body>
</html>
"""

# Обработчик WebSocket-соединения
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    active_connections.append(ws)
    for message in chat_history:
        if 'color' not in message:
            message['color'] = '#00FF00'
        await ws.send_str(json.dumps(message))
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                current_time = time.strftime("%H:%M:%S", time.localtime())
                message = {
                    'user': data['user'],
                    'time': current_time,
                    'text': data['text'],
                    'color': data.get('color', '#00FF00')
                }
                chat_history.append(message)

                with open("history.json", "w") as history:
                    json.dump(chat_history, history)

                if len(chat_history) > 65535:
                    chat_history.pop(0)
                # Рассылка сообщения всем подключённым клиентам
                for conn in active_connections:
                    await conn.send_json(message)
            elif msg.type == WSMsgType.ERROR:
                print(f'Ошибка WebSocket: {ws.exception()}')
    except Exception as e:
        print(f"Ошибка WebSocket: {e}")
    finally:
        active_connections.remove(ws)

    return ws

# Главная страница с чатом
async def index(request):
    return web.Response(text=CHAT_HTML, content_type='text/html')

# Инициализация сервера
async def init():
    app = web.Application()
    app.add_routes([
        web.get('/', index),
        web.get('/ws', websocket_handler)
    ])
    return app

web.run_app(init(), host='localhost', port=6969, ssl_context=ssl_context)
