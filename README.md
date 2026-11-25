# NexovAI Doctor Assistant

NexovAI Doctor Assistant is a browser-based voice assistant designed to help patients interact with a doctor appointment system using natural speech.

Patients can speak with the assistant to find doctors, check appointment availability, book appointments, view existing appointments, and cancel appointments.

## Technologies Used

### Backend

- Python
- FastAPI
- Pipecat
- MySQL

### AI and Voice

- Google Gemini API
- ElevenLabs Speech-to-Text
- ElevenLabs Text-to-Speech
- WebRTC

### Frontend

- HTML
- CSS
- JavaScript

## Features

- Browser-based voice interaction.
- Speech recognition using ElevenLabs.
- AI-powered conversation using Google Gemini.
- Text-to-speech responses using ElevenLabs.
- View available doctors.
- Check appointment slot availability.
- Book doctor appointments.
- View patient appointments.
- Cancel appointments.
- MySQL database integration.

## Project Structure

```text
nexovai-doctor-assistant/
│
├── backend/
│   ├── main.py
│   ├── assistant.py
│   ├── db.py
│   ├── doctor_service.py
│   ├── doctors.json
│   └── test_db.py
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── .env
├── .env.example
├── .gitignore
└── README.md
```

## Prerequisites

- Python 3.11
- MySQL Server
- Google Gemini API key
- ElevenLabs API key

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/PoojaMeasa/NexovAI-Doctor-Assistant.git
cd NexovAI-Doctor-Assistant
```

### 2. Create a virtual environment

```bash
py -3.11 -m venv venv
```

### 3. Activate the virtual environment

Windows:

```bash
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file in the project root using `.env.example` as a reference.

Add your MySQL credentials, Gemini API key, ElevenLabs API key, and ElevenLabs Voice ID.

### 6. Configure MySQL

Create a database named:

```sql
CREATE DATABASE nexovai_doctor;
```

Create the required `doctors` and `appointments` tables before starting the application.

### 7. Start the backend

Open a terminal in the backend folder:

```bash
cd backend
uvicorn main:app --reload
```

Backend API:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

### 8. Start the frontend

Open `frontend/index.html` using VS Code Live Server.

The dashboard will allow you to start and end a voice call.

## Environment Variables

Refer to `.env.example` for the required configuration variables.

Never upload your actual `.env` file or API keys to GitHub.

## Author

Developed as part of an internship assignment.

## License

This project is developed for educational and internship purposes.
