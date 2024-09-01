# Django Project

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Introduction

GTC is a Django-based web application designed to create REST APIs for 1840 GTC.

## Features

- User authentication and authorization
- REST API with Django Ninja
- websockets

## Installation

### Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.10
- pip
- PostgreSQL (or another database)

### Setup

1. Clone the repository:

    ```bash
    git clone https://github.com/1840-Golbal-talent-cloud/GTC-backend
    cd GTC-backend
    ```

2. Create a virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Set up your environment variables:

    Create a `.env` file in the project root directory and add the following:

    ```plaintext
    SECRET_KEY=[secret key]
    DEBUG=True
    DATABASE_URL=[db-url]
    ```

5. Apply the migrations:

    ```bash
    python manage.py migrate
    ```

6. Create a superuser (admin):

    ```bash
    python manage.py createsuperuser
    ```

7. Run the development server:

    ```bash
    python manage.py runserver
    ```

## Configuration

- **Settings:** Configuration settings can be adjusted in the `settings.py` file. Ensure to configure your database, static files, and any third-party services here.
- **Environment Variables:** All sensitive data should be placed in the `.env` file to avoid being committed to version control.

## Usage

### Accessing the Application

After running the server, you can access the application by navigating to `http://127.0.0.1:8000/` in your web browser.

### API Documentation

If your project includes an API, you can access the API documentation at `http://127.0.0.1:8000/api/docs/` (if using tools like `drf-yasg` or `Swagger`).

### Admin Interface

The Django admin interface can be accessed at `http://127.0.0.1:8000/admin/`.

## Running Tests

To run tests for the project, use the following command:

```bash
python manage.py test
