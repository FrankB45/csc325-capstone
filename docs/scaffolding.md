### Frontend: React with Vite

The frontend was generated using Vite:

```sh
npm create vite@latest
```

The scaffold used:

- **Project directory:** `frontend`
- **Framework:** React
- **Variant:** JavaScript
- **Linting:** ESLint

- An `/api` development proxy was added to `vite.config.js`.

### Backend: Django with the MongoDB Project Template

The backend was generated inside the `backend` folder using the MongoDB-compatible Django project template:

```sh
python -m django startproject config . --template https://github.com/mongodb-labs/django-mongodb-project/archive/refs/heads/6.0.x.zip
```

In this command:

- `config` is the Django project package containing settings and top-level URL configuration.
- `.` tells Django to generate the project inside the current folder.
- `--template` selects the MongoDB-compatible project template.
- `6.0.x` selects the template branch for Django 6.0.

The application package is named `git_gallery_app`. The corresponding Django app-generation command is:

```sh
python manage.py startapp git_gallery_app
```

After generation:

- Django REST framework was added for JSON API endpoints.
- The database connection was configured for local MongoDB.
- The backend was simplified by removing admin, authentication, sessions, messages, and Django-served template/static-file features.
- Application routes were connected under the `/api/` prefix.
- The `/api/hello/` endpoint was added to verify communication with the frontend.

When changing database models, generate migrations from `backend`:

```sh
python manage.py makemigrations
python manage.py migrate
```

