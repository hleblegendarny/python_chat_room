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
            height: 90vh;
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
        }
        .input-container input {
            flex: 1;
            padding: 10px;
            background-color: #333;
            color: #00FF00;
            border: none;
            font-size: 16px;
        }
        .input-container button {
            background-color: #00FF00;
            color: black;
            border: none;
            padding: 10px;
            cursor: pointer;
            font-size: 16px;
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
            border: 1px solid #00FF00;
            margin-bottom: 10px;
            width: 100%;
        }
    </style>
</head>
<body>
    <div class="registration-container" id="registration-container">
        <div class="registration-box">
            <input type="text" id="username" placeholder="Введите имя" maxlength="20">
            <button onclick="registerUser()">Зарегистрироваться</button>
        </div>
    </div>

    <div class="chat-container">
        <div class="chat-history" id="chat-history"></div>
        <div class="input-container">
            <input type="text" id="message" placeholder="Напишите сообщение...">
            <button onclick="sendMessage()">Отправить</button>
        </div>
    </div>

    <script>
        let socket;

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
                if (message.user == "HlebLegendarny"){
                    msgElement.innerHTML = `<b>&lt;${message.user} at ${message.time}&gt;</b>: )${message.text})`;
                    chatHistory.appendChild(msgElement);
                    chatHistory.scrollTop = chatHistory.scrollHeight;
                    return true
                }
                msgElement.innerHTML = `<b>&lt;${message.user} at ${message.time}&gt;</b>: ${message.text}`;
                chatHistory.appendChild(msgElement);
                chatHistory.scrollTop = chatHistory.scrollHeight;
            };

            socket.onopen = () => {
                console.log('WebSocket подключён');
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
            if (message && socket && socket.readyState === WebSocket.OPEN) {
                const username = getCookie('username');
                socket.send(JSON.stringify({ user: username, text: message }));
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
    </script>
</body>
</html>
"""

# Обработчик WebSocket-соединения
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    print("Новое WebSocket подключение установлено")
    active_connections.append(ws)
    for message in chat_history:
        await ws.send_str(json.dumps(message))

    try:
        async for msg in ws:
            print(f"Получено сообщение: {msg.data}")
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                current_time = time.strftime("%H:%M:%S", time.localtime())
                message = {
                    'user': data['user'],
                    'time': current_time,
                    'text': data['text']
                }
                chat_history.append(message)
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
        with open("history.json", "w") as history:
            json.dump(chat_history, history)
            history.close()
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
