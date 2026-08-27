import sqlite3

DATABASE = "dementia_app.db"


def get_connection():
    return sqlite3.connect(DATABASE)


# =====================================================
# DATABASE CREATION
# =====================================================

def create_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS family_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        relationship TEXT,
        photo_path TEXT,
        voice_path TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recent_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        event_name TEXT NOT NULL,
        event_date TEXT,
        description TEXT,
        photo_path TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS event_family_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        family_member_id INTEGER NOT NULL,
        FOREIGN KEY(event_id) REFERENCES recent_events(id),
        FOREIGN KEY(family_member_id) REFERENCES family_members(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS event_face_annotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        person_name TEXT,
        description TEXT,
        x REAL,
        y REAL,
        width REAL,
        height REAL,
        FOREIGN KEY(event_id) REFERENCES recent_events(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS game_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        game_name TEXT NOT NULL,
        total_questions INTEGER,
        score INTEGER,
        total_attempts INTEGER,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    )
    """)

    conn.commit()
    conn.close()


# =====================================================
# PATIENT FUNCTIONS
# =====================================================

def add_patient(name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO patients(name)
    VALUES(?)
    """, (name,))

    conn.commit()
    conn.close()


def get_patient_id(name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id
    FROM patients
    WHERE name=?
    """, (name,))

    result = cursor.fetchone()

    conn.close()

    if result:
        return result[0]

    return None


def get_all_patients():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM patients
    ORDER BY name
    """)

    results = cursor.fetchall()

    conn.close()

    return results


# =====================================================
# FAMILY MEMBER FUNCTIONS
# =====================================================

def add_family_member(
        patient_id,
        name,
        relationship
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO family_members
    (
        patient_id,
        name,
        relationship
    )
    VALUES (?, ?, ?)
    """, (
        patient_id,
        name,
        relationship
    ))

    member_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return member_id


def update_family_member_photo(
        family_member_id,
        photo_path
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE family_members
    SET photo_path=?
    WHERE id=?
    """, (
        photo_path,
        family_member_id
    ))

    conn.commit()
    conn.close()


def update_family_member_voice(
        family_member_id,
        voice_path
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE family_members
    SET voice_path=?
    WHERE id=?
    """, (
        voice_path,
        family_member_id
    ))

    conn.commit()
    conn.close()


def get_family_members(patient_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        name,
        relationship,
        photo_path,
        voice_path
    FROM family_members
    WHERE patient_id=?
    ORDER BY name
    """, (patient_id,))

    results = cursor.fetchall()

    conn.close()

    return results


def delete_family_member(member_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM family_members
    WHERE id=?
    """, (member_id,))

    conn.commit()
    conn.close()


# =====================================================
# RECENT EVENTS
# =====================================================

def add_recent_event(
        patient_id,
        event_name,
        event_date,
        description,
        photo_path,
        family_member_ids
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO recent_events
    (
        patient_id,
        event_name,
        event_date,
        description,
        photo_path
    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        patient_id,
        event_name,
        event_date,
        description,
        photo_path
    ))

    event_id = cursor.lastrowid

    for family_member_id in family_member_ids:
        cursor.execute("""
        INSERT INTO event_family_members
        (
            event_id,
            family_member_id
        )
        VALUES (?, ?)
        """, (
            event_id,
            family_member_id
        ))

    conn.commit()
    conn.close()

    return event_id


def get_recent_events(patient_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        event_name,
        event_date,
        description,
        photo_path
    FROM recent_events
    WHERE patient_id=?
    ORDER BY event_date DESC
    """, (patient_id,))

    results = cursor.fetchall()

    conn.close()

    return results


def delete_recent_event(event_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM event_face_annotations
    WHERE event_id=?
    """, (event_id,))

    cursor.execute("""
    DELETE FROM event_family_members
    WHERE event_id=?
    """, (event_id,))

    cursor.execute("""
    DELETE FROM recent_events
    WHERE id=?
    """, (event_id,))

    conn.commit()
    conn.close()


# =====================================================
# FACE ANNOTATIONS
# =====================================================

def add_event_face_annotation(
        event_id,
        person_name,
        description,
        x,
        y,
        width,
        height
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO event_face_annotations
    (
        event_id,
        person_name,
        description,
        x,
        y,
        width,
        height
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        event_id,
        person_name,
        description,
        x,
        y,
        width,
        height
    ))

    conn.commit()
    conn.close()


def get_event_face_annotations(event_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        person_name,
        description,
        x,
        y,
        width,
        height
    FROM event_face_annotations
    WHERE event_id=?
    """, (event_id,))

    results = cursor.fetchall()

    conn.close()

    return results


# =====================================================
# GAME RESULTS
# =====================================================

def save_game_result(
        patient_id,
        game_name,
        total_questions,
        score,
        total_attempts
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO game_results
    (
        patient_id,
        game_name,
        total_questions,
        score,
        total_attempts
    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        patient_id,
        game_name,
        total_questions,
        score,
        total_attempts
    ))

    conn.commit()
    conn.close()


def get_game_results(patient_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        game_name,
        total_questions,
        score,
        total_attempts,
        completed_at
    FROM game_results
    WHERE patient_id=?
    ORDER BY completed_at DESC
    """, (patient_id,))

    results = cursor.fetchall()

    conn.close()

    return results


# =====================================================
# TEST RUN
# =====================================================

if __name__ == "__main__":
    create_database()
    print("✅ Database created successfully")