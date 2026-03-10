/**
 * Voice Recognition Diagnostic Tool
 * Run this in browser console to diagnose speech recognition issues
 */

function runVoiceDiagnostic() {
    console.log('='.repeat(60));
    console.log('🔍 VOICE RECOGNITION DIAGNOSTIC TOOL');
    console.log('='.repeat(60));
    
    // Check 1: Browser Support
    console.log('\n1️⃣ Checking Browser Support...');
    const hasWebkit = 'webkitSpeechRecognition' in window;
    const hasStandard = 'SpeechRecognition' in window;
    const supported = hasWebkit || hasStandard;
    
    if (supported) {
        console.log('✅ Speech Recognition API is supported');
        console.log('   Implementation:', hasWebkit ? 'webkit' : 'standard');
    } else {
        console.log('❌ Speech Recognition API is NOT supported');
        console.log('💡 Try using Chrome, Edge, or Safari');
        return;
    }
    
    // Check 2: Secure Context
    console.log('\n2️⃣ Checking Secure Context...');
    console.log('   Protocol:', window.location.protocol);
    console.log('   Hostname:', window.location.hostname);
    console.log('   Full URL:', window.location.href);
    
    const isHTTPS = window.location.protocol === 'https:';
    const isLocalhost = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1';
    const isSecure = isHTTPS || isLocalhost;
    
    if (isSecure) {
        console.log('✅ Secure context detected');
        if (isHTTPS) console.log('   Using HTTPS ✓');
        if (isLocalhost) console.log('   Using localhost ✓');
    } else {
        console.log('❌ NOT in secure context');
        console.log('⚠️  Speech recognition requires HTTPS or localhost');
        console.log('💡 Solution: Access via https://' + window.location.host);
    }
    
    // Check 3: Permissions API
    console.log('\n3️⃣ Checking Microphone Permissions...');
    if (navigator.permissions) {
        navigator.permissions.query({ name: 'microphone' })
            .then(result => {
                console.log('   Permission state:', result.state);
                if (result.state === 'granted') {
                    console.log('✅ Microphone permission granted');
                } else if (result.state === 'prompt') {
                    console.log('⚠️  Microphone permission not yet requested');
                    console.log('💡 Click the microphone button to request permission');
                } else {
                    console.log('❌ Microphone permission denied');
                    console.log('💡 Click the lock icon in address bar to change');
                }
            })
            .catch(err => {
                console.log('⚠️  Could not check permissions:', err.message);
            });
    } else {
        console.log('⚠️  Permissions API not available');
    }
    
    // Check 4: MediaDevices API
    console.log('\n4️⃣ Checking MediaDevices API...');
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        console.log('✅ getUserMedia is available');
        
        // Try to enumerate devices
        if (navigator.mediaDevices.enumerateDevices) {
            navigator.mediaDevices.enumerateDevices()
                .then(devices => {
                    const audioInputs = devices.filter(d => d.kind === 'audioinput');
                    console.log('   Audio input devices found:', audioInputs.length);
                    audioInputs.forEach((device, i) => {
                        console.log(`   ${i + 1}. ${device.label || 'Microphone ' + (i + 1)}`);
                    });
                    if (audioInputs.length === 0) {
                        console.log('❌ No microphone detected');
                        console.log('💡 Please connect a microphone');
                    }
                })
                .catch(err => {
                    console.log('⚠️  Could not enumerate devices:', err.message);
                });
        }
    } else {
        console.log('❌ getUserMedia is NOT available');
    }
    
    // Check 5: Internet Connection
    console.log('\n5️⃣ Checking Internet Connection...');
    console.log('   Online status:', navigator.onLine ? '✅ Online' : '❌ Offline');
    
    // Test connection to Google
    fetch('https://www.google.com/favicon.ico', { 
        mode: 'no-cors',
        cache: 'no-cache'
    })
        .then(() => {
            console.log('✅ Can reach Google servers');
        })
        .catch(err => {
            console.log('❌ Cannot reach Google servers');
            console.log('   Error:', err.message);
            console.log('💡 Check firewall or VPN settings');
        });
    
    // Check 6: Test Speech Recognition
    console.log('\n6️⃣ Testing Speech Recognition...');
    try {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const testRecognition = new SpeechRecognition();
        console.log('✅ Can create SpeechRecognition instance');
        console.log('   Properties:');
        console.log('   - lang:', testRecognition.lang);
        console.log('   - continuous:', testRecognition.continuous);
        console.log('   - interimResults:', testRecognition.interimResults);
        console.log('   - maxAlternatives:', testRecognition.maxAlternatives);
    } catch (err) {
        console.log('❌ Cannot create SpeechRecognition instance');
        console.log('   Error:', err.message);
    }
    
    // Summary
    console.log('\n' + '='.repeat(60));
    console.log('📊 DIAGNOSTIC SUMMARY');
    console.log('='.repeat(60));
    
    const issues = [];
    const solutions = [];
    
    if (!supported) {
        issues.push('Browser does not support Speech Recognition');
        solutions.push('Use Chrome, Edge, or Safari browser');
    }
    
    if (!isSecure) {
        issues.push('Not using HTTPS or localhost');
        solutions.push('Access via: https://' + window.location.host);
        solutions.push('Or use: http://localhost:8000');
    }
    
    if (!navigator.onLine) {
        issues.push('No internet connection detected');
        solutions.push('Check your internet connection');
    }
    
    if (issues.length === 0) {
        console.log('✅ No obvious issues detected');
        console.log('💡 If voice recognition still fails:');
        console.log('   1. Click microphone button and grant permission');
        console.log('   2. Speak clearly within 3-5 seconds');
        console.log('   3. Check browser console for errors');
        console.log('   4. Try reloading the page');
    } else {
        console.log('❌ Issues Found:');
        issues.forEach((issue, i) => {
            console.log(`   ${i + 1}. ${issue}`);
        });
        console.log('\n💡 Solutions:');
        solutions.forEach((solution, i) => {
            console.log(`   ${i + 1}. ${solution}`);
        });
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('📝 To test voice recognition:');
    console.log('   1. Click the microphone button in the chat');
    console.log('   2. Allow microphone access when prompted');
    console.log('   3. Speak your message clearly');
    console.log('   4. Check console for any errors');
    console.log('='.repeat(60));
}

// Auto-run diagnostic
console.log('💡 Voice Recognition Diagnostic Tool loaded');
console.log('💡 Run: runVoiceDiagnostic() to check your setup');

// Export for use
if (typeof window !== 'undefined') {
    window.runVoiceDiagnostic = runVoiceDiagnostic;
}
