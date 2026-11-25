from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from doctor_service import (
    get_all_doctors,
    book_appointment,
    cancel_appointment,
    get_patient_appointments,
    check_slot_availability
)

from assistant import run_bot

from pipecat.transports.smallwebrtc.request_handler import (
    SmallWebRTCRequest,
    SmallWebRTCPatchRequest,
    SmallWebRTCRequestHandler
)


app = FastAPI(title="NexovAI Doctor Assistant")

webrtc_handler = SmallWebRTCRequestHandler()


class BookingRequest(BaseModel):
    phone_number: str
    doctor_id: int
    appointment_date: str
    appointment_time: str


class CancellationRequest(BaseModel):
    appointment_id: int
    phone_number: str


class AvailabilityRequest(BaseModel):
    doctor_id: int
    appointment_date: str
    appointment_time: str


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "NexovAI Doctor Assistant API is running"
    }


@app.get("/doctors")
def get_doctors():
    return get_all_doctors()


@app.post("/appointments")
def create_appointment(booking: BookingRequest):

    result = book_appointment(
        booking.phone_number,
        booking.doctor_id,
        booking.appointment_date,
        booking.appointment_time
    )

    if isinstance(result, str):
        return {"message": result}

    return {
        "message": "Appointment booked successfully",
        "appointment_id": result
    }


@app.get("/appointments/{phone_number}")
def get_appointments(phone_number: str):

    appointments = get_patient_appointments(phone_number)

    return {
        "phone_number": phone_number,
        "appointments": appointments
    }


@app.post("/appointments/cancel")
def cancel_patient_appointment(request: CancellationRequest):

    result = cancel_appointment(
        request.appointment_id,
        request.phone_number
    )

    if result:
        return {
            "message": "Appointment cancelled successfully"
        }

    return {
        "message": "Appointment not found or already cancelled"
    }


@app.post("/availability")
def check_availability(request: AvailabilityRequest):

    available = check_slot_availability(
        request.doctor_id,
        request.appointment_date,
        request.appointment_time
    )

    if available:
        return {"message": "Slot is available"}

    return {"message": "Slot already booked"}


# WebRTC voice assistant endpoint

@app.post("/api/offer")
async def handle_webrtc_offer(
    request: SmallWebRTCRequest,
    background_tasks: BackgroundTasks
):

    async def connection_callback(connection):

        background_tasks.add_task(
            run_bot,
            connection
        )

    answer = await webrtc_handler.handle_web_request(
        request=request,
        webrtc_connection_callback=connection_callback
    )

    return answer


# WebRTC ICE candidate endpoint

@app.patch("/api/offer")
async def handle_ice_candidates(
    request: SmallWebRTCPatchRequest
):

    await webrtc_handler.handle_patch_request(request)

    return {
        "status": "success"
    }


@app.on_event("shutdown")
async def shutdown_event():

    await webrtc_handler.close()