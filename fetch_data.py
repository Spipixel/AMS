import os
import mysql.connector
from mysql.connector import Error
from fastapi import HTTPException


students = "students"
teachers = "teachers"
courses = "courses"
enrollments = "enrollments"

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
    }
}




def connect():
    try:
        conn = mysql.connector.connect(
            host = "localhost",
            port = 3306,
            user = "root",
            password = "Ayush@2008",
            database = "ams_db",
            connection_timeout=5
        )

    
        if conn.is_connected():
            return [1, conn]
        
    except KeyError as exc:
        return [0, exc, "keyerror"]
    except Error as exc:
        return [0, exc, "mysql_error"]


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


def get_db_details(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("select database(),version()")
        result = cursor.fetchone()
        cursor.close()

        return [1, result]
    except Error as exc:
        return [0, exc, "mysql_error"]

# def get_data(conn,tablename):
#     cursor = None

#     if tablename not in SCHEMA:
#         return [0,"ERR_UNKNOWN_TABLE"]

#     try:
#         cursor = conn.cursor()
#         cursor.execute(f"select * from {tablename}")
#         data = cursor.fetchall()
#         return [1,data]
#     except Error as exc:
#         return [0,exc, "mysql_error"]
#     finally:
#         if cursor is not None:
#             cursor.close()


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

        return [1, data]

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

# def format_data_DIL(raw_data):
#     data = []
#     for i in raw_data:
#         temp = []
#         for j in i.values():
#             temp.append(str(j))
#         data.append(temp)
#     return data


def validate_execution(return_data):
        if return_data[0] == 1:
            details = return_data[1]
            return 1
        else:
            return [0,f"Query execution failed: {return_data[1]}", "MYSQL_ERR"]
        

def add_courses(conn,raw_data):
    
    data = tuple(raw_data.values())

    tablename=courses
    cursor = None
    teacher_id = raw_data['teacher_id']
    replacement_teacher_id = raw_data['replacement_teacher_id']


    # check if teacher exists
    check_teacher_existence = verify_data_by_ID(conn,teachers,teacher_id)
    check_replacement_teacher_existence = verify_data_by_ID(conn,teachers,replacement_teacher_id)


    # Verfiying if teacher exists or not
    if teacher_id == replacement_teacher_id:
        return [0, "Teacher and replacement teacher cannot be same!!"]
    
    if not check_teacher_existence[0]:
        return [0,check_teacher_existence[1]]

    if not check_replacement_teacher_existence[0]:
        return [0,check_replacement_teacher_existence[1]]
    

    try:
        cursor = conn.cursor()
        query = f"""
            INSERT INTO {tablename} (
                course_name, teacher_id, replacement_teacher_id, start_time, end_time, 
                seat_capacity, fee_amount, schedule_days, duration_months, start_date, 
                end_date, status
            ) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, data)
        conn.commit()  
        return [1, "Success"]
    except Error as exc:
        return [0,exc, "mysql_error"]
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

def main():
    print("Trying to establish connection between database!")

    output = connect()
    if output[0] == 0:
        if output[2] == "keyerror":
            return [0, f"Missing environment variable: {output[1]}", 'error']
        elif output[2] == "mysql_error":
            return [0, f"Mysql connection failed: {output[1]}", 'mysql_error']
        return

    connection = output[1]

    try:
        database_details = get_db_details(connection)

        # fetch_raw_data = get_data(connection,courses)
        # validate_db_details = validate_execution(database_details)
        # if not validate_db_details:
        #     return
        # validate_fetch_data = validate_execution(fetch_raw_data)
        # if not validate_fetch_data:
        #     return
        # fetched_data = format_data(fetch_raw_data[1])

        data = data_validation(
            courses,
            {
                "course_name": "Full Stack Development",
                "teacher_id": 2,
                "replacement_teacher_id": 1,
                "start_time": "09:00",
                "end_time": "11:00",
                "seat_capacity": 30,
                "fee_amount": 4000,
                "schedule_days": "MON,TUE,WED",
                "duration_months": 5,
                "start_date": "2026-12-12",
                "end_date": "2027-12-12",
                "status": "ACTIVE"
            }
        )

        if not data[0]:
            return data[1]
        
        add_course = add_courses(connection, data[1])

        if add_course[0]:
            print(add_course[1])
        else:
            print(add_course)

    finally:
        # Call the new disconnect function here
        close_connection(connection)

# if __name__ == "__main__":
#     main()
