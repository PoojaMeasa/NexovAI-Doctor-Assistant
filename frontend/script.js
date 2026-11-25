// Backend API URL
const API_URL = "http://127.0.0.1:8000";

// HTML Elements
const startBtn = document.getElementById("startCallBtn");
const endBtn = document.getElementById("endCallBtn");
const statusDiv = document.getElementById("callStatus");
const statusDot = document.getElementById("statusDot");
const transcriptDiv = document.getElementById("transcript");
const doctorsList = document.getElementById("doctorsList");
const remoteAudio = document.getElementById("remoteAudio");

// WebRTC Variables
let peerConnection = null;
let localStream = null;


// Update call status
function updateStatus(message, connected = false) {
    statusDiv.innerText = message;

    statusDot.classList.toggle("offline", !connected);
}


// Load doctors from backend
async function loadDoctors() {

    try {
        const response = await fetch(`${API_URL}/doctors`);

        if (!response.ok) {
            throw new Error("Unable to fetch doctors");
        }

        const doctors = await response.json();

        doctorsList.innerHTML = "";

        if (doctors.length === 0) {
            doctorsList.innerHTML = "<p>No doctors available.</p>";
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

    <h3>${doctor.doctor_name}</h3>

    <span class="doctor-specialization">
        ${doctor.specialization}
    </span>

    <div class="doctor-details">
        <p>
            <span>📅</span>
            <strong>Available Days</strong>
        </p>
        <p>${doctor.available_days}</p>

        <p>
            <span>🕒</span>
            <strong>Available Time</strong>
        </p>
        <p>${doctor.available_time}</p>
    </div>
`;

            doctorsList.appendChild(doctorDiv);
        });

    } catch (error) {

        console.error("Doctor loading error:", error);

        doctorsList.innerHTML = `
            <p class="loading-text">
                Unable to load doctors. Please check the backend.
            </p>
        `;
    }
}


// Wait until ICE candidates are gathered
function waitForIceGathering(pc) {

    return new Promise(resolve => {

        if (pc.iceGatheringState === "complete") {
            resolve();
            return;
        }

        pc.addEventListener("icegatheringstatechange", () => {

            if (pc.iceGatheringState === "complete") {
                resolve();
            }

        });
    });
}


// Start voice call
async function startCall() {

    try {

        updateStatus("Connecting...");

        transcriptDiv.innerText =
            "Requesting microphone permission...";

        // Get microphone permission
        localStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });

        // Create WebRTC connection
        peerConnection = new RTCPeerConnection();

        // Create data channel
        peerConnection.createDataChannel("chat");

        // Add microphone audio
        localStream.getTracks().forEach(track => {

            peerConnection.addTrack(track, localStream);

        });

        // Receive assistant audio
        peerConnection.ontrack = event => {

            remoteAudio.srcObject = event.streams[0];

            remoteAudio.play().catch(error => {
                console.error("Audio playback error:", error);
            });

        };

        // Create WebRTC offer
        const offer = await peerConnection.createOffer();

        await peerConnection.setLocalDescription(offer);

        // Wait for ICE gathering
        await waitForIceGathering(peerConnection);

        // Send offer to FastAPI
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

        if (!response.ok) {
            throw new Error("WebRTC connection request failed");
        }

        // Get backend answer
        const answer = await response.json();

        await peerConnection.setRemoteDescription(answer);

        updateStatus("Connected", true);

        transcriptDiv.innerText =
            "You are connected to NexovAI. Start speaking!";

        startBtn.disabled = true;
        endBtn.disabled = false;

    } catch (error) {

        console.error("Voice connection error:", error);

        endCall();

        updateStatus("Connection Failed");

        transcriptDiv.innerText = error.message;

    }
}


// End voice call
function endCall() {

    // Close WebRTC connection
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

    // Clear remote audio
    remoteAudio.srcObject = null;

    // Update dashboard
    updateStatus("Not Connected");

    transcriptDiv.innerText = "Call ended.";

    startBtn.disabled = false;
    endBtn.disabled = true;
}


// Button events
startBtn.addEventListener("click", startCall);

endBtn.addEventListener("click", endCall);


// Load doctors when page opens
loadDoctors();