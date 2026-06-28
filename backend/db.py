"""
Database module - do not modify. All storage is handled here.
Your app.py should use these functions only; you will not write any SQL.

Each student is a dict: {"id": int, "name": str, "course": str, "mark": int}.
"""

import os
import psycopg2


def _connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def get_all_students():
    """
    Fetch all students from the database.
    Returns: list of dicts [{"id": 1, "name": "...", "course": "...", "mark": 78}, ...]
    """
    conn = _connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, course, mark FROM students ORDER BY id;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "name": r[1], "course": r[2], "mark": r[3]} for r in rows]


def get_student_by_id(student_id):
    """
    Fetch one student by id.
    Parameters: student_id (int)
    Returns: dict or None if not found
    """
    conn = _connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, course, mark FROM students WHERE id = %s;", (student_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "name": row[1], "course": row[2], "mark": row[3]}


def insert_student(name, course, mark):
    """
    Insert a new student. Parameters: name (str), course (str), mark (int).
    Returns: dict of the new student including id.
    """
    conn = _connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO students (name, course, mark) VALUES (%s, %s, %s) RETURNING id, name, course, mark;",
        (name, course, mark),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {"id": row[0], "name": row[1], "course": row[2], "mark": row[3]}


def update_student(student_id, name=None, course=None, mark=None):
    """
    Update a student. Parameters: student_id (int), and optionally name, course, mark.
    Returns: updated student dict or None if not found.
    """
    existing = get_student_by_id(student_id)
    if not existing:
        return None
    new_name = name if name is not None and name != "" else existing["name"]
    new_course = course if course is not None and course != "" else existing["course"]
    new_mark = mark if mark is not None else existing["mark"]
    conn = _connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE students SET name = %s, course = %s, mark = %s WHERE id = %s RETURNING id, name, course, mark;",
        (new_name, new_course, new_mark, student_id),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {"id": row[0], "name": row[1], "course": row[2], "mark": row[3]}


def delete_student(student_id):
    """
    Delete a student by id.
    Parameters: student_id (int)
    Returns: {"id": student_id} if deleted, or None if not found.
    """
    conn = _connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE id = %s RETURNING id;", (student_id,))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not row:
        return None
    return {"id": row[0]}
