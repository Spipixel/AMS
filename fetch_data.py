import os
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from fastapi import HTTPException
from globalVAR import *

students = tables[0]
teachers = tables[1]
courses = tables[2]
enrollments = tables[3]
login_t = tables[4]
logged_t = tables[5]

SCHEMA = {
    courses: {
        "course_name": {
            "type": str,
            "max_len": 180,
            "required": True
        },
        "teacher_id": {
            "type": int,
            "required": True
        },
        "replacement_teacher_id": {
            "type": int,
            "required": True
        },
        "start_time": {
            "type": str,
            "required": True
        },
        "end_time": {
            "type": str,
            "required": True            
        },
        "seat_capacity": {
            "type": int,
            "max_len": 200,
            "required": True
        },
        "fee_amount": {
            "type": float,
            "required": True
        },
        "schedule_days": {
            "type": str,
            "required": True
        },
        "duration_months": {
            "type": int,
            "required": True
        },
        "start_date": {
            "type": str,
            "required": True
        }, 
        "end_date": {
            "type": str,
            "required": True
        },
        "status": {
            "type": str,
            "required": True
        }
    },
    students: {
        "student_name": {
            "type": str,
            "max_len": 100,
            "required": True
        },
        "phone": {
            "type": str,
            "max_len": 10,
            "required": True
        },
        "email": {
            "type": str,
            "max_len": 200,
            "required": True
        },
        "address": {
            "type": str,
            "max_len": 255,
            "required": True
        },
        "status": {
            "type": str,
            "required": True
        }
    },
    teachers: {
        "teacher_name": {
            "type": str,
            "max_len": 100,
            "required": True
        },
        "specialised": {
            "type": str,
            "max_len": 255,
            "required": True
        },
        "salary": {
            "type": float,
            "required": True
        },
        "status": {
            "type": str,
            "required": True
        }
    },
    enrollments: {
        "student_id": {
            "type": int,
            "required": True
        },
        "course_id": {
            "type": int,
            "required": True
        },
        "enrollment_date": {
            "type": str,
            "required": True
        },
        "status": {
            "type": str,
            "required": True
        }
    }
}

def connect():
    try:
        conn = mysql.connector.connect(
            host = HOST,
            port = PORT,
            user = USER,
            password = PASSWORD,
            database = DB,
            connection_timeout=5
        )
    
        if conn.is_connected():
            return [1, conn]
        
    except KeyError as exc:
        return [0, exc, "keyerror"]
    except Error as exc:
        return [0, exc, "mysql_error"]

from datetime import datetime

def authentication(conn, username, password):
    try:
        cursor = conn.cursor()        
        query = f"SELECT id FROM {login_t} WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))
        result = cursor.fetchone()
        
        if result is not None:
            user_id = result[0]
            if isinstance(user_id, int) and user_id > 0:
                now = datetime.now()
                current_date = now.date()
                current_time = now.time().strftime('%H:%M:%S')
                
                log_query = f"""
                    INSERT INTO {logged_t} (admin_id, logged_date, logged_time) 
                    VALUES (%s, %s, %s)
                """
                cursor.execute(log_query, (user_id, current_date, current_time))
                log_id = cursor.lastrowid
                
                conn.commit()
                cursor.close()
                
                return [1, "success", log_id]
        
        cursor.close()
        return [0, "failed", "Logged_in failed"]

    except Error as exc:
        try:
            conn.rollback()
        except:
            pass
        return [0, str(exc), "MYSQL_ERR"]


def data_validation(tablename,data):
    if tablename not in SCHEMA:
        return [0,"ERR_UNKNOWN_TABLE"]

    rules = SCHEMA[tablename]

    if not isinstance(data,dict):
        return [0, "ERR_INVALID_DATA"]

    extra = set(data) - set(rules)
    missing = {
        col for col, rule in rules.items()
        if rule.get("required") and col not in data
    }

    if extra:
        return [0, f"ERR_UNKNOWN_COLUMNS: {extra}"]

    if missing:
        return [0, f"ERR_MISSING_COLUMNS: {missing}"]

    for column, rule in rules.items():
        value = data.get(column)

        if rule.get('required', False) and value is None:
            return [0,f"ERR_REQUIRED_{column.upper()}"]

        if value is not None:
            excepted_type = rule.get('type', str)
            try:
                data[column] = excepted_type(value)
                if rule.get('max_len') != None:
                    if isinstance(value,int) or isinstance(value,float):
                        if rule['max_len'] < value:
                            return [0,f"ERR_LARGE_{column.upper()}_VALUE: {value}, REQUIRED_VALUE: {rule['max_len']}"]
                    elif isinstance(value,str):
                        if len(value) > rule['max_len']:
                            return [0,f"ERR_LARGE_{column.upper()}_VALUE: {value}, REQUIRED_VALUE: {rule['max_len']}"]
                

            except (ValueError, TypeError):
                return [0, f"ERR_INVALID_DATA_TYPE\nField '{column}' requires {excepted_type.__name__}."]

    return [1,data]

def get_format(conn,tablename):
    try:
        raw_data = get_data(conn,tablename)
        

        if raw_data[0] != 1:
            raise HTTPException(
                status_code=500,
                detail="Failed to fetch courses"
            )

        return raw_data[1]

    finally:
        close_connection(conn)

def get_enrollments(conn):
    try:
        cursor = conn.cursor()
        query = (
            "select e.id, s.student_name, c.course_name, e.enrollment_date "
            "from enrollments as e "
            "join students as s on s.id = e.student_id "
            "join courses as c on c.id = e.course_id"
        )
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        return [1,result]
    except Error as exc:
        return [0,exc, "Mysql_err"]



