// Backend API URL
const API_URL = "http://127.0.0.1:8000";

// HTML Elements
const startCallBtn = document.getElementById("startCallBtn");
const endCallBtn = document.getElementById("endCallBtn");

const callStatus = document.getElementById("callStatus");
const statusDot = document.getElementById("statusDot");

const transcript = document.getElementById("transcript");
const doctorsList = document.getElementById("doctorsList");

const remoteAudio = document.getElementById("remoteAudio");

// WebRTC Variables
let peerConnection = null;
let localStream = null;
let dataChannel = null;

// Change connection status
function updateStatus(message, statusClass = "") {
    callStatus.textContent = message;

    statusDot.className = "status-dot";

    if (statusClass) {
        statusDot.classList.add(statusClass);
    }
}

// Add conversation message
function addMessage(message, sender) {
    if (!message || !String(message).trim()) {
        return;
    }

    const emptyMessage = transcript.querySelector(".empty-transcript");

    if (emptyMessage) {
        emptyMessage.remove();
    }

    const messageDiv = document.createElement("div");
    messageDiv.className = `transcript-message ${sender}`;

    const label = document.createElement("span");
    label.className = "message-label";
    label.textContent = sender === "user" ? "YOU" : "NEXOVAI";

    const messageText = document.createElement("div");
    messageText.textContent = message;

    messageDiv.appendChild(label);
    messageDiv.appendChild(messageText);

    transcript.appendChild(messageDiv);

    transcript.scrollTop = transcript.scrollHeight;
}

// Reset conversation
function resetTranscript() {
    transcript.innerHTML = `
        <div class="empty-transcript">
            <div>💬</div>
            <h3>No conversation yet</h3>
            <p>
                Start a voice call to begin talking
                with NexovAI.
            </p>
        </div>
    `;
}

// Load Doctors from Backend
async function loadDoctors() {
    doctorsList.innerHTML = `
        <p class="loading-text">Loading doctors...</p>
    `;

    try {
        const response = await fetch(`${API_URL}/doctors`);

        if (!response.ok) {
            throw new Error("Unable to load doctors");
        }

        const doctors = await response.json();

        doctorsList.innerHTML = "";

        if (!Array.isArray(doctors) || doctors.length === 0) {
            doctorsList.innerHTML = `
                <p class="loading-text">No doctors available.</p>
            `;
            return;
        }

        doctors.forEach(doctor => {
            const doctorDiv = document.createElement("div");

            doctorDiv.className = "doctor-card";

            doctorDiv.innerHTML = `
                <div class="doctor-top">
                    <div class="doctor-avatar">👨‍⚕️</div>
                    <span class="doctor-availability">Available</span>
                </div>

                <h3></h3>
                <span class="doctor-specialization"></span>

                <div class="doctor-details">
                    <p>📅 <strong>Available Days</strong></p>
                    <p class="doctor-days"></p>

                    <p>🕒 <strong>Available Time</strong></p>
                    <p class="doctor-time"></p>
                </div>
            `;

            doctorDiv.querySelector("h3").textContent =
                doctor.doctor_name || "Doctor";

            doctorDiv.querySelector(".doctor-specialization").textContent =
                doctor.specialization || "General";

            doctorDiv.querySelector(".doctor-days").textContent =
                doctor.available_days || "Contact for details";

            doctorDiv.querySelector(".doctor-time").textContent =
                doctor.available_time || "Contact for details";

            doctorsList.appendChild(doctorDiv);
        });

    } catch (error) {
        console.error("Doctor loading error:", error);

        doctorsList.innerHTML = `
            <p class="error-text">
                Unable to load doctors.
                Please check whether the backend is running.
            </p>
        `;
    }
}

// Wait for ICE Gathering
function waitForICEGathering(connection) {
    return new Promise(resolve => {
        if (connection.iceGatheringState === "complete") {
            resolve();
            return;
        }

        function checkState() {
            if (connection.iceGatheringState === "complete") {
                connection.removeEventListener(
                    "icegatheringstatechange",
                    checkState
                );

                resolve();
            }
        }

        connection.addEventListener(
            "icegatheringstatechange",
            checkState
        );

        // Prevent waiting forever
        setTimeout(() => {
            connection.removeEventListener(
                "icegatheringstatechange",
                checkState
            );

            resolve();
        }, 10000);
    });
}

