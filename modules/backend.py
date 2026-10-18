from datetime import date, datetime
from pathlib import Path
import csv
import os
import tempfile


error_code = {
    "ERR001": "No empty Slot is available!",
    "ERR002": "Wrong ID",
    "ERR003": "Primary teacher and replacement teacher cannot be same",
    "ERR004": "Invalid Data Type",
    "ERR005": "Invalid Duration",
    "ERR006": "Invalid Slot ID",
    "ERR007": "Invalid seat capacity",
    "ERR008": "Invalid schedule days format",
    "ERR009": "Invalid date format or date value",
    "ERR010": "Course start date cannot be before today",
    "ERR011": "End date must be after start date",
    "ERR012": "Invalid file extension / invalid file type",
    "ERR013": "Invalid format for data to append in file",
    "ERR014": "Data length does not match the CSV header",
    "ERR015": "No permission to call append data function",
    "ERR016": "Wrong file to append data",
    "ERR017": "Invalid ID prefix",
    "ERR018": "File missing, unreadable, or invalid CSV header",
    "ERR019": "Invalid or duplicate IDs in the CSV file",
    "ERR020": "File does not exist",
    "ERR021": "Empty or invalid CSV header",
    "ERR022": "Unable to read or write CSV file",
    "ERR023": "Unauthorized file",
    "ERR024": "Record not found / duplicate course name",
    "ERR025": "Invalid or missing record fields",
    "ERR026": "Invalid course status",
    "ERR027": "Duplicate course name",
    "ERR_D01": "Course Entry Failed",
    "ERR_NOT_VALID_FIELD_NAME_00": "Wrong Column ID name",
}

folder = Path("data")

maximum_duration = 60
minimum_duration = 1
schedule_days_format = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
maximum_seat_capacity = 60
course_status = ["ACTIVE", "COMPLETED", "CANCELED"]

valid_ids = ["S", "T", "PR", "S1", "ST", "F", "SP", "FP", "E", "C1"]
working_files = {
    "courses": "courses.csv",
    "time_slots": "time_slots.csv",
    "enrollments": "enrollments.csv",
    "fee_payments": "fee_payments.csv",
    "salary_payments": "salary_payments.csv",
    "sessions": "sessions.csv",
    "student_attendance": "student_attendance.csv",
    "student_fees": "student_fees.csv",
    "students": "students.csv",
    "teacher_attendance": "teacher_attendance.csv",
    "teacher_payroll": "teacher_payroll.csv",
    "teachers": "teachers.csv",
}

allowed_files = set(working_files.values())


def is_error(result):
    return isinstance(result, str) and result in error_code


def filename_validation(filename):
    if not isinstance(filename, str) or not filename.strip():
        return "ERR012"
    if filename not in allowed_files or Path(filename).name != filename:
        return "ERR023"
    return 1


def get_header(filename):
    valid = filename_validation(filename)
    if valid != 1:
        return valid

    file = folder / filename
    if not file.is_file():
        return "ERR020"

    try:
        with file.open("r", newline="", encoding="utf-8") as f:
            header = next(csv.reader(f), None)

        if not header or any(not isinstance(col, str) or not col.strip() for col in header):
            return "ERR021"
        if len(header) != len(set(header)):
            return "ERR021"
        return header
    except (OSError, csv.Error, UnicodeError):
        return "ERR022"


def get_data(filename):
    valid = filename_validation(filename)
    if valid != 1:
        return valid

    file = folder / filename
    if not file.is_file():
        return "ERR020"

    header = get_header(filename)
    if is_error(header):
        return header

    try:
        with file.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != header:
                return "ERR021"
            rows = list(reader)
            if any(None in row or any(value is None for value in row.values()) for row in rows):
                return "ERR025"
            return rows
    except (OSError, csv.Error, UnicodeError):
        return "ERR022"


def append_data(who_can_call, filename, row=None):
    valid_caller = {
        "add_course": working_files["courses"],
        "add_student": working_files["students"],
        "add_teacher": working_files["teachers"],
    }
    if who_can_call not in valid_caller:
        return "ERR015"
    if valid_caller[who_can_call] != filename:
        return "ERR016"

    valid = filename_validation(filename)
    if valid != 1:
        return valid
    if not isinstance(row, (list, tuple)):
        return "ERR013"
    if any(not isinstance(value, (str, int, float)) for value in row):
        return "ERR013"

    header = get_header(filename)
    if is_error(header):
        return header
    if len(row) != len(header):
        return "ERR014"

    file = folder / filename
    try:
        with file.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)
        return 1
    except (OSError, csv.Error, UnicodeError):
        return "ERR022"


