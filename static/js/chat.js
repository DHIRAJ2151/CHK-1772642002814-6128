document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chat-container');
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatToggle = document.getElementById('chat-toggle');
    const voiceInputButton = document.getElementById('voice-input-button');
    const voiceStatus = document.getElementById('voice-status');
    const toggleSpeechButton = document.getElementById('toggle-speech');
    
    // Check if we're on the test page
    const isTestPage = document.body.classList.contains('test-chat-page');
    
    // Speech settings - TTS disabled by default, user must enable
    let speechEnabled = false;
    let recognition = null;
    let isListening = false;
    
    // Initialize Speech Recognition (Speech-to-Text)
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        recognition.maxAlternatives = 1;
        
        // Check if site is secure (HTTPS or localhost)
        const isSecure = window.location.protocol === 'https:' || 
                        window.location.hostname === 'localhost' || 
                        window.location.hostname === '127.0.0.1';
        
        if (!isSecure) {
            console.warn('⚠️ Speech recognition may not work on non-HTTPS sites. Current protocol:', window.location.protocol);
            console.warn('💡 Try accessing via: https://' + window.location.host);
        }
        
        recognition.onstart = function() {
            isListening = true;
            voiceInputButton.classList.add('listening');
            voiceStatus.classList.remove('hidden');
            console.log('✅ Voice recognition started');
        };
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            const confidence = event.results[0][0].confidence;
            chatInput.value = transcript;
            console.log('✅ Recognized:', transcript, '(confidence:', confidence, ')');
            showNotification('✅ Recognized: "' + transcript.substring(0, 40) + (transcript.length > 40 ? '..."' : '"'));
        };
        
        recognition.onerror = function(event) {
            console.error('❌ Speech recognition error:', event.error);
            console.error('Error details:', event);
            isListening = false;
            voiceInputButton.classList.remove('listening');
            voiceStatus.classList.add('hidden');
            
            let errorMessage = '';
            let helpText = '';
            
            switch(event.error) {
                case 'no-speech':
                    errorMessage = '🎤 No speech detected. Please try again and speak clearly.';
                    helpText = 'Tip: Speak within 3-5 seconds of clicking the microphone button.';
                    break;
                case 'audio-capture':
                    errorMessage = '❌ Microphone not found. Please check your microphone connection.';
                    helpText = 'Make sure your microphone is plugged in and working.';
                    break;
                case 'not-allowed':
                    errorMessage = '❌ Microphone access denied. Please enable it in browser settings.';
                    helpText = 'Click the lock icon in the address bar and allow microphone access.';
                    break;
                case 'network':
                    // Network error - could be ad blocker, no internet, or HTTPS issue
                    if (!isSecure) {
                        errorMessage = '🔒 Voice input requires HTTPS or localhost.';
                        helpText = 'Current URL: ' + window.location.protocol + '//' + window.location.host;
                        console.error('🔒 Not using HTTPS. Speech recognition requires secure context.');
                        console.error('💡 Solution: Access via https://' + window.location.host + ' or http://localhost:8000');
                    } else {
                        errorMessage = '⚠️ Voice recognition unavailable. This may be due to ad blocker or network restrictions.';
                        helpText = 'Try: 1) Disable ad blocker for this site, 2) Check internet connection, 3) Refresh page';
                        console.error('💡 Possible causes:');
                        console.error('   • Ad blocker blocking Google Speech API');
                        console.error('   • Browser extension interfering');
                        console.error('   • Network/firewall restrictions');
                        console.error('   • No internet connection');
                    }
                    break;
                case 'aborted':
                    errorMessage = '⏹️ Voice input stopped.';
                    helpText = '';
                    break;
                case 'service-not-allowed':
                    errorMessage = '🔒 Speech recognition requires HTTPS or localhost.';
                    helpText = 'Please access via: https://' + window.location.host + ' or http://localhost:8000';
                    break;
                case 'bad-grammar':
                    errorMessage = '⚠️ Speech recognition configuration error.';
                    helpText = 'Please try again or type your message.';
                    break;
                default:
                    errorMessage = '⚠️ Voice recognition error: ' + event.error;
                    helpText = 'Please try typing your message instead.';
            }
            
            showNotification(errorMessage);
            if (helpText) {
                console.log('💡 Help:', helpText);
            }
        };
        
        recognition.onend = function() {
            isListening = false;
            voiceInputButton.classList.remove('listening');
            voiceStatus.classList.add('hidden');
            console.log('🔴 Voice recognition ended');
        };
        
        // Log initial setup
        console.log('🎤 Speech Recognition initialized');
        console.log('📍 Protocol:', window.location.protocol);
        console.log('🔒 Secure context:', isSecure);
        console.log('🌐 Host:', window.location.host);
        
    } else {
        console.warn('❌ Speech recognition not supported in this browser');
        console.log('💡 Supported browsers: Chrome, Edge, Safari');
        if (voiceInputButton) {
            voiceInputButton.style.display = 'none';
        }
    }
    
    // Voice input button click handler
    if (voiceInputButton && recognition) {
        voiceInputButton.addEventListener('click', function() {
            if (isListening) {
                recognition.stop();
            } else {
                try {
                    // Start recognition directly - browser will handle permissions and connectivity
                    recognition.start();
                } catch (error) {
                    console.error('Error starting recognition:', error);
                    
                    // Handle specific errors
                    if (error.message && error.message.includes('already started')) {
                        console.log('Recognition already running, stopping first...');
                        recognition.stop();
                        setTimeout(() => {
                            try {
                                recognition.start();
                            } catch (retryError) {
                                console.error('Retry failed:', retryError);
                                showNotification('❌ Could not start voice recognition. Please try again.');
                            }
                        }, 100);
                    } else {
                        showNotification('❌ Could not start voice recognition. Please try again.');
                    }
                }
            }
        });
    } else if (voiceInputButton && !recognition) {
        // Speech recognition not supported
        voiceInputButton.style.opacity = '0.5';
        voiceInputButton.style.cursor = 'not-allowed';
        voiceInputButton.title = 'Voice input not supported in this browser';
        voiceInputButton.addEventListener('click', function() {
            showNotification('⚠️ Voice input is not supported in this browser. Please use Chrome, Edge, or Safari.');
        });
    }
    
    // Toggle speech button
    if (toggleSpeechButton) {
        // Set initial state to muted (TTS disabled by default)
        const icon = toggleSpeechButton.querySelector('i');
        icon.className = 'fas fa-volume-mute';
        toggleSpeechButton.title = 'Enable Text-to-Speech';
        
        toggleSpeechButton.addEventListener('click', function() {
            speechEnabled = !speechEnabled;
            const icon = toggleSpeechButton.querySelector('i');
            if (speechEnabled) {
                icon.className = 'fas fa-volume-up';
                toggleSpeechButton.title = 'Disable Text-to-Speech';
                showNotification('✅ Text-to-Speech enabled');
            } else {
                icon.className = 'fas fa-volume-mute';
                toggleSpeechButton.title = 'Enable Text-to-Speech';
                showNotification('🔇 Text-to-Speech disabled');
                // Stop any ongoing speech
                window.speechSynthesis.cancel();
            }
        });
    }
    
    // Text-to-Speech function
    function speakText(text) {
        if (!speechEnabled || !('speechSynthesis' in window)) {
            return;
        }
        
        // Cancel any ongoing speech
        window.speechSynthesis.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        
        utterance.onerror = function(event) {
            console.error('Speech synthesis error:', event.error);
        };
        
        window.speechSynthesis.speak(utterance);
    }
    
    // Show notification
    function showNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'chat-notification';
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }

    function focusChatInput() {
        if (!chatInput) return;
        // Ensure focus happens after the container becomes visible and layout settles
        requestAnimationFrame(() => {
            setTimeout(() => {
                try {
                    chatInput.focus();
                    // Mobile: bring input into view
                    if (typeof chatInput.scrollIntoView === 'function') {
                        chatInput.scrollIntoView({ block: 'nearest', inline: 'nearest' });
                    }
                } catch (e) {}
            }, 50);
        });
    }

    // Toggle chat window (only for widget)
    if (chatToggle) {
        chatToggle.addEventListener('click', function() {
            chatContainer.classList.toggle('hidden');

            // When opening, focus the input so user can type immediately
            const isHidden = chatContainer.classList.contains('hidden');
            if (!isHidden && chatInput) {
                try { chatToggle.blur(); } catch (e) {}
                focusChatInput();
            }
        });
    }

    // Send message when button is clicked
    sendButton.addEventListener('click', sendMessage);

    // Send message when Enter key is pressed
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        // Add user message to chat
        addMessage('user', message);
        chatInput.value = '';
        chatInput.focus();

        // Show typing indicator
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'message bot-message';
        typingIndicator.id = 'typing-indicator';
        typingIndicator.innerHTML = 'KrushiBot is typing...';
        chatMessages.appendChild(typingIndicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            // Get CSRF token from cookie (may be absent; endpoint is CSRF-exempt)
            const csrftoken = getCookie('csrftoken');

            const headers = { 'Content-Type': 'application/json' };
            if (csrftoken) {
                headers['X-CSRFToken'] = csrftoken;
            }

            const response = await fetch('/api/chat/', {
                method: 'POST',
                headers,
                body: JSON.stringify({ message: message }),
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Remove typing indicator
            const indicator = document.getElementById('typing-indicator');
            if (indicator) {
                indicator.remove();
            }

            if (data.success) {
                addMessage('bot', data.response);
                // Speak the bot's response
                speakText(data.response);
            } else {
                const errorMsg = 'Sorry, I encountered an error: ' + (data.error || 'Unknown error');
                addMessage('bot', errorMsg);
                speakText(errorMsg);
            }
        } catch (error) {
            console.error('Error:', error);
            const indicator = document.getElementById('typing-indicator');
            if (indicator) {
                indicator.remove();
            }
            const errorMsg = 'Sorry, I am unable to process your request at the moment. Please try again later.';
            addMessage('bot', errorMsg);
            speakText(errorMsg);
            console.error('Chat error details:', error.message);
        }
    }

    function addMessage(sender, text) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${sender}-message`;
        
        // For test page, add specific styling classes
        if (isTestPage) {
            messageElement.classList.add('p-2', 'mb-2', 'rounded');
            if (sender === 'user') {
                messageElement.classList.add('ml-auto', 'text-white', 'bg-success');
            } else {
                messageElement.classList.add('bg-light');
            }
        }
        
        // Add speaker icon for bot messages
        if (sender === 'bot' && speechEnabled) {
            const speakerIcon = document.createElement('button');
            speakerIcon.className = 'message-speaker-btn';
            speakerIcon.innerHTML = '<i class="fas fa-volume-up"></i>';
            speakerIcon.title = 'Replay message';
            speakerIcon.onclick = function(e) {
                e.stopPropagation();
                speakText(text);
            };
            messageElement.appendChild(speakerIcon);
        }
        
        const textSpan = document.createElement('span');
        textSpan.textContent = text;
        messageElement.appendChild(textSpan);
        
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Helper function to get CSRF token from cookies
    function getCookie(name) {
        if (!document.cookie) {
            console.warn('No cookies found');
            return null;
        }
        
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Check if this cookie name begins with the prefix we want
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                return decodeURIComponent(cookie.substring(name.length + 1));
            }
        }
        
        console.warn(`Cookie '${name}' not found`);
        return null;
    }
});
