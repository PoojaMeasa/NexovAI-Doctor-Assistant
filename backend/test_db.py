from doctor_service import book_appointment

result = book_appointment(
    "9123456780",
    1,
    "2026-11-27",
    "11:00:00"
)

print("Booking Result:", result)