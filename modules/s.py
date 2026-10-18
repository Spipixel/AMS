students = {
    1: {
        "name": "Ankit"
    }
}

# Financial records
student_fee_records = {
    1: {
        "Student_id": 1,
        "course_enrollment": ["python","networking"],
        "fee": [1200,3400],
        "status": ["paid","unpaid"]
    }
}


def get_fee_detail_of_course(taget_course=None):
    target_id = None
    students_target_id = None
    if taget_course != None:
        for id,data in student_fee_records.items():
            students_target_id = id
            for key,value in data.items():
                # To check if the student is enrolled in python or not
                if key == "course_enrollment":
                    if isinstance(value,list):
                        for index,i in enumerate(value):
                            if i == taget_course:
                                target_id = index
                                break
        return [target_id, taget_course,students_target_id]

print(get_fee_detail_of_course("python"))