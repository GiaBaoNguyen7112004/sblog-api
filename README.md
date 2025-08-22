# SBlog API

SBlog is a simple blogging platform built with **Django** where users can **share**, **read**, and **interact** with blog posts.

---

## Features

- User registration & authentication (JWT-based)
- Create, read, update, delete (CRUD) blog posts
- Comment on posts
- Like/unlike posts
- Search and filter posts by title, author, or tags
- RESTful API endpoints

---

## Tech Stack

- Python 3.x  
- Django 4.x  
- Django REST Framework  
- SQLite / PostgreSQL (configurable)  
- JWT Authentication  

---

## Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/sblog.git
cd sblog
Create virtual environment

python -m venv venv
source venv/bin/activate  # Linux / Mac
venv\Scripts\activate     # Windows
Install dependencies

pip install -r requirements.txt
Apply migrations

python manage.py migrate
Run the server

python manage.py runserver
Server will run at http://127.0.0.1:8000/

