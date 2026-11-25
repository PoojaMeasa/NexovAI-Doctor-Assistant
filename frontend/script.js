const API_URL = "http://127.0.0.1:8000";

const startBtn = document.getElementById("startBtn");
const endBtn = document.getElementById("endBtn");
const statusDiv = document.getElementById("status");
const transcriptDiv = document.getElementById("transcript");

let peerConnection = null;
let localStream = null;

// Load doctors
async function loadDoctors() {
    const doctorsList = document.getElementById("doctorsList");

    try {
        const response = await fetch(`${API_URL}/doctors`);

        if (!response.ok) {
            throw new Error("Unable to fetch doctors");
        }

        const doctors = await response.json();

        doctorsList.innerHTML = "";

        doctors.forEach(doctor => {
            const doctorDiv = document.createElement("div");
            doctorDiv.className = "doctor-item";

            doctorDiv.innerHTML = `
                <strong>${doctor.doctor_name}</strong><br>
                Specialization: ${doctor.specialization}<br>
                Available Days: ${doctor.available_days}<br>
                Available Time: ${doctor.available_time}
            `;

            doctorsList.appendChild(doctorDiv);
        });

    } catch (error) {
        doctorsList.innerHTML = "Unable to load doctors.";
        console.error(error);
    }
}

// Wait until browser finishes gathering ICE candidates
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
        statusDiv.innerText = "Connecting...";
        transcriptDiv.innerText = "Requesting microphone permission...";

        // Get microphone access
localStream = await navigator.mediaDevices.getUserMedia({
audio: {
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true
    }
});
        // Create WebRTC connectio  n
        peerConnection = new RTCPeerConnection();

        // Create WebRTC data channel
        peerConnection.createDataChannel("chat");
      
        // Add microphone audio to connection
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });

        // Receive assistant audio
        const remoteAudio = document.createElement("audio");
        remoteAudio.autoplay = true;

        peerConnection.ontrack = event => {
            remoteAudio.srcObject = event.streams[0];
            document.body.appendChild(remoteAudio);
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

        const answer = await response.json();

        // Set backend answer
        await peerConnection.setRemoteDescription(answer);

        statusDiv.innerText = "Connected";
        transcriptDiv.innerText = "You are connected to NexovAI. Start speaking!";

        startBtn.disabled = true;
        endBtn.disabled = false;

    } catch (error) {

        console.error("Voice connection error:", error);

        statusDiv.innerText = "Connection Failed";
        transcriptDiv.innerText = error.message;

        endCall();
    }
}

// End voice call
function endCall() {

    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }

    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localStream = null;
    }

    statusDiv.innerText = "Not Connected";
    transcriptDiv.innerText = "Call ended.";

    startBtn.disabled = false;
    endBtn.disabled = true;
}

// Button events
startBtn.addEventListener("click", startCall);
endBtn.addEventListener("click", endCall);

// Load doctors when page opens
loadDoctors();