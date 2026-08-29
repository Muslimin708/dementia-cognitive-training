import secrets
import sqlite3
import string
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

DATABASE = "dementia_app.db"
PHOTO_REFRESH_DAYS = 30


def utc_now():
    """Return the current UTC date/time in SQLite-compatible format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def get_connection():
    """Open a database connection with foreign-key enforcement enabled."""
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _column_exists(conn, table_name, column_name):
    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(column[1] == column_name for column in columns)


def _add_column_if_missing(conn, table_name, column_definition):
    column_name = column_definition.split()[0]
    if not _column_exists(conn, table_name, column_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")


def generate_patient_code(length=8):
    """Generate an easy-to-share code without ambiguous characters."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_database():
    """Create tables and safely migrate databases created by older versions."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                access_code TEXT UNIQUE,
                created_by TEXT DEFAULT 'Nursing staff',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
            );

            CREATE TABLE IF NOT EXISTS family_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                relationship TEXT,
                email TEXT,
                photo_path TEXT,
                photo_added_at TEXT,
                photo_updated_at TEXT,
                voice_path TEXT,
                voice_added_at TEXT,
                voice_updated_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS recent_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                event_name TEXT NOT NULL,
                event_date TEXT,
                description TEXT,
                photo_path TEXT,
                photo_added_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS event_family_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                family_member_id INTEGER NOT NULL,
                UNIQUE(event_id, family_member_id),
                FOREIGN KEY(event_id) REFERENCES recent_events(id) ON DELETE CASCADE,
                FOREIGN KEY(family_member_id) REFERENCES family_members(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS event_face_annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                person_name TEXT,
                description TEXT,
                x REAL,
                y REAL,
                width REAL,
                height REAL,
                FOREIGN KEY(event_id) REFERENCES recent_events(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS game_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                game_name TEXT NOT NULL,
                total_questions INTEGER NOT NULL DEFAULT 0,
                score INTEGER NOT NULL DEFAULT 0,
                total_attempts INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS email_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                family_member_id INTEGER,
                recipient_email TEXT NOT NULL,
                reminder_type TEXT NOT NULL DEFAULT 'photo_refresh',
                due_at TEXT NOT NULL,
                sent_at TEXT,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'sent', 'failed', 'cancelled')),
                error_message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE,
                FOREIGN KEY(family_member_id) REFERENCES family_members(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_family_patient
            ON family_members(patient_id);

            CREATE INDEX IF NOT EXISTS idx_events_patient
            ON recent_events(patient_id);

            CREATE INDEX IF NOT EXISTS idx_results_patient
            ON game_results(patient_id);

            CREATE INDEX IF NOT EXISTS idx_reminders_due
            ON email_reminders(status, due_at);
            """
        )

        # Migrate columns from the user's existing database without deleting data.
        patient_columns = [
            "access_code TEXT",
            "created_by TEXT DEFAULT 'Nursing staff'",
            "created_at TEXT",
            "is_active INTEGER NOT NULL DEFAULT 1",
        ]
        family_columns = [
            "email TEXT",
            "photo_added_at TEXT",
            "photo_updated_at TEXT",
            "voice_added_at TEXT",
            "voice_updated_at TEXT",
            "created_at TEXT",
        ]
        event_columns = ["photo_added_at TEXT", "created_at TEXT"]

        for definition in patient_columns:
            _add_column_if_missing(conn, "patients", definition)
        for definition in family_columns:
            _add_column_if_missing(conn, "family_members", definition)
        for definition in event_columns:
            _add_column_if_missing(conn, "recent_events", definition)

        # Assign unique access codes to patients created by the earlier version.
        patient_ids = conn.execute(
            "SELECT id FROM patients WHERE access_code IS NULL OR TRIM(access_code) = ''"
        ).fetchall()
        for (patient_id,) in patient_ids:
            code = _generate_unique_code(conn)
            conn.execute(
                "UPDATE patients SET access_code = ?, created_at = COALESCE(created_at, ?) WHERE id = ?",
                (code, utc_now(), patient_id),
            )

        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_patients_access_code "
            "ON patients(access_code)"
        )


def _generate_unique_code(conn, length=8):
    while True:
        code = generate_patient_code(length)
        exists = conn.execute(
            "SELECT 1 FROM patients WHERE access_code = ?", (code,)
        ).fetchone()
        if not exists:
            return code


# =====================================================
# PATIENT FUNCTIONS - USED BY NURSING STAFF
# =====================================================

