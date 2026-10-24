from fastapi import (
    FastAPI,
    Body,
    HTTPException,
    status,
    Request,
    Response,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware

import secrets
import time

from fetch_data import (
    connect,
    close_connection,
    get_format,
    get_row,
    students,
    courses,
    teachers,
    get_enrollments,
    get_enrolled_student_details,
    add_courses,
    delete_row,
    authentication,
)
from log import RequestLoggingMiddleware, log_error


# --------------------------------------------------
# APP AND MIDDLEWARE
# --------------------------------------------------

app = FastAPI()

# Keep the existing request logger.
app.add_middleware(RequestLoggingMiddleware)

# Change these to the exact origins serving your frontend.
# Do not add "null" for normal development or deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# --------------------------------------------------
# SESSION AUTHENTICATION
# --------------------------------------------------
# Prototype only: sessions are lost when the process restarts and
# are not shared between multiple workers. Use a database/Redis store
# for a multi-worker or production deployment.

ACTIVE_SESSIONS = {}

SESSION_COOKIE = "ams_session"
SESSION_DURATION = 60 * 60  # 1 hour


def require_admin(request: Request):
    """Require a valid, unexpired session cookie for protected routes."""
    token = request.cookies.get(SESSION_COOKIE)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin login required.",
        )

    session = ACTIVE_SESSIONS.get(token)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )

    if session["expires_at"] <= time.time():
        ACTIVE_SESSIONS.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        )

    return session


def open_database_or_503(endpoint: str):
    """Open a DB connection or raise 503 before accessing output[1]."""
    output = connect()

    if not output or len(output) < 2 or output[0] != 1 or output[1] is None:
        log_error("Database connection failed", endpoint=endpoint)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable.",
        )

    return output[1]


def unwrap_helper_result(result, endpoint: str):
    """
    Handle helpers that return (status, data/message).
    Expected success shape: (1, data). Adjust if your fetch_data.py
    helper uses a different return contract.
    """
    if not isinstance(result, (tuple, list)) or len(result) < 2:
        log_error("Unexpected database helper result", endpoint=endpoint)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected database response.",
        )

    if result[0] != 1:
        log_error("Database helper failed", endpoint=endpoint)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch requested data.",
        )

    return result[1]


# --------------------------------------------------
# LOGIN / LOGOUT
# --------------------------------------------------

@app.post("/auth/v1/login", status_code=status.HTTP_200_OK)
def auth_login(
    response: Response,
    data: dict = Body(...),
):
    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not username.strip() or not isinstance(password, str) or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing username or password.",
        )

    connection = open_database_or_503("/auth/v1/login")

    try:
        auth_status, auth_message, auth_data = authentication(
            connection,
            username.strip(),
            password,
        )

        if auth_status != 1:
            log_error("Login failed", endpoint="/auth/v1/login")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )

        # auth_data in the supplied authentication() function is the
        # login-log ID. It is NOT necessarily the admin's database ID.
        token = secrets.token_urlsafe(32)

        ACTIVE_SESSIONS[token] = {
            "login_id": auth_data,
            "username": username.strip(),
            "expires_at": time.time() + SESSION_DURATION,
        }

        response.set_cookie(
            key=SESSION_COOKIE,
            value=token,
            httponly=True,
            secure=False,  # Local HTTP development only. Set True on HTTPS.
            samesite="lax",
            max_age=SESSION_DURATION,
            path="/",
        )

        return {
            "status": 1,
            "message": "Login successful",
        }

    except HTTPException:
        # Preserve intentional 400/401/503 responses.
        raise
    except Exception as exc:
        log_error(
            "Unexpected login error",
            endpoint="/auth/v1/login",
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected server error occurred.",
        )
    finally:
        close_connection(connection)


@app.post("/auth/v1/logout")
def auth_logout(
    request: Request,
    response: Response,
    admin=Depends(require_admin),
):
    token = request.cookies.get(SESSION_COOKIE)

    if token:
        ACTIVE_SESSIONS.pop(token, None)

    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=False,  # Must match the cookie setting; use True on HTTPS.
        samesite="lax",
    )

    return {
        "status": 1,
        "message": "Logged out successfully",
    }


