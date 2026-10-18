from fastapi import FastAPI, Body, HTTPException
from fetch_data import connect, get_data, close_connection, get_format, get_row
from fetch_data import students, courses,teachers, enrollments


app = FastAPI()


@app.get("/attested/get_courses")
async def get_courses_data():
    output = connect()

    if not output or output[0] != 1:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection unvailable"
        )
    
    connection = output[1]

    data = get_format(connection,courses)
    return data

@app.get("/attested/course/{course_id}")
async def get_courses_data(course_id: int):
    output = connect()

    if not output or output[0] != 1:
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable"
        )

    connection = output[1]

    data = get_row(connection,courses,course_id)
    return data




@app.get("/attested/get_students")
async def get_students_data():
    output = connect()

    if not output or output[0] != 1:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection unvailable"
        )
    
    connection = output[1]

    data = get_format(connection,students)
    return data



@app.get("/attested/get_teachers")
async def get_teachers_data():
    output = connect()

    if not output or output[0] != 1:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection unvailable"
        )
    
    connection = output[1]

    data = get_format(connection,teachers)
    return data