def add_patient(name, created_by="Nursing staff", access_code=None):
    """Register a patient and return (patient_id, access_code)."""
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Patient name is required.")

    with get_connection() as conn:
        code = (access_code or _generate_unique_code(conn)).strip().upper()
        if conn.execute(
            "SELECT 1 FROM patients WHERE access_code = ?", (code,)
        ).fetchone():
            raise ValueError("This patient access code is already in use.")

        cursor = conn.execute(
            """
            INSERT INTO patients(name, access_code, created_by, created_at, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (cleaned_name, code, created_by.strip() or "Nursing staff", utc_now()),
        )
        return cursor.lastrowid, code


def get_patient_by_code(access_code):
    """Validate a code and return (id, name, access_code), or None."""
    code = (access_code or "").strip().upper()
    if not code:
        return None
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, name, access_code
            FROM patients
            WHERE access_code = ? AND is_active = 1
            """,
            (code,),
        ).fetchone()


def get_patient_id(name):
    """Compatibility helper for older interface code."""
    with get_connection() as conn:
        result = conn.execute(
            "SELECT id FROM patients WHERE name = ? AND is_active = 1 ORDER BY id LIMIT 1",
            (name.strip(),),
        ).fetchone()
        return result[0] if result else None


def get_all_patients():
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, name, access_code FROM patients WHERE is_active = 1 ORDER BY name"
        ).fetchall()


def update_patient(patient_id, name):
    with get_connection() as conn:
        conn.execute(
            "UPDATE patients SET name = ? WHERE id = ?",
            (name.strip(), patient_id),
        )


def deactivate_patient(patient_id):
    with get_connection() as conn:
        conn.execute("UPDATE patients SET is_active = 0 WHERE id = ?", (patient_id,))


# =====================================================
# FAMILY MEMBER FUNCTIONS - ACCESS THROUGH PATIENT CODE
# =====================================================

def add_family_member(patient_code, name, relationship, email=None):
    """Map a family member to the patient identified by the access code."""
    patient = get_patient_by_code(patient_code)
    if not patient:
        raise ValueError("Invalid or inactive patient access code.")

    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Family member name is required.")

    cleaned_email = (email or "").strip().lower() or None
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO family_members(
                patient_id, name, relationship, email, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (patient[0], cleaned_name, relationship, cleaned_email, utc_now()),
        )
        return cursor.lastrowid


def get_family_members(patient_id):
    """Keep the original five-column result for current games/dashboard."""
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, name, relationship, photo_path, voice_path
            FROM family_members
            WHERE patient_id = ?
            ORDER BY name
            """,
            (patient_id,),
        ).fetchall()


def get_family_members_by_code(patient_code):
    patient = get_patient_by_code(patient_code)
    if not patient:
        return []
    return get_family_members_detailed(patient[0])


def get_family_members_detailed(patient_id):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, name, relationship, email, photo_path, photo_added_at,
                   photo_updated_at, voice_path, voice_added_at, voice_updated_at
            FROM family_members
            WHERE patient_id = ?
            ORDER BY name
            """,
            (patient_id,),
        ).fetchall()


def get_family_members_with_relations(patient_id=1):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, relationship, photo_path
            FROM family_members
            WHERE patient_id = ?
            ORDER BY name
            """,
            (patient_id,),
        ).fetchall()
    return [
        {"id": row[0], "name": row[1], "relation": row[2], "photo": row[3]}
        for row in rows
    ]


def update_family_member_email(family_member_id, email):
    with get_connection() as conn:
        conn.execute(
            "UPDATE family_members SET email = ? WHERE id = ?",
            ((email or "").strip().lower() or None, family_member_id),
        )


def update_family_member_photo(family_member_id, photo_path):
    """Store the photo path and both first-upload and latest-update dates."""
    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE family_members
            SET photo_path = ?,
                photo_added_at = COALESCE(photo_added_at, ?),
                photo_updated_at = ?
            WHERE id = ?
            """,
            (photo_path, now, now, family_member_id),
        )
        _replace_photo_reminder(conn, family_member_id, now)


def update_family_member_voice(family_member_id, voice_path):
    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE family_members
            SET voice_path = ?,
                voice_added_at = COALESCE(voice_added_at, ?),
                voice_updated_at = ?
            WHERE id = ?
            """,
            (voice_path, now, now, family_member_id),
        )


def _replace_photo_reminder(conn, family_member_id, photo_updated_at):
    member = conn.execute(
        "SELECT patient_id, email FROM family_members WHERE id = ?",
        (family_member_id,),
    ).fetchone()
    if not member or not member[1]:
        return

    updated = datetime.strptime(photo_updated_at, "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=timezone.utc
    )
    due_at = (updated + timedelta(days=PHOTO_REFRESH_DAYS)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    conn.execute(
        """
        UPDATE email_reminders
        SET status = 'cancelled'
        WHERE family_member_id = ?
          AND reminder_type = 'photo_refresh'
          AND status = 'pending'
        """,
        (family_member_id,),
    )
    conn.execute(
        """
        INSERT INTO email_reminders(
            patient_id, family_member_id, recipient_email,
            reminder_type, due_at, status, created_at
        ) VALUES (?, ?, ?, 'photo_refresh', ?, 'pending', ?)
        """,
        (member[0], family_member_id, member[1], due_at, utc_now()),
    )


def delete_family_member(member_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM family_members WHERE id = ?", (member_id,))


# =====================================================
# EMAIL REMINDER FUNCTIONS
# =====================================================

def get_due_email_reminders(as_of=None):
    """Return reminders ready for an external SMTP/email sender."""
    check_time = as_of or utc_now()
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT r.id, r.recipient_email, r.reminder_type, r.due_at,
                   p.name AS patient_name, f.name AS family_member_name
            FROM email_reminders r
            JOIN patients p ON p.id = r.patient_id
            LEFT JOIN family_members f ON f.id = r.family_member_id
            WHERE r.status = 'pending' AND r.due_at <= ?
            ORDER BY r.due_at
            """,
            (check_time,),
        ).fetchall()


