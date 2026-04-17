"""学生档案业务逻辑"""
import re
import io
import openpyxl
from app.extensions import db
from app.models.student import Student


class StudentService:
    _STUDENT_ID_RE = re.compile(r"^\d{8,20}$")

    def get_students(self, page: int, per_page: int, filters: dict) -> dict:
        q = Student.query
        if filters.get("name"):
            q = q.filter(Student.name.ilike(f"%{filters['name']}%"))
        if filters.get("class_name"):
            q = q.filter_by(class_name=filters["class_name"])
        if filters.get("face_registered") is not None:
            val = filters["face_registered"]
            if isinstance(val, str):
                val = val.lower() == "true"
            q = q.filter_by(face_registered=val)
        pagination = q.order_by(Student.student_id).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return {
            "items": [s.to_dict() for s in pagination.items],
            "total": pagination.total,
        }

    def get_student_by_id(self, sid: int):
        s = Student.query.get(sid)
        return s.to_dict() if s else None

    def create_student(self, data: dict) -> dict:
        required = ["student_id", "name", "class_name"]
        for f in required:
            if not data.get(f):
                return {"ok": False, "code": 400, "message": f"{f} 不能为空"}
        if Student.query.filter_by(student_id=data["student_id"]).first():
            return {"ok": False, "code": 409, "message": "学号已存在"}
        s = Student(
            student_id=data["student_id"].strip(),
            name=data["name"].strip(),
            class_name=data["class_name"].strip(),
            department=data.get("department", "").strip(),
        )
        db.session.add(s)
        db.session.commit()
        return {"ok": True, "data": s.to_dict()}

    def update_student(self, sid: int, data: dict) -> dict:
        s = Student.query.get(sid)
        if not s:
            return {"ok": False, "code": 404, "message": "学生不存在"}
        for field in ("name", "class_name", "department"):
            if data.get(field) is not None:
                setattr(s, field, data[field].strip())
        db.session.commit()
        return {"ok": True, "data": s.to_dict()}

    def delete_student(self, sid: int) -> dict:
        s = Student.query.get(sid)
        if not s:
            return {"ok": False, "code": 404, "message": "学生不存在"}
        db.session.delete(s)
        db.session.commit()
        return {"ok": True}

    def import_from_excel(self, file_storage) -> dict:
        content = file_storage.read()
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return {"success": 0, "failed": 0, "errors": []}

        # 跳过表头
        header = [str(c).strip() if c else "" for c in rows[0]]
        required_cols = ["学号", "姓名", "班级"]
        if not all(c in header for c in required_cols):
            return {"success": 0, "failed": len(rows) - 1,
                    "errors": ["Excel 表头不符合模板，必须包含：学号、姓名、班级"]}

        idx = {c: header.index(c) for c in header if c}
        success_count, errors = 0, []
        for row_num, row in enumerate(rows[1:], start=2):
            student_id = str(row[idx["学号"]]).strip() if row[idx["学号"]] else ""
            name = str(row[idx["姓名"]]).strip() if row[idx["姓名"]] else ""
            class_name = str(row[idx["班级"]]).strip() if row[idx["班级"]] else ""
            if not student_id or not name or not class_name:
                errors.append(f"第{row_num}行：学号/姓名/班级不能为空")
                continue
            if Student.query.filter_by(student_id=student_id).first():
                errors.append(f"第{row_num}行：学号 {student_id} 已存在")
                continue
            dept = str(row[idx.get("院系", -1)]).strip() if idx.get("院系") is not None and row[idx.get("院系", -1)] else ""
            db.session.add(Student(student_id=student_id, name=name,
                                   class_name=class_name, department=dept))
            success_count += 1
        db.session.commit()
        return {"success": success_count, "failed": len(errors), "errors": errors}

    def get_all_classes(self) -> list:
        rows = db.session.query(Student.class_name).distinct().order_by(
            Student.class_name
        ).all()
        return [r[0] for r in rows]