// Handle incoming Data Channel Messages
function handleDataChannelMessage(event) {
    try {
        const message = JSON.parse(event.data);

console.log("Received message:", JSON.stringify(message, null, 2));
        // Handle NexovAI transcript messages
        if (message.type === "transcript") {
            if (message.role === "user") {
                addMessage(message.text, "user");
            } else if (message.role === "assistant") {
                addMessage(message.text, "assistant");
            }

            return;
        }

        // Handle other message formats
        const text =
            message.text ||
            message.message ||
            message.content ||
            message.data?.text ||
            "";

        if (!text) {
            return;
        }

        const type = message.type || "";

        if (
            type.includes("user-transcription") ||
            type.includes("user_transcription") ||
            type.includes("transcription")
        ) {
            addMessage(text, "user");
        } else if (
            type.includes("bot-llm-text") ||
            type.includes("assistant") ||
            type.includes("bot")
        ) {
            addMessage(text, "assistant");
        }

    } catch (error) {
        console.error("Data channel message error:", error);
    }
}

// Start Voice Call
async function startCall() {
    try {
        startCallBtn.disabled = true;

        updateStatus("Connecting...", "connecting");

        resetTranscript();

        // Get microphone permission
        localStream = await navigator.mediaDevices.getUserMedia({
            audio: true
        });

        // Create Peer Connection
        peerConnection = new RTCPeerConnection();

        // Add microphone audio tracks
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });

        // Create Data Channel
        dataChannel = peerConnection.createDataChannel("chat");

        dataChannel.onopen = () => {
            console.log("Data channel connected");
        };

        dataChannel.onmessage = handleDataChannelMessage;

        // Receive AI audio - Debugging added
        peerConnection.ontrack = event => {
            console.log("AI audio track received:", event.track.kind);
            console.log("Remote audio stream:", event.streams[0]);

            remoteAudio.srcObject = event.streams[0];

            remoteAudio.autoplay = true;
            remoteAudio.playsInline = true;

            remoteAudio.play().then(() => {
                console.log("AI audio playback started successfully");
            }).catch(error => {
                console.error("Audio playback error:", error);
            });
        };

        // Monitor connection
        peerConnection.onconnectionstatechange = () => {
            console.log(
                "Connection state:",
                peerConnection.connectionState
            );

            if (peerConnection.connectionState === "connected") {
                updateStatus("Connected", "connected");

                startCallBtn.disabled = true;
                endCallBtn.disabled = false;
            }

            if (
                peerConnection.connectionState === "failed" ||
                peerConnection.connectionState === "disconnected"
            ) {
                updateStatus("Connection Lost", "error");
            }

            if (peerConnection.connectionState === "closed") {
                updateStatus("Not Connected");
            }
        };

        // Create WebRTC Offer
        const offer = await peerConnection.createOffer();

        await peerConnection.setLocalDescription(offer);

        // Wait for ICE candidates
        await waitForICEGathering(peerConnection);

        // Send offer to FastAPI backend
        console.log("Sending WebRTC offer to:", `${API_URL}/api/offer`);
        const response = await fetch(`${API_URL}/api/offer`, {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                sdp: peerConnection.localDescription.sdp,
                type: peerConnection.localDescription.type
            })
        });
        console.log("Backend response status:", response.status);

        if (!response.ok) {
            const errorText = await response.text();

            throw new Error(
                `Backend error: ${response.status} ${errorText}`
            );
        }

        // Receive backend answer
        const answer = await response.json();

        const remoteDescription = answer.answer || answer;

        if (!remoteDescription.sdp || !remoteDescription.type) {
            throw new Error("Invalid WebRTC answer received from backend.");
        }

        await peerConnection.setRemoteDescription(
            new RTCSessionDescription(remoteDescription)
        );

        console.log("WebRTC connection established");

        endCallBtn.disabled = false;

    } catch (error) {
        console.error("Voice call error:", error);

        updateStatus("Connection Failed", "error");

        alert(
            "Unable to start the voice assistant. Please check your backend and microphone permission."
        );

        endCall();
    }
}

// End Voice Call
function endCall() {
    console.log("Ending voice call");

    // Close Data Channel
    if (dataChannel) {
        dataChannel.close();
        dataChannel = null;
    }

    // Close Peer Connection
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }

    // Stop microphone
    if (localStream) {
        localStream.getTracks().forEach(track => {
            track.stop();
        });

        localStream = null;
    }

    // Stop remote audio
    remoteAudio.pause();
    remoteAudio.srcObject = null;

    // Update buttons
    startCallBtn.disabled = false;
    endCallBtn.disabled = true;

    // Update status
    updateStatus("Not Connected");
}

// Button Events
startCallBtn.addEventListener("click", startCall);

endCallBtn.addEventListener("click", endCall);

// Load Doctors when page opens
document.addEventListener("DOMContentLoaded", () => {
    loadDoctors();
});