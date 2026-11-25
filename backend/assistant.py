import os
import json
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker, PipelineParams
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams
)

from pipecat.services.elevenlabs.stt import (
    ElevenLabsRealtimeSTTService
)

from pipecat.services.elevenlabs.tts import (
    ElevenLabsTTSService
)

from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.llm_service import FunctionCallParams

from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import (
    SmallWebRTCTransport
)

from pipecat.workers.runner import WorkerRunner


# --------------------------------------------------
# PATH AND ENVIRONMENT CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# Import existing database functions
try:
    from .doctor_service import (
        get_all_doctors,
        get_doctors_by_specialization,
        book_appointment,
        cancel_appointment,
        get_patient_appointments,
        check_slot_availability
    )

except ImportError:
    from doctor_service import (
        get_all_doctors,
        get_doctors_by_specialization,
        book_appointment,
        cancel_appointment,
        get_patient_appointments,
        check_slot_availability
    )


# --------------------------------------------------
# SYSTEM PROMPT
# --------------------------------------------------

SYSTEM_PROMPT = """
You are NexovAI, a friendly doctor appointment voice assistant.

Your main responsibilities are:

1. Help patients find doctors.
2. Help patients check appointment availability.
3. Help patients book appointments.
4. Help patients cancel appointments.
5. Help patients check existing appointments.

COMMUNICATION RULES:

- Speak clearly and politely.
- Keep responses short and simple.
- Use English unless the patient speaks another language.
- Ask one question at a time.
- Never invent doctor details or appointment information.

BOOKING RULES:

1. Ask which doctor or specialization the patient needs.
2. Find available doctors using the doctor tool.
3. Ask for the appointment date and time.
4. Check availability before booking.
5. Ask for the patient's phone number.
6. Read the phone number back digit by digit.
7. Ask the patient to confirm the phone number.
8. Only after the patient explicitly confirms, call the booking tool.
9. Tell the patient whether booking succeeded or failed.

CANCELLATION RULES:

1. Ask for the patient's phone number.
2. Read it back digit by digit.
3. Ask the patient to confirm it.
4. Retrieve the patient's appointments.
5. Ask which appointment they want to cancel.
6. Confirm the appointment details before cancelling.
7. Only cancel after the patient explicitly agrees.

APPOINTMENT RULES:

- Never book an unavailable slot.
- Never cancel an appointment without confirmation.
- Never invent appointment IDs.
- Always report the actual result returned by the database.

IMPORTANT:

You are a doctor appointment assistant.
You are NOT a medical diagnosis system.

For medical emergencies, advise the patient to contact
emergency medical services immediately.
"""


# --------------------------------------------------
# TOOL 1: FIND DOCTORS
# --------------------------------------------------

async def find_doctors(
    params: FunctionCallParams,
    specialization: str = ""
):
    """
    Find all doctors or doctors matching a specialization.

    Args:
        specialization: Doctor specialization, such as
                        Cardiologist or Dermatologist.
                        Leave empty to find all doctors.
    """

    try:

        if specialization.strip():
            doctors = await asyncio.to_thread(
                get_doctors_by_specialization,
                specialization
            )
        else:
            doctors = await asyncio.to_thread(
                get_all_doctors
            )

        await params.result_callback({
            "doctors": json.loads(
                json.dumps(doctors, default=str)
            )
        })

    except Exception as error:

        logger.exception("Find doctors failed")

        await params.result_callback({
            "error": str(error)
        })


# --------------------------------------------------
# TOOL 2: CHECK APPOINTMENT AVAILABILITY
# --------------------------------------------------

async def check_availability(
    params: FunctionCallParams,
    doctor_id: int,
    appointment_date: str,
    appointment_time: str
):
    """
    Check whether a doctor's appointment slot is available.

    Args:
        doctor_id: Doctor ID from the doctor list.
        appointment_date: Date in YYYY-MM-DD format.
        appointment_time: Time in HH:MM:SS format.
    """

    try:

        result = await asyncio.to_thread(
            check_slot_availability,
            doctor_id,
            appointment_date,
            appointment_time
        )

        await params.result_callback({
            "availability": str(result)
        })

    except Exception as error:

        logger.exception("Availability check failed")

        await params.result_callback({
            "error": str(error)
        })


# --------------------------------------------------
# TOOL 3: BOOK APPOINTMENT
# --------------------------------------------------

async def make_appointment(
    params: FunctionCallParams,
    phone_number: str,
    doctor_id: int,
    appointment_date: str,
    appointment_time: str,
    phone_number_confirmed: bool
):
    """
    Book an appointment for a patient.

    Only call this after the patient has explicitly
    confirmed their phone number.

    Args:
        phone_number: Patient's phone number.
        doctor_id: Doctor ID.
        appointment_date: Date in YYYY-MM-DD format.
        appointment_time: Time in HH:MM:SS format.
        phone_number_confirmed: True only after the
                                patient confirms the number.
    """

    try:

        if not phone_number_confirmed:
            await params.result_callback({
                "error": "Phone number confirmation is required."
            })
            return

        result = await asyncio.to_thread(
            book_appointment,
            phone_number,
            doctor_id,
            appointment_date,
            appointment_time
        )

        await params.result_callback({
            "booking_result": str(result)
        })

    except Exception as error:

        logger.exception("Appointment booking failed")

        await params.result_callback({
            "error": str(error)
        })