def _atomic_write_csv(file, fieldnames, rows):
    temp_path = None
    try:
        file.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=file.parent,
            delete=False,
        ) as temp:
            temp_path = Path(temp.name)
            writer = csv.DictWriter(
                temp, fieldnames=fieldnames, extrasaction="raise"
            )
            writer.writeheader()
            writer.writerows(rows)

        os.replace(temp_path, file)
        return 1
    except (OSError, csv.Error, UnicodeError, ValueError):
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        return "ERR022"


def check_id_exsist(filename, record_id):
    valid = filename_validation(filename)
    if valid != 1:
        return valid

    if not isinstance(record_id, str):
        return "ERR004"
    if not record_id.startswith(tuple(valid_ids)):
        return "ERR002"

    rows = get_data(filename)
    if is_error(rows):
        return rows

    header = get_header(filename)
    if is_error(header):
        return header
    if not header:
        return "ERR021"

    id_column = header[0]
    if any(row.get(id_column) == record_id for row in rows):
        return 1
    return "ERR002"


def soft_delete(filename, record_id):
    valid = filename_validation(filename)
    if valid != 1:
        return valid

    if not isinstance(record_id, str) or not record_id.strip():
        return "ERR004"
    if not record_id.startswith(tuple(valid_ids)):
        return "ERR002"

    file = folder / filename
    history_file = folder / "history" / filename

    header = get_header(filename)
    if is_error(header):
        return header
    if not header:
        return "ERR021"

    data = get_data(filename)
    if is_error(data):
        return data

    id_column = header[0]
    matching_rows = [row for row in data if row.get(id_column) == record_id]
    if not matching_rows:
        return "ERR024"
    if len(matching_rows) > 1:
        return "ERR019"

    deleted_row = matching_rows[0]
    remaining_rows = [row for row in data if row.get(id_column) != record_id]

    linked_slot_id = None
    if filename == working_files["courses"]:
        slots = get_all_time_slot()
        if is_error(slots):
            return slots
        linked_slots = [
            slot for slot in slots if slot.get("course_id") == record_id
        ]
        if len(linked_slots) > 1:
            return "ERR025"
        if linked_slots:
            linked_slot_id = linked_slots[0].get("slot_id")

    try:
        history_file.parent.mkdir(parents=True, exist_ok=True)
        history_rows = []

        if history_file.exists():
            with history_file.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                history_header = reader.fieldnames
                history_rows = list(reader)

            if history_header != header:
                return "ERR021"
            if any(
                None in row or any(value is None for value in row.values())
                for row in history_rows
            ):
                return "ERR025"

        history_rows.append(deleted_row)
        result = _atomic_write_csv(history_file, header, history_rows)
        if result != 1:
            return result

        result = _atomic_write_csv(file, header, remaining_rows)
        if result != 1:
            return result

    except (OSError, csv.Error, UnicodeError, ValueError):
        return "ERR022"

    if linked_slot_id is not None:
        result = update_column(
            working_files["time_slots"],
            "slot_id",
            linked_slot_id,
            "course_id",
            "NULL",
        )
        if result != 1:
            return result

    return 1


def restore():
    return


def rollback():
    return


def update_row(filename, fileheader, row_data, column_name, column_data):
    valid = filename_validation(filename)
    if valid != 1:
        return valid

    file = folder / filename
    if not file.is_file():
        return "ERR020"

    header = get_header(filename)
    if is_error(header):
        return header

    if fileheader != header:
        return "ERR021"
    if column_name not in header:
        return "ERR023"
    if not isinstance(row_data, dict) or set(row_data.keys()) != set(header):
        return "ERR025"

    try:
        with file.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        found = False
        for index, row in enumerate(rows):
            if row.get(column_name) == str(column_data):
                rows[index] = row_data.copy()
                found = True
                break

        if not found:
            return "ERR024"
        return _atomic_write_csv(file, header, rows)
    except (OSError, csv.Error, UnicodeError):
        return "ERR022"


def update_column(
    filename,
    column_name,
    column_data,
    to_update_column_name,
    to_update_column_data,
):
    valid = filename_validation(filename)
    if valid != 1:
        return valid

    file = folder / filename
    if not file.is_file():
        return "ERR020"

    header = get_header(filename)
    if is_error(header):
        return header
    if column_name not in header or to_update_column_name not in header:
        return "ERR023"

    data = get_data(filename)
    if is_error(data):
        return data

    found = False
    for row in data:
        if row.get(column_name) == str(column_data):
            row[to_update_column_name] = str(to_update_column_data)
            found = True
            break

    if not found:
        return "ERR024"
    return _atomic_write_csv(file, header, data)


def generate_new_id(prefix, filename):
    if not isinstance(prefix, str) or not prefix or not prefix.isalnum():
        return "ERR017"

    valid = filename_validation(filename)
    if valid != 1:
        return valid

    file = folder / filename
    if not file.is_file():
        return "ERR018"

    header = get_header(filename)
    if is_error(header) or not header:
        return "ERR018"

    try:
        with file.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return "ERR018"

            id_column = reader.fieldnames[0]
            ids = []
            for row in reader:
                existing_id = row.get(id_column)
                if not existing_id or not existing_id.startswith(prefix):
                    return "ERR019"
                number_part = existing_id[len(prefix):]
                if not number_part.isdigit():
                    return "ERR019"
                ids.append(existing_id)

        if len(ids) != len(set(ids)):
            return "ERR019"

        highest_number = 0
        number_width = 2
        for existing_id in ids:
            number_part = existing_id[len(prefix):]
            highest_number = max(highest_number, int(number_part))
            number_width = max(number_width, len(number_part))

        return f"{prefix}{highest_number + 1:0{number_width}d}"
    except (OSError, csv.Error, UnicodeError):
        return "ERR018"


def avaiable_slots():
    time_slots_data = get_data(working_files["time_slots"])
    if is_error(time_slots_data):
        return time_slots_data

    empty_slots = {}
    for row in time_slots_data:
        if "course_id" not in row or "slot_id" not in row or "start_time" not in row:
            return "ERR025"
        if row["course_id"] == "NULL":
            empty_slots[row["slot_id"]] = row["start_time"]
    return empty_slots


def get_all_time_slot():
    return get_data(working_files["time_slots"])


def get_time_slot_column_data(slot_id, column_name):
    slots = get_all_time_slot()
    if is_error(slots):
        return slots

    for slot in slots:
        if slot.get("slot_id") == str(slot_id):
            if column_name not in slot:
                return "ERR023"
            return slot[column_name]
    return "ERR006"


def validate_course_dates(data):
    try:
        start_text = data["start_date"]
        end_text = data["end_date"]
        start_date = datetime.strptime(start_text, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_text, "%Y-%m-%d").date()
        if start_date.isoformat() != start_text or end_date.isoformat() != end_text:
            return "ERR009"
    except (ValueError, TypeError, KeyError):
        return "ERR009"

    if start_date < date.today():
        return "ERR010"
    if end_date <= start_date:
        return "ERR011"
    return None


def parse_course_schedule_days(value):
    if not isinstance(value, str) or not value.strip():
        return None

    days = value.split(",")
    if (
        any(day not in schedule_days_format for day in days)
        or len(days) != len(set(days))
    ):
        return None
    return set(days)


def dates_overlap(start1, end1, start2, end2):
    return start1 <= end2 and start2 <= end1


