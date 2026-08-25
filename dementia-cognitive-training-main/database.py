import sqlite3
from pathlib import Path

DATABASE_NAME = "dementia_app.db"


# =====================================================
# CONNECTION
# =====================================================

def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# =====================================================
# DATABASE SETUP
# =====================================================

def create_database():

    connection = get_connection()
    cursor = connection.cursor()

    # ---------------------------------------------
    # Patients
    # ---------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)

    # ---------------------------------------------
    # Family Members
    # ---------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            relationship TEXT NOT NULL,
            photo_path TEXT,
            voice_path TEXT,
            FOREIGN KEY (patient_id)
                REFERENCES patients(id)
                ON DELETE CASCADE
        )
    """)

    # ---------------------------------------------
    # Recognition Game Results
    # ---------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recognition_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            family_member_id INTEGER NOT NULL,
            correct INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id)
                REFERENCES patients(id),
            FOREIGN KEY (family_member_id)
                REFERENCES family_members(id)
        )
    """)

    # ---------------------------------------------
    # Memory Training Sessions
    # ---------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id)
                REFERENCES patients(id)
        )
    """)

    connection.commit()
    connection.close()


# =====================================================
# PATIENTS
# =====================================================

def add_patient(name):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO patients (name) VALUES (?)",
        (name,)
    )

    patient_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return patient_id


def get_patient_id(name):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM patients WHERE name=?",
        (name,)
    )

    result = cursor.fetchone()

    connection.close()

    if result:
        return result[0]

    return None


def get_all_patients():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name
        FROM patients
        ORDER BY name
    """)

    patients = cursor.fetchall()

    connection.close()

    return patients


def delete_patient(patient_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM patients
        WHERE id = ?
    """, (patient_id,))

    connection.commit()
    connection.close()


# =====================================================
# FAMILY MEMBERS
# =====================================================

def add_family_member(
    patient_id,
    name,
    relationship
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO family_members
        (
            patient_id,
            name,
            relationship
        )
        VALUES (?, ?, ?)
    """,
    (
        patient_id,
        name,
        relationship
    ))

    family_member_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return family_member_id


def update_family_member_photo(
    family_member_id,
    photo_path
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE family_members
        SET photo_path = ?
        WHERE id = ?
    """,
    (
        photo_path,
        family_member_id
    ))

    connection.commit()
    connection.close()


def update_family_member_voice(
    family_member_id,
    voice_path
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE family_members
        SET voice_path = ?
        WHERE id = ?
    """,
    (
        voice_path,
        family_member_id
    ))

    connection.commit()
    connection.close()


def get_family_member(
    family_member_id
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            patient_id,
            name,
            relationship,
            photo_path,
            voice_path
        FROM family_members
        WHERE id = ?
    """, (family_member_id,))

    result = cursor.fetchone()

    connection.close()

    return result


def get_family_members(
    patient_id
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            relationship,
            photo_path,
            voice_path
        FROM family_members
        WHERE patient_id = ?
        ORDER BY name
    """, (patient_id,))

    family_members = cursor.fetchall()

    connection.close()

    return family_members


def delete_family_member(
    family_member_id
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            photo_path,
            voice_path
        FROM family_members
        WHERE id = ?
    """, (family_member_id,))

    result = cursor.fetchone()

    if result:

        photo_path, voice_path = result

        if photo_path:
            photo_file = Path(photo_path)

            if photo_file.exists():
                photo_file.unlink()

        if voice_path:
            voice_file = Path(voice_path)

            if voice_file.exists():
                voice_file.unlink()

    cursor.execute("""
        DELETE FROM family_members
        WHERE id = ?
    """, (family_member_id,))

    connection.commit()
    connection.close()


# =====================================================
# MEMORY TRAINING
# =====================================================

def save_memory_score(
    patient_id,
    score
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO memory_sessions
        (
            patient_id,
            score
        )
        VALUES (?, ?)
    """,
    (
        patient_id,
        score
    ))

    connection.commit()
    connection.close()


def get_memory_scores(
    patient_id
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            score,
            created_at
        FROM memory_sessions
        WHERE patient_id = ?
        ORDER BY created_at DESC
    """, (patient_id,))

    scores = cursor.fetchall()

    connection.close()

    return scores


# =====================================================
# FACE RECOGNITION RESULTS
# =====================================================

def save_recognition_result(
    patient_id,
    family_member_id,
    correct
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO recognition_results
        (
            patient_id,
            family_member_id,
            correct
        )
        VALUES (?, ?, ?)
    """,
    (
        patient_id,
        family_member_id,
        int(correct)
    ))

    connection.commit()
    connection.close()


def get_recognition_results(
    patient_id
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            family_member_id,
            correct,
            created_at
        FROM recognition_results
        WHERE patient_id = ?
        ORDER BY created_at DESC
    """, (patient_id,))

    results = cursor.fetchall()

    connection.close()

    return results


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    create_database()

    print("Database created successfully.")