# --------------------------------------------------
# TOOL 4: GET PATIENT APPOINTMENTS
# --------------------------------------------------

async def get_appointments(
    params: FunctionCallParams,
    phone_number: str
):
    """
    Retrieve appointments belonging to a patient.

    Args:
        phone_number: Patient's registered phone number.
    """

    try:

        appointments = await asyncio.to_thread(
            get_patient_appointments,
            phone_number
        )

        await params.result_callback({
            "appointments": json.loads(
                json.dumps(appointments, default=str)
            )
        })

    except Exception as error:

        logger.exception("Getting appointments failed")

        await params.result_callback({
            "error": str(error)
        })


# --------------------------------------------------
# TOOL 5: CANCEL APPOINTMENT
# --------------------------------------------------

async def cancel_patient_appointment(
    params: FunctionCallParams,
    appointment_id: int,
    phone_number: str,
    phone_number_confirmed: bool
):
    """
    Cancel an existing patient appointment.

    Only call this after the patient confirms their
    phone number and agrees to cancel the appointment.

    Args:
        appointment_id: ID of the appointment to cancel.
        phone_number: Patient's registered phone number.
        phone_number_confirmed: True only after the
                                patient confirms the number.
    """

    try:

        if not phone_number_confirmed:
            await params.result_callback({
                "error": "Phone number confirmation is required."
            })
            return

        result = await asyncio.to_thread(
            cancel_appointment,
            appointment_id,
            phone_number
        )

        await params.result_callback({
            "cancellation_result": str(result)
        })

    except Exception as error:

        logger.exception("Appointment cancellation failed")

        await params.result_callback({
            "error": str(error)
        })


# --------------------------------------------------
# CREATE AI SERVICES
# --------------------------------------------------

def create_ai_services():

    gemini_key = os.getenv("GOOGLE_API_KEY")

    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")

    voice_id = os.getenv("ELEVENLABS_VOICE_ID")


    if not gemini_key:
        raise ValueError("GOOGLE_API_KEY is missing")

    if not elevenlabs_key:
        raise ValueError("ELEVENLABS_API_KEY is missing")

    if not voice_id:
        raise ValueError("ELEVENLABS_VOICE_ID is missing")


    # Speech To Text
    stt = ElevenLabsRealtimeSTTService(
        api_key=elevenlabs_key
    )


    # Gemini LLM
    llm = GoogleLLMService(
        api_key=gemini_key,
        settings=GoogleLLMService.Settings(
            model="gemini-3.8-flash",
            system_instruction=SYSTEM_PROMPT
        ),
        retry_on_timeout=True,
        stream_idle_timeout_secs=30.0
    )


    # Text To Speech
    tts = ElevenLabsTTSService(
        api_key=elevenlabs_key,
         settings=ElevenLabsTTSService.Settings(
        voice=voice_id
    )
    )


    return stt, llm, tts


# --------------------------------------------------
# RUN VOICE ASSISTANT
# --------------------------------------------------

async def run_bot(webrtc_connection):

    logger.info("Starting NexovAI voice assistant")


    # Create WebRTC transport
    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True
        )
    )


    # Initialize AI services
    stt, llm, tts = create_ai_services()


    # Register appointment tools
    context = LLMContext(
        tools=[
            find_doctors,
            check_availability,
            make_appointment,
            get_appointments,
            cancel_patient_appointment
        ]
    )


    # Create conversation aggregators
    user_aggregator, assistant_aggregator = (
        LLMContextAggregatorPair(
            context,
            user_params=LLMUserAggregatorParams(
                vad_analyzer=SileroVADAnalyzer()
            )
        )
    )


    # Create voice pipeline
    pipeline = Pipeline([
        transport.input(),
        stt,
        user_aggregator,
        llm,
        tts,
        transport.output(),
        assistant_aggregator
    ])


    # Create pipeline worker
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True
        )
    )


    # Create worker runner
    runner = WorkerRunner(
        handle_sigint=False
    )


    await runner.add_workers(worker)


    # Browser connected event
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):

        logger.info("Browser voice client connected")

        context.add_message({
            "role": "developer",
            "content": (
                "Introduce yourself as NexovAI, "
                "a friendly doctor appointment assistant. "
                "Ask the patient how you can help."
            )
        })

        await worker.queue_frames([
            LLMRunFrame()
        ])


    # Browser disconnected event
    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):

        logger.info("Browser voice client disconnected")

        await runner.cancel()


    logger.info("NexovAI voice pipeline started")

    await runner.run()