def mark_email_reminder_sent(reminder_id):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE email_reminders
            SET status = 'sent', sent_at = ?, error_message = NULL
            WHERE id = ?
            """,
            (utc_now(), reminder_id),
        )


def mark_email_reminder_failed(reminder_id, error_message):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE email_reminders
            SET status = 'failed', error_message = ?
            WHERE id = ?
            """,
            (str(error_message), reminder_id),
        )


def create_missing_photo_reminders():
    """Create reminders for dated photos where no pending reminder exists."""
    created = 0
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT f.id, f.patient_id, f.email,
                   COALESCE(f.photo_updated_at, f.photo_added_at)
            FROM family_members f
            WHERE f.email IS NOT NULL
              AND TRIM(f.email) <> ''
              AND COALESCE(f.photo_updated_at, f.photo_added_at) IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM email_reminders r
                  WHERE r.family_member_id = f.id
                    AND r.reminder_type = 'photo_refresh'
                    AND r.status = 'pending'
              )
            """
        ).fetchall()
        for member_id, patient_id, email, photo_date in rows:
            photo_dt = datetime.strptime(photo_date, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
            due_at = (photo_dt + timedelta(days=PHOTO_REFRESH_DAYS)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            conn.execute(
                """
                INSERT INTO email_reminders(
                    patient_id, family_member_id, recipient_email,
                    reminder_type, due_at, status, created_at
                ) VALUES (?, ?, ?, 'photo_refresh', ?, 'pending', ?)
                """,
                (patient_id, member_id, email, due_at, utc_now()),
            )
            created += 1
    return created


# =====================================================
# RECENT EVENTS
# =====================================================

def add_recent_event(
    patient_id, event_name, event_date, description, photo_path, family_member_ids
):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO recent_events(
                patient_id, event_name, event_date, description,
                photo_path, photo_added_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id,
                event_name,
                event_date,
                description,
                photo_path,
                utc_now() if photo_path else None,
                utc_now(),
            ),
        )
        event_id = cursor.lastrowid
        for family_member_id in family_member_ids or []:
            conn.execute(
                """
                INSERT OR IGNORE INTO event_family_members(event_id, family_member_id)
                VALUES (?, ?)
                """,
                (event_id, family_member_id),
            )
        return event_id


def get_recent_events(patient_id):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, event_name, event_date, description, photo_path
            FROM recent_events
            WHERE patient_id = ?
            ORDER BY event_date DESC, id DESC
            """,
            (patient_id,),
        ).fetchall()


def delete_recent_event(event_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM recent_events WHERE id = ?", (event_id,))


# =====================================================
# FACE ANNOTATIONS
# =====================================================

def add_event_face_annotation(
    event_id, person_name, description, x, y, width, height
):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO event_face_annotations(
                event_id, person_name, description, x, y, width, height
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, person_name, description, x, y, width, height),
        )


def get_event_face_annotations(event_id):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, person_name, description, x, y, width, height
            FROM event_face_annotations
            WHERE event_id = ?
            """,
            (event_id,),
        ).fetchall()


# =====================================================
# GAME RESULTS
# =====================================================

def save_game_result(
    patient_id, game_name, total_questions, score, total_attempts=None
):
    """Single compatible result function. The duplicate game_logs version is removed."""
    attempts = total_questions if total_attempts is None else total_attempts
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO game_results(
                patient_id, game_name, total_questions, score, total_attempts
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (patient_id, game_name, total_questions, score, attempts),
        )


def get_game_results(patient_id):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, game_name, total_questions, score,
                   total_attempts, completed_at
            FROM game_results
            WHERE patient_id = ?
            ORDER BY completed_at DESC, id DESC
            """,
            (patient_id,),
        ).fetchall()


if __name__ == "__main__":
    create_database()
    print("Database created or upgraded successfully.")
