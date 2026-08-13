import sqlite3


DATABASE_NAME = "dementia_app.db"


def create_database():
    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            relationship TEXT NOT NULL,
            photo_path TEXT,
            voice_path TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients (id)
        )
    """)

    connection.commit()
    connection.close()

def add_patient(name):
    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO patients (name) VALUES (?)",
        (name,)
    )

    connection.commit()
    connection.close()

def get_patient_id(name):
    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM patients WHERE name = ?",
        (name,)
    )

    result = cursor.fetchone()

    connection.close()

    if result:
        return result[0]

    return None

def add_family_member(patient_id, name, relationship):
    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO family_members
        (patient_id, name, relationship)
        VALUES (?, ?, ?)
        """,
        (patient_id, name, relationship)
    )

    family_member_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return family_member_id

def update_family_member_photo(family_member_id, photo_path):
    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE family_members
        SET photo_path = ?
        WHERE id = ?
        """,
        (photo_path, family_member_id)
    )

    connection.commit()
    connection.close()

def update_family_member_voice(family_member_id, voice_path):
    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE family_members
        SET voice_path = ?
        WHERE id = ?
        """,
        (voice_path, family_member_id)
    )

    connection.commit()
    connection.close()

def get_family_members(patient_id):
    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, name, relationship, photo_path, voice_path
        FROM family_members
        WHERE patient_id = ?
        ORDER BY name
        """,
        (patient_id,)
    )

    family_members = cursor.fetchall()

    connection.close()

    return family_members

def delete_family_member(family_member_id):
    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM family_members
        WHERE id = ?
        """,
        (family_member_id,)
    )

    connection.commit()
    connection.close()

if __name__ == "__main__":
    create_database()
    print("Database created successfully.")