@app.get("/auth/v1/me")
def auth_me(admin=Depends(require_admin)):
    """Optional endpoint for the frontend to check its current session."""
    return {
        "status": 1,
        "username": admin["username"],
        "expires_at": admin["expires_at"],
    }


# --------------------------------------------------
# GET ALL COURSES
# --------------------------------------------------

@app.get("/attested/get_courses")
def get_courses_data(admin=Depends(require_admin)):
    connection = open_database_or_503("/attested/get_courses")
    try:
        return get_format(connection, courses)
    finally:
        close_connection(connection)


# --------------------------------------------------
# GET ONE COURSE
# --------------------------------------------------

@app.get("/attested/course/{course_id}")
def get_course(
    course_id: int,
    admin=Depends(require_admin),
):
    connection = open_database_or_503("/attested/course/{course_id}")

    try:
        result = get_row(connection, courses, course_id)

        if not result or result[0] != 1:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch course.",
            )

        if len(result) < 2 or result[1] is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found.",
            )

        return result[1]
    finally:
        close_connection(connection)


# --------------------------------------------------
# ADD COURSE
# --------------------------------------------------

@app.post("/attested/add_course", status_code=status.HTTP_201_CREATED)
def add_course_endpoint(
    data: dict = Body(...),
    admin=Depends(require_admin),
):
    connection = open_database_or_503("/attested/add_course")

    try:
        result = add_courses(connection, data)

        if not isinstance(result, (tuple, list)) or len(result) < 3:
            log_error(
                "Unexpected add_courses result",
                endpoint="/attested/add_course",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected response while adding course.",
            )

        success, message, data_result = result

        if not success:
            if data_result == "mysql_error":
                log_error(
                    "Database error while adding course",
                    endpoint="/attested/add_course",
                    error=str(message),
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to add course.",
                )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(message),
            )

        return {
            "success": True,
            "message": message,
            "data": data_result,
        }
    finally:
        close_connection(connection)


# --------------------------------------------------
# DELETE RECORD
# --------------------------------------------------

@app.delete("/attested/delete")
def delete_endpoint(
    table: str,
    id: int,
    admin=Depends(require_admin),
):
    connection = open_database_or_503("/attested/delete")

    try:
        result = delete_row(connection, table, id)

        if not isinstance(result, (tuple, list)) or len(result) < 3:
            log_error(
                "Unexpected delete_row result",
                endpoint="/attested/delete",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected response while deleting record.",
            )

        success, message, data_result = result

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(message),
            )

        return {
            "success": True,
            "detail": message,
            "data": data_result,
        }
    finally:
        close_connection(connection)


# --------------------------------------------------
# GET ENROLLMENT DATA
# --------------------------------------------------

@app.get("/attested/get_enrollment_data")
def get_enrollment_data(admin=Depends(require_admin)):
    connection = open_database_or_503("/attested/get_enrollment_data")

    try:
        result = get_enrollments(connection)
        data = unwrap_helper_result(result, "/attested/get_enrollment_data")
        return data
    finally:
        close_connection(connection)


# --------------------------------------------------
# GET ENROLLED STUDENT DETAILS
# --------------------------------------------------

@app.get("/attested/enrolled/{id}")
def get_enrolled_student_details_endpoint(
    id: int,
    admin=Depends(require_admin),
):
    connection = open_database_or_503("/attested/enrolled/{id}")

    try:
        result = get_enrolled_student_details(connection, id)
        data = unwrap_helper_result(result, "/attested/enrolled/{id}")

        if data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment/student record not found.",
            )

        return data
    finally:
        close_connection(connection)


# --------------------------------------------------
# GET STUDENTS
# --------------------------------------------------

@app.get("/attested/get_students")
def get_students_data(admin=Depends(require_admin)):
    connection = open_database_or_503("/attested/get_students")

    try:
        return get_format(connection, students)
    finally:
        close_connection(connection)


# --------------------------------------------------
# GET TEACHERS
# --------------------------------------------------

@app.get("/attested/get_teachers")
def get_teachers_data(admin=Depends(require_admin)):
    connection = open_database_or_503("/attested/get_teachers")


    try:
        return get_format(connection, teachers)
    finally:
        close_connection(connection)
