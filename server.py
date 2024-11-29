import aiohttp
import asyncio
from aiohttp import web
import time
import json
import os

# HTML-шаблон для чата с регистрацией через куки
CHAT_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
    <title>Чат</title>
    <style>
        body {
            background-color: black;
            color: #00FF00;
            font-family: 'Courier New', monospace;
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
        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }

        if (!getCookie('username')) {
            document.getElementById('registration-container').style.display = 'flex';
        }

        function registerUser() {
            const username = document.getElementById('username').value.trim();
            if (username) {
                document.cookie = `username=${username}; path=/; max-age=3600`;
                document.getElementById('registration-container').style.display = 'none';
                location.reload();
            } else {
                alert('Введите имя пользователя.');
            }
        }

        function updateChat() {
            fetch('/messages')
                .then(response => response.json())
                .then(data => {
                    const chatHistory = document.getElementById('chat-history');
                    chatHistory.innerHTML = '';
                    data.messages.forEach(message => {
                        const msgElement = document.createElement('div');
                        msgElement.innerHTML = `<b>&lt;${message.user} at ${message.time}&gt;</b>: ${message.text}`;
                        chatHistory.appendChild(msgElement);
                    });
                    chatHistory.scrollTop = chatHistory.scrollHeight;
                });
        }

        function sendMessage() {
            const messageInput = document.getElementById('message');
            const message = messageInput.value.trim();
            if (message) {
                const user = getCookie('username');
                fetch(`/send?username=${encodeURIComponent(user)}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                }).then(() => {
                    messageInput.value = '';
                    updateChat();
                });
            }
        }

        window.onload = function () {
                    const username = getCookie('username');
                    if (!username) {
                        document.getElementById('registration-container').style.display = 'flex';
                    } else {
                        document.getElementById('registration-container').style.display = 'none';
                        updateChat();
                    }
                };
    </script>
</body>
</html>
"""

# Хранение сообщений чата
if os.path.exists("history.json"):
    with open("history.json", "r") as history:
        chat_history = json.load(history)
else:
    chat_history = []

# Обработчик для получения истории сообщений
async def get_messages(request):
    return web.json_response({'messages': chat_history})

# Обработчик для отправки сообщений
async def send_message(request):
    data = await request.json()
    message = data.get('message')
    if message:
        current_time = time.strftime("%H:%M:%S", time.localtime())
        user = request.query.get('username', 'Пользователь')
        chat_history.append({'user': user, 'time': current_time, 'text': message})
        if len(chat_history) > 1000:
            chat_history.pop(0)
        return web.Response(status=200)
    return web.Response(status=400)

# Главная страница с чатом
async def index(request):
    return web.Response(text=CHAT_HTML, content_type='text/html')

# Запуск сервера
async def init():
    app = web.Application()
    app.add_routes([web.get('/', index), web.get('/messages', get_messages), web.post('/send', send_message)])
    return app

web.run_app(init(), host='localhost', port=6969)

with open("history.json", "w") as history:
    json.dump(chat_history, history, indent=4)
