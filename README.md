# School Management System (Django)

This is a small **school management system** built with Django.

It is a single-database, single-schema app (not multiple schemas).  
All data is stored in shared tables, and we use Django ORM and roles to control who can see and do what.

---

## Roles

The system has three main roles:

- **Admin**
  - Manages teachers and students.
  - Can add, update and delete records.
- **Teacher**
  - Can view and manage the students assigned to them.
- **Student**
  - Can log in and view their own details.

Each role sees a different dashboard and different menu options.

---

## Main features

- Custom login and logout.
- Dashboards for admin, teacher and student.
- Simple HTML pages (Django templates) for listing, creating, updating and deleting data.
- Role-based access control (RBAC) using a `role` field on the user and simple decorators in views.
- Some basic APIs using Django REST Framework with `GenericViewSet` (if you enable DRF).

---

## Tech stack

- Python
- Django
- Django REST Framework
- PostgreSQL (can be changed to another DB if needed)
