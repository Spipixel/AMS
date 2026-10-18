
from fastapi import FastAPI, Body, HTTPException

from fetch_data import (
    connect,
    get_data,
    close_connection,
    get_format,
    get_row,
    students,
    data_validation,
    courses,
    teachers,
    enrollments,
    add_courses,
    delete_row
)

from log import RequestLoggingMiddleware, log_error

app = FastAPI()

app.add_middleware(RequestLoggingMiddleware)


# --------------------------------------------------
# GET ALL COURSES
# --------------------------------------------------

@app.get("/attested/get_courses")
async def get_courses_data():
    output = connect()

    if not output or output[0] != 1:
        log_error("Database connection failed", endpoint="/attested/get_courses")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable"
        )

    connection = output[1]
    return get_format(connection, courses)


@app.get("/attested/course/{course_id}")
def get_course(course_id: int):
    output = connect()

    if not output or output[0] != 1:
        log_error(
            "Database connection failed",
            endpoint="/attested/course/{course_id}"
        )
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable"
        )

    connection = output[1]

    try:
        result = get_row(connection, courses, course_id)

        if result[0] != 1:
            raise HTTPException(
                status_code=500,
                detail="Failed to fetch course"
            )

        if result[1] is None:
            raise HTTPException(
                status_code=404,
                detail="Course not found"
            )

        return result[1]

    finally:
        close_connection(connection)

@app.post("/attested/add_course", status_code=201)
def addCourse(data: dict = Body(...)):
    output = connect()

    if not output or output[0] != 1:
        log_error(
            "Database connection failed",
            endpoint="/attested/add_course"
        )
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable"
        )

    conn = output[1]

    try:
        fetched_data = add_courses(conn, data)
        success, msg, result = fetched_data

        if not success:
            if result == "mysql_error":
                log_error(
                    "Database error while adding course",
                    endpoint="/attested/add_course",
                    error=str(msg)
                )
                raise HTTPException(
                    status_code=500,
                    detail="Failed to add course"
                )

            raise HTTPException(
                status_code=400,
                detail=msg
            )

        return {
            "success": True,
            "message": msg,
            "data": result
        }

    finally:
        close_connection(conn)


@app.delete("/attested/delete")
def delete(table: str, id: int):
    output = connect()

    if not output or output[0] != 1:
        log_error(
            "Database connection failed",
            endpoint="/attested/delete"
        )
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable"
        )

    conn = output[1]

    try:
        delete_request = delete_row(conn, table, id)
        success, msg, data = delete_request

        if not success:
            raise HTTPException(
                status_code=400,
                detail=msg
            )

        return {
            "success": True,
            "detail": msg,
            "data": data
        }

    finally:
        close_connection(conn)


@app.get("/attested/get_students")
async def get_students_data():
    output = connect()

    if not output or output[0] != 1:
        log_error(
            "Database connection failed",
            endpoint="/attested/get_students"
        )
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable"
        )

    connection = output[1]
    return get_format(connection, students)



@app.get("/attested/get_teachers")
async def get_teachers_data():
    output = connect()

    if not output or output[0] != 1:
        log_error(
            "Database connection failed",
            endpoint="/attested/get_teachers"
        )
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable"
        )

    connection = output[1]
    return get_format(connection, teachers)
