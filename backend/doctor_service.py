from datetime import timedelta

try:
    from .db import get_db_connection
except ImportError:
    from db import get_db_connection


def get_all_doctors():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM doctors")
        doctors = cursor.fetchall()

        return doctors

    finally:
        cursor.close()
        connection.close()


def get_doctors_by_specialization(specialization):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT * FROM doctors
            WHERE specialization LIKE %s
        """

        cursor.execute(query, (f"%{specialization}%",))
        doctors = cursor.fetchall()

        return doctors

    finally:
        cursor.close()
        connection.close()


def book_appointment(
    phone_number,
    doctor_id,
    appointment_date,
    appointment_time
):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT doctor_id
            FROM doctors
            WHERE doctor_id = %s
            FOR UPDATE
            """,
            (doctor_id,)
        )

        doctor = cursor.fetchone()

        if not doctor:
            connection.rollback()
            return "Doctor not found"

        query = """
            SELECT COUNT(*)
            FROM appointments
            WHERE doctor_id = %s
            AND appointment_date = %s
            AND appointment_time = %s
            AND status = 'BOOKED'
        """

        cursor.execute(
            query,
            (doctor_id, appointment_date, appointment_time)
        )

        count = cursor.fetchone()[0]

        if count > 0:
            connection.rollback()
            return "Slot already booked"

        insert_query = """
            INSERT INTO appointments
            (
                phone_number,
                doctor_id,
                appointment_date,
                appointment_time
            )
            VALUES (%s, %s, %s, %s)
        """

        cursor.execute(
            insert_query,
            (
                phone_number,
                doctor_id,
                appointment_date,
                appointment_time
            )
        )

        appointment_id = cursor.lastrowid

        connection.commit()

        return appointment_id

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def cancel_appointment(appointment_id, phone_number):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        query = """
            UPDATE appointments
            SET status = 'CANCELLED'
            WHERE appointment_id = %s
            AND phone_number = %s
            AND status = 'BOOKED'
        """

        cursor.execute(
            query,
            (appointment_id, phone_number)
        )

        connection.commit()

        return cursor.rowcount > 0

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def get_patient_appointments(phone_number):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                a.*,
                d.doctor_name,
                d.specialization
            FROM appointments a
            JOIN doctors d
                ON a.doctor_id = d.doctor_id
            WHERE a.phone_number = %s
        """

        cursor.execute(query, (phone_number,))

        appointments = cursor.fetchall()

        for appointment in appointments:
            appointment_time = appointment["appointment_time"]

            if isinstance(appointment_time, timedelta):
                total_seconds = int(
                    appointment_time.total_seconds()
                )

                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60

                appointment["appointment_time"] = (
                    f"{hours:02}:{minutes:02}:{seconds:02}"
                )

        return appointments

    finally:
        cursor.close()
        connection.close()


def check_slot_availability(
    doctor_id,
    appointment_date,
    appointment_time
):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        query = """
            SELECT COUNT(*)
            FROM appointments
            WHERE doctor_id = %s
            AND appointment_date = %s
            AND appointment_time = %s
            AND status = 'BOOKED'
        """

        cursor.execute(
            query,
            (doctor_id, appointment_date, appointment_time)
        )

        count = cursor.fetchone()[0]

        return count == 0

    finally:
        cursor.close()
        connection.close()