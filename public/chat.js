// FastAPI WebSocket Chat - Updated Version 3 with User Accounts
let ws;
let token;
let currentUsername;
let currentUser;
let currentRoom = 'general';
let availableRooms = new Set(['general', 'random', 'tech', 'gaming']);

// DOM elements
const loginView = document.getElementById('login-view');
const chatView = document.getElementById('chat-view');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const loginError = document.getElementById('login-error');
const registerError = document.getElementById('register-error');
const registerSuccess = document.getElementById('register-success');
const welcomeUser = document.getElementById('welcome-user');
const welcomeRoom = document.getElementById('welcome-room');
const userList = document.getElementById('user-list');
const roomList = document.getElementById('room-list');

// Form switching functions
function showRegisterForm() {
    loginForm.classList.add('d-none');
    registerForm.classList.remove('d-none');
    clearErrors();
}

function showLoginForm() {
    registerForm.classList.add('d-none');
    loginForm.classList.remove('d-none');
    clearErrors();
}

function clearErrors() {
    loginError.textContent = '';
    registerError.textContent = '';
    registerSuccess.textContent = '';
}

// Registration function
async function register() {
    const username = document.getElementById('register-username').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const fullName = document.getElementById('register-fullname').value.trim();
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-confirm-password').value;

    // Validation
    if (!username || !email || !password) {
        registerError.textContent = 'Please fill in all required fields';
        return;
    }

    if (password !== confirmPassword) {
        registerError.textContent = 'Passwords do not match';
        return;
    }

    if (password.length < 6) {
        registerError.textContent = 'Password must be at least 6 characters long';
        return;
    }

    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                email: email,
                full_name: fullName || null,
                password: password
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Registration failed');
        }

        const userData = await response.json();
        registerSuccess.textContent = 'Account created successfully! You can now login.';
        registerError.textContent = '';

        // Clear form
        document.getElementById('register-username').value = '';
        document.getElementById('register-email').value = '';
        document.getElementById('register-fullname').value = '';
        document.getElementById('register-password').value = '';
        document.getElementById('register-confirm-password').value = '';

        // Switch to login form after 2 seconds
        setTimeout(() => {
            showLoginForm();
            // Pre-fill username
            document.getElementById('login-username').value = username;
        }, 2000);

    } catch (error) {
        registerError.textContent = error.message;
        registerSuccess.textContent = '';
        console.error('Registration error:', error);
    }
}

// Updated login function
async function login() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    if (!username || !password) {
        loginError.textContent = 'Please enter both username and password';
        return;
    }

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Login failed');
        }

        const data = await response.json();
        token = data.access_token;
        currentUsername = username;

        // Get user information
        const userResponse = await fetch('/api/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (userResponse.ok) {
            currentUser = await userResponse.json();
        }

        loginView.classList.add('d-none');
        chatView.classList.remove('d-none');
        welcomeUser.textContent = currentUser?.full_name || currentUsername;

        await loadRoomsFromServer();
        initializeEventListeners();
        connectToChat();

    } catch (error) {
        loginError.textContent = error.message;
        console.error('Login error:', error);
    }
}

function connectToChat(roomId = null) {
    if (roomId) {
        currentRoom = roomId;
    }
    welcomeRoom.textContent = currentRoom;

    if (ws) {
        ws.close();
    }

    // Construct WebSocket URL. Note the use of `ws://` or `wss://`
    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${wsProtocol}://${window.location.host}/ws/${currentRoom}/${currentUsername}?token=${token}`;

    ws = new WebSocket(wsUrl);

    // Clear messages when switching rooms
    document.getElementById('messages').innerHTML = '';

    // Update room list active state
    updateRoomListActiveState();

    ws.onopen = function() {
        addMessage("Connected to the chat!", "system-message");
    };

    ws.onmessage = function(event) {
        const messageData = JSON.parse(event.data);

        if (messageData.type === 'system') {
            addMessage(messageData.message, 'system-message');
            if (messageData.users) {
                userList.textContent = messageData.users.join(', ');
                updateRoomUserCount(currentRoom, messageData.users.length);
            }
        } else {
             addMessage(`${messageData.sender}: ${messageData.message}`);
        }
    };

    ws.onclose = function() {
        addMessage("Connection closed. Try logging in again or joining a different room.", "system-message");
        userList.textContent = 'N/A';
    };

    ws.onerror = function(event) {
        addMessage("An error occurred.", "system-message");
        console.error("WebSocket error:", event);
    }
}

function addMessage(message, className = '') {
    const messages = document.getElementById('messages');
    const li = document.createElement('li');
    li.textContent = message;
    if (className) {
        li.classList.add(className);
    }
    messages.appendChild(li);
    messages.scrollTop = messages.scrollHeight;
}

function sendMessage() {
    const messageInput = document.getElementById('messageText');
    const message = messageInput.value;
    if (message && ws && ws.readyState === WebSocket.OPEN) {
        const messagePayload = JSON.stringify({ message: message });
        ws.send(messagePayload);
        messageInput.value = '';
    } else {
        addMessage("Cannot send message. Not connected.", "system-message");
    }
}

function reconnect() {
    if (ws) {
        ws.close();
    }
    connectToChat();
}

// Server-side room management functions
async function loadRoomsFromServer() {
    try {
        const response = await fetch('/api/rooms', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const rooms = await response.json();
            availableRooms.clear();
            rooms.forEach(room => {
                availableRooms.add(room.name);
            });
            updateRoomList(rooms);
        } else {
            console.error('Failed to load rooms from server');
            // Fallback to default rooms
            initializeRoomList();
        }
    } catch (error) {
        console.error('Error loading rooms:', error);
        // Fallback to default rooms
        initializeRoomList();
    }
}

function initializeRoomList() {
    updateRoomList();
}

function updateRoomList(serverRooms = null) {
    roomList.innerHTML = '';

    if (serverRooms) {
        // Use server data
        serverRooms.forEach(room => {
            const roomElement = createRoomElement(room.name, room.user_count, room.display_name);
            roomList.appendChild(roomElement);
        });
    } else {
        // Use local data (fallback)
        availableRooms.forEach(room => {
            const roomElement = createRoomElement(room, 0);
            roomList.appendChild(roomElement);
        });
    }
}

function createRoomElement(roomName, userCount = 0, displayName = null) {
    const roomDiv = document.createElement('div');
    roomDiv.className = `room-item ${roomName === currentRoom ? 'active' : ''}`;
    roomDiv.onclick = () => joinRoom(roomName);

    const roomDisplayName = displayName || roomName;

    roomDiv.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <span><i class="bi bi-hash"></i> ${roomDisplayName}</span>
            <small class="user-count">${userCount}</small>
        </div>
    `;

    return roomDiv;
}

function joinRoom(roomName) {
    if (roomName !== currentRoom) {
        currentRoom = roomName;
        connectToChat(roomName);
    }
}

async function createRoom() {
    console.log('createRoom function called'); // Debug log
    const newRoomInput = document.getElementById('new-room-name');
    if (!newRoomInput) {
        console.error('New room input element not found');
        return;
    }

    const roomName = newRoomInput.value.trim();
    console.log('Room name:', roomName); // Debug log

    if (!roomName) {
        alert('Please enter a room name');
        return;
    }

    // Check if room already exists locally
    if (availableRooms.has(roomName)) {
        joinRoom(roomName);
        newRoomInput.value = '';
        console.log('Joined existing room:', roomName);
        return;
    }

    try {
        // Create room on server
        const response = await fetch('/api/rooms', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                name: roomName,
                display_name: roomName.charAt(0).toUpperCase() + roomName.slice(1),
                description: `${roomName} discussion room`,
                is_public: true,
                max_users: 100
            })
        });

        if (response.ok) {
            const newRoom = await response.json();
            availableRooms.add(newRoom.name);
            await loadRoomsFromServer(); // Refresh room list
            newRoomInput.value = '';
            joinRoom(newRoom.name);
            console.log('Created and joined room:', newRoom.name);
        } else {
            const errorData = await response.json();
            if (errorData.detail && errorData.detail.includes('already exists')) {
                // Room exists on server but not in local cache
                availableRooms.add(roomName);
                await loadRoomsFromServer();
                joinRoom(roomName);
                newRoomInput.value = '';
            } else {
                alert('Failed to create room: ' + (errorData.detail || 'Unknown error'));
            }
        }
    } catch (error) {
        console.error('Error creating room:', error);
        alert('Failed to create room. Please try again.');
    }
}

function updateRoomListActiveState() {
    const roomItems = document.querySelectorAll('.room-item');
    roomItems.forEach(item => {
        const roomName = item.querySelector('span').textContent.trim().substring(1); // Remove # symbol
        if (roomName === currentRoom) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

function updateRoomUserCount(roomName, userCount) {
    const roomItems = document.querySelectorAll('.room-item');
    roomItems.forEach(item => {
        const itemRoomName = item.querySelector('span').textContent.trim().substring(1); // Remove # symbol
        if (itemRoomName === roomName) {
            const userCountElement = item.querySelector('.user-count');
            userCountElement.textContent = userCount;
        }
    });
}

// Event listeners
document.getElementById('messageText').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

// Add event listener for new room input when the chat view is loaded
function initializeEventListeners() {
    const newRoomInput = document.getElementById('new-room-name');
    if (newRoomInput) {
        newRoomInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                createRoom();
            }
        });
    }
}

// Make sure functions are available globally for onclick handlers
window.createRoom = createRoom;
window.sendMessage = sendMessage;
window.login = login;
