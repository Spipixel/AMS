student = {}
def add(id,name,pno,email,course):
    i = 1
    student[i] = {
        "id": id,
        "name": name,
        "pno": pno,
        "email": email,
        "course": course 
    }

add(12,"ayush","91208923","email@ds.com",{"id": "m", "name": 2})

for n,m in student.items():
    for j in m.values():
        if isinstance(j,list):
            print(j)

{
    "timestamp": "2026-10-18T13:03:41.221192+00:00", 
    "client_ip": "127.0.0.1", 
    "method": "GET", 
    "path": "/attested/course/5", 
    "query_params": {}, 
    "request_data":0, 
    "status_code": 200, 
    "outcome": "success", 
    "response_data": 
        {
            "id": 5, 
            "course_name": "Python Programming", 
            "teacher_id": 2, 
            "replacement_teacher_id": 3, 
            "start_time": 36000.0, 
            "end_time": 39600.0, 
            "seat_capacity": 20, 
            "fee_amount": 7500.0, 
            "schedule_days": "MON,WED,FRI", 
            "duration_months": 4, 
            "start_date": "2026-10-12", 
            "end_date": "2027-02-12",
             "status": "ACTIVE", 
             "created_at": "2026-10-13T19:10:57"
        }
}


# Format
# Client_id: 127.0.0.1
# Asked_for: {
#   Course_name: Python Programming
#   techer_id: 2
# }
# use if in first loop to get client id and again use it in second loop it
