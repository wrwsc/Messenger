// Инициализация переменных
let socket = null;
let currentChatId = null;
let currentUser = JSON.parse(localStorage.getItem('currentUser')) || null;
const usersList = document.querySelector('.users-list');
const messageInput = document.querySelector('.input-container input');
const sendButton = document.querySelector('.send-button');
const messagesContainer = document.querySelector('.messages-container');
const searchInput = document.querySelector('#searchInput');

// Функция для установки WebSocket-соединения
function setupWebSocket(chatId) {
    if (socket) {
        socket.close();
        socket = null;
    }
    socket = new WebSocket(`ws://127.0.0.1:8000/bittalk-mes/ws/${chatId}/${currentUser.id}`);
    socket.onmessage = function(event) {
        const messageData = JSON.parse(event.data);
        if (true) {
            if (true) {
                displayMessage(messageData.message);
            }
        } else if (messageData.action === 'message_read') {
            markMessageAsRead(messageData.message_id, messageData.read_by);
        }
    };

    socket.onopen = function() {
        console.log('WebSocket соединение установлено');
    };

    socket.onerror = function(error) {
        console.error('Ошибка WebSocket:', error);
    };

    socket.onclose = function() {
        console.log('WebSocket соединение закрыто');
    };
}

// Обработчик для отображения сообщений
function displayMessage(message) {
    const existingMessage = document.querySelector(`.message[data-message-id='${message.id}']`);
    if (existingMessage) {
        return;
    }
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${message.sender_id === currentUser.id ? 'sent' : 'received'}`;
    messageDiv.dataset.messageId = message.id;
    let messageDate = new Date(message.created_at);
    // Проверка на корректность даты
    if (isNaN(messageDate.getTime())) {
        console.error('Неверный формат даты:', message.created_at);
        messageDate = new Date();
    }
    const messageTime = messageDate.toLocaleTimeString();
    messageDiv.innerHTML = `
        ${message.content}
        <div class="message-time">${messageTime}</div>`;
    messagesContainer.appendChild(messageDiv);
}


function saveMessagesToLocalStorage(chatId) {
    localStorage.setItem(`messages_${chatId}`, JSON.stringify(messages[chatId] || []));
}

// Загрузка сообщений из localStorage
function loadMessagesFromLocalStorage(chatId) {
    const storedMessages = localStorage.getItem(`messages_${chatId}`);
    if (storedMessages) {
        return JSON.parse(storedMessages);
    }
    return [];
}


// В начале загрузки страницы
loadCurrentUser()


async function loadCurrentUser() {
    const response = await fetch('bittalk-mes/current_user', {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
    });

    if (response.ok) {
        const data = await response.json();
        console.log('Загруженный пользователь:', data.user);
        localStorage.setItem('currentUser', JSON.stringify(data.user));
        currentUser = data.user;
    } else {
        console.error('Не удалось загрузить текущего пользователя');
    }
}


// Обработчик отправки сообщения
async function sendMessage() {
    const message = messageInput.value;
    const chatId = parseInt(currentChatId);
    if (!currentUser || !currentUser.id) {
        console.error('Ошибка: currentUser не определён');
        alert('Ошибка: пользователь не найден. Пожалуйста, войдите в систему.');
        window.location.href = '/auth';
        return;
    }
    if (!chatId || !message) {
        console.error('Ошибка: chatId или сообщение отсутствует');
        return;
    }

    const senderId = currentUser.id;
    const recipientId = currentChatId;

    if (senderId === recipientId) {
        console.error('Невозможно отправить сообщение самому себе!');
        return;
    }
    fetch('/bittalk-mes/messages/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify({
            content: message,
            chat_id: chatId,
            sender_id: senderId,
            recipient_id: recipientId
        })
    })
    .then(response => response.text())
    .then(data => {
        try {
            const jsonData = JSON.parse(data);
            console.log('Сообщение отправлено:', jsonData);
        } catch (error) {
            console.error('Ошибка при парсинге JSON:', error);
        }
        messageInput.value = '';
    })
    .catch(error => {
        console.error('Ошибка при отправке сообщения:', error);
    });
}

// Функция для пометки сообщения как прочитанного
function markMessageAsRead(messageId, userId) {
    const messageDiv = document.querySelector(`.message[data-message-id='${messageId}']`);
    if (messageDiv) {
        messageDiv.classList.add('read');
    }
}

// Обработчик выбора пользователя
function selectUser(event, chat) {
    if (!chat) {
        const chatItem = event.target.closest('.chat-item');
        chat = {
            id: chatItem.getAttribute('data-chat-id'),
            name: chatItem.getAttribute('data-chat-name'),
            avatar: chatItem.getAttribute('data-chat-avatar')
        };
    }
    currentChatId = chat.id;
    document.querySelector('.chat-header img').src = chat.avatar;
    document.querySelector('.chat-header h3').textContent = chat.name;
    messagesContainer.innerHTML = '';
    setupWebSocket(currentChatId);
    loadMessagesForChat(currentChatId);
}

document.querySelectorAll('.chat-item').forEach(item => {
    item.addEventListener('click', (event) => {
        selectUser(event);
    });
});



// Функция для загрузки сообщений
async function loadMessagesForChat(chatId) {
    try {
        const response = await fetch(`/bittalk-mes/messages/${chatId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            messagesContainer.innerHTML = '';
            data.forEach(message => {
                displayMessage(message);
            });
        } else {
            console.error('Ошибка при загрузке сообщений');
        }
    } catch (error) {
        console.error('Ошибка при запросе сообщений:', error);
    }
}

// Обработчик для поиска пользователей
searchInput.addEventListener('input', (e) => {
    const searchTerm = e.target.value.toLowerCase();
    document.querySelectorAll('.chat-item').forEach(item => {
        const userName = item.querySelector('h4').textContent.toLowerCase();
        item.style.display = userName.includes(searchTerm) ? 'flex' : 'none';
    });
});

// Поиск пользователей
function searchUsers() {
    const query = document.getElementById('searchInput').value;
    console.log(query);
    fetch(`/auth/search/?query=${query}`)
        .then(response => response.json())
        .then(data => {
            console.log(data);
            const resultsContainer = document.getElementById('searchResults');
            resultsContainer.innerHTML = '';

            data.filter(user => user.id !== currentUser.id).forEach(user => {
                const userDiv = document.createElement('div');
                userDiv.textContent = user.name;
                userDiv.className = 'search-result';
                userDiv.addEventListener('click', () => {
                    selectUser(null, user);
                });

                resultsContainer.appendChild(userDiv);
            });
        })
        .catch(error => console.error('Ошибка при поиске пользователей:', error));
}

// Текущий токен пользователя
function getToken() {
    return localStorage.getItem('token');
}

sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Поиск пользователей по запросу
document.getElementById('searchInput').addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        searchUsers();
    }
});


document.querySelectorAll('.chat-item').forEach(item => {
    const chatId = item.getAttribute('data-chat-id');
    const chatName = item.getAttribute('data-chat-name');
    const chatAvatar = item.getAttribute('data-chat-avatar');
    const chat = { id: chatId, name: chatName, avatar: chatAvatar };
    item.addEventListener('click', (event) => {
        selectUser(event, chat);
    });
});