def check_course_conflict(data, selected_slot_id):
    courses = get_data(working_files["courses"])
    if is_error(courses):
        return courses

    all_slots = get_all_time_slot()
    if is_error(all_slots):
        return all_slots

    try:
        new_start = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        new_end = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
    except (ValueError, TypeError, KeyError):
        return "ERR009"

    new_days = {
        day
        for enabled, day in zip(data["schedule_days"], schedule_days_format)
        if enabled == 1
    }
    new_name = data["course_name"].strip().casefold()

    course_to_slot = {}
    for slot in all_slots:
        slot_course_id = slot.get("course_id")
        if slot_course_id and slot_course_id != "NULL":
            if slot_course_id in course_to_slot:
                return "ERR025"
            course_to_slot[slot_course_id] = slot.get("slot_id")

    for course in courses:
        existing_status = course.get("status")
        if existing_status not in course_status:
            return "ERR025"

        if existing_status != "ACTIVE":
            continue

        existing_name = course.get("course_name", "").strip().casefold()
        if existing_name == new_name:
            return "ERR027"

        if course_to_slot.get(course.get("course_id")) != selected_slot_id:
            continue

        try:
            existing_start = datetime.strptime(
                course["start_date"], "%Y-%m-%d"
            ).date()
            existing_end = datetime.strptime(
                course["end_date"], "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError, KeyError):
            return "ERR025"

        if not dates_overlap(new_start, new_end, existing_start, existing_end):
            continue

        existing_days = parse_course_schedule_days(course.get("schedule_days", ""))
        if existing_days is None:
            return "ERR025"

        if new_days.intersection(existing_days):
            return "ERR001"

    return 1


def add_course(data=None, total_number_of_courses=0):
    if not isinstance(data, dict):
        return "ERR025"

    required_fields = {
        "course_name",
        "start_time",
        "primary_teacher_id",
        "replacement_teacher_ids",
        "seat_capacity",
        "fee_amount",
        "schedule_days",
        "duration_months",
        "start_date",
        "end_date",
        "status",
    }
    if not required_fields.issubset(data):
        return "ERR025"

    for field in ("course_name", "start_time", "primary_teacher_id",
                  "replacement_teacher_ids"):
        if not isinstance(data[field], str) or not data[field].strip():
            return "ERR025"

    if data["status"] not in course_status:
        return "ERR026"

    for field in ("fee_amount", "seat_capacity", "duration_months"):
        if type(data[field]) is not int:
            return "ERR004"

    if data["fee_amount"] < 0:
        return "ERR004"
    if not minimum_duration <= data["duration_months"] <= maximum_duration:
        return "ERR005"
    if not 1 <= data["seat_capacity"] <= maximum_seat_capacity:
        return "ERR007"

    days = data["schedule_days"]
    if (
        not isinstance(days, list)
        or len(days) != len(schedule_days_format)
        or any(type(value) is not int or value not in (0, 1) for value in days)
        or not any(days)
    ):
        return "ERR008"

    date_error = validate_course_dates(data)
    if date_error is not None:
        return date_error

    teachers = get_data(working_files["teachers"])
    if is_error(teachers):
        return teachers
    teacher_ids = {row.get("teacher_id") for row in teachers}

    if data["primary_teacher_id"] not in teacher_ids:
        return "ERR002"
    if data["replacement_teacher_ids"] not in teacher_ids:
        return "ERR002"
    if data["primary_teacher_id"] == data["replacement_teacher_ids"]:
        return "ERR003"

    all_slots = get_all_time_slot()
    if is_error(all_slots):
        return all_slots

    selected_slot = None
    for slot in all_slots:
        if slot.get("start_time") == data["start_time"]:
            selected_slot = slot
            break

    if selected_slot is None:
        return "ERR006"

    selected_slot_id = selected_slot.get("slot_id")
    conflict = check_course_conflict(data, selected_slot_id)
    if conflict != 1:
        return conflict

    if selected_slot.get("course_id") != "NULL":
        return "ERR001"

    end_time = selected_slot.get("end_time")
    if not end_time:
        return "ERR025"

    course_id = generate_new_id("C", working_files["courses"])
    if is_error(course_id):
        return course_id

    schedule_days_text = ",".join(
        day for enabled, day in zip(days, schedule_days_format) if enabled == 1
    )

    course_row = [
        course_id,
        data["course_name"].strip(),
        data["start_time"],
        end_time,
        data["primary_teacher_id"],
        data["replacement_teacher_ids"],
        data["seat_capacity"],
        data["fee_amount"],
        schedule_days_text,
        data["duration_months"],
        data["start_date"],
        data["end_date"],
        data["status"],
    ]

    result = append_data("add_course", working_files["courses"], course_row)
    if result != 1:
        return result

    result = update_column(
        working_files["time_slots"],
        "slot_id",
        selected_slot_id,
        "course_id",
        course_id,
    )
    if result != 1:
        delete_result = soft_delete(working_files["courses"], course_id)
        if delete_result != 1:
            return "ERR_D01"
        return result

    return 1


def main():
    result = add_course({
        "course_name": "Ai/ml",
        "start_time": "11:00",
        "primary_teacher_id": "T001",
        "replacement_teacher_ids": "T003",
        "seat_capacity": 10,
        "fee_amount": 2300,
        "schedule_days": [1, 1, 1, 1, 0, 0],
        "duration_months": 12,
        "start_date": "2026-10-12",
        "end_date": "2027-10-12",
        "status": "ACTIVE",
    })

    if is_error(result):
        print(f"{result}: {error_code[result]}")
    elif result == 1:
        print("Course created successfully.")
    else:
        print(f"Unexpected result: {result!r}")


if __name__ == "__main__":
    main()