def get_enrolled_student_details(conn, student_id):
    try:
        cursor = conn.cursor()
        # 1. Added quotes to make the query a valid Python string
        query = (
            "SELECT e.id, s.student_name, c.course_name, e.enrollment_date "
            "FROM enrollments AS e "
            "JOIN students AS s ON s.id = e.student_id "
            "JOIN courses AS c ON c.id = e.course_id "
            "WHERE e.student_id = %s"
        )
        # 2. Passed student_id as a tuple (student_id,)
        cursor.execute(query, (student_id,)) 
        result = cursor.fetchall()
        cursor.close()
        return [1, result]
    except Error as exc: 
        # 3. Removed the undefined Mysql_err variable
        return [0, exc] 


def get_db_details(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("select database(),version()")
        result = cursor.fetchone()
        cursor.close()

        return [1, result]
    except Error as exc:
        return [0, exc, "mysql_error"]

def get_data(conn, tablename):
    cursor = None

    if tablename not in SCHEMA:
        return [0, "ERR_UNKNOWN_TABLE"]

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM {tablename}")
        data = cursor.fetchall()

        return [1, data]

    except Error as exc:
        return [0, exc, "mysql_error"]

    finally:
        if cursor is not None:
            cursor.close()

def get_row(conn, tablename, id):
    cursor = None

    if tablename not in SCHEMA:
        return [0, "ERR_UNKNOWN_TABLE"]

    if not isinstance(id,int):
        return [0, "ERR_INVALID_ARGUMENT"]

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        query = f"SELECT * FROM `{tablename}` WHERE id = %s"
        cursor.execute(query, (id,))

        data = cursor.fetchone()

        return [1, data, "success"]

    except Error as exc:
        return [0, str(exc), "mysql_error"]

    finally:
        if cursor is not None:
            cursor.close()

def verify_data_by_ID(conn, tablename, data_id):
    cursor = None

    if tablename not in SCHEMA:
        return [0, "ERR_UNKNOWN_TABLE"]

    try:
        cursor = conn.cursor()
        
        query = f"SELECT 1 FROM {tablename} WHERE id = %s LIMIT 1"
        cursor.execute(query, (data_id,))
        
        data = cursor.fetchone()

        if data is None:
            msg = f"{data_id} does not exist on table {tablename}"
            return [0, msg]
            
        return [1, "Go Wild!"]
        
    except Error as exc:
        return [0, f"mysql_error: {str(exc)}"]
        
    finally:
        if cursor is not None:
            cursor.close()

def validate_execution(return_data):
        if return_data[0] == 1:
            details = return_data[1]
            return 1
        else:
            return [0,f"Query execution failed: {return_data[1]}", "MYSQL_ERR"]
        
def add_courses(conn, raw_data):
    cursor = None

    # 1. Validate incoming data using your existing SCHEMA
    validation = data_validation(courses, raw_data)

    if not validation[0]:
        return [0, validation[1], None]

    data_dict = validation[1]

    # 2. Match the exact order of SQL columns
    fields = [
        "course_name",
        "teacher_id",
        "replacement_teacher_id",
        "start_time",
        "end_time",
        "seat_capacity",
        "fee_amount",
        "schedule_days",
        "duration_months",
        "start_date",
        "end_date",
        "status"
    ]

    data = tuple(data_dict[field] for field in fields)

    teacher_id = data_dict["teacher_id"]
    replacement_teacher_id = data_dict["replacement_teacher_id"]

    # 3. Check teacher IDs
    if teacher_id == replacement_teacher_id:
        return [0, "Teacher and replacement teacher cannot be same", None]

    check_teacher = verify_data_by_ID(conn, teachers, teacher_id)

    if not check_teacher[0]:
        return [0, check_teacher[1], None]

    check_replacement = verify_data_by_ID(
        conn, teachers, replacement_teacher_id
    )

    if not check_replacement[0]:
        return [0, check_replacement[1], None]

    try:
        cursor = conn.cursor()

        query = """
            INSERT INTO courses (
                course_name, teacher_id, replacement_teacher_id,
                start_time, end_time, seat_capacity, fee_amount,
                schedule_days, duration_months, start_date,
                end_date, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, data)
        conn.commit()

        return [1, "Course added successfully", {
            "course_id": cursor.lastrowid
        }]

    except Error:
        conn.rollback()
        # Log the actual exception on the server.
        return [0, "Database insert failed", "mysql_error"]

    finally:
        if cursor is not None:
            cursor.close()

def close_connection(conn):
    """Safely checks and closes the MySQL database connection."""
    try:
        if conn and conn.is_connected():
            conn.close()
            # print("Disconnected mysql connection!!")
    except Exception as e:
        print(f"Error while closing connection: {e}")

def delete_row(conn,tablename, id):
    cursor = None

    if not isinstance(id,int):
        return [0,f"Invalid {id} data type",None]

    try:
        cursor = conn.cursor()

        data_existence = get_row(conn,tablename,id)
        if data_existence[0] != 1:
            return [0,"Data not Found!!",None]

        query = f"DELETE FROM {tablename} WHERE id = %s"
        cursor.execute(query,(id,))
        conn.commit()

        return [1,f"Success", f"Successfully deleted {id}, Row = {data_existence[1]}"]
        # check if table is for student then we have delete it from enrollment too
        pass
    except Exception as exc:
        return [0,"error",exc]
    finally:
        if courses is not None:
            cursor.close()

