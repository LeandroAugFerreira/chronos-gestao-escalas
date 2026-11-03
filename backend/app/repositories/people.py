"""One filtered, scoped query for both the directory and its export."""
from app.models.entities import Employee
from app.repositories.scoped import scoped


def employee_query(principal, *, unit_id=None, department_id=None, status=None,
                   search="", sort="name", descending=False):
    query = scoped(Employee, principal, "people:read", Employee.unit_id)
    if unit_id:
        query = query.where(Employee.unit_id == unit_id)
    if department_id:
        query = query.where(Employee.department_id == department_id)
    if status:
        query = query.where(Employee.status == status)
    if search:
        query = query.where(Employee.name.ilike(f"%{search}%") | Employee.registration.ilike(f"%{search}%"))
    column = getattr(Employee, sort)
    return query.order_by(column.desc() if descending else column.asc(), Employee.id)
