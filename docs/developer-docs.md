# Running the project locally

## Terminal 1 - MongoDB (Docker Compose)

```sh
docker compose up
```

- Keeping this terminal open keeps the docker container alive
- `Ctrl + C` to stop the running process

## Terminal 2 - API (Django Backend)

```sh
cd backend
```

**(linux/macos)**

```sh
source .venv/bin/activate
```

**(windows)**

```powershell
.\.venv\Scripts\Activate.ps1
```

```sh
python -m pip install -r requirements.txt
python -m playwright install --with-deps chromium
python manage.py migrate
python manage.py runserver
```

## Terminal 3 - Background worker (Secondary Django app)

```sh
cd backend
```

**(linux/macos)**

```sh
source .venv/bin/activate
```

**(windows)**

```powershell
.\.venv\Scripts\Activate.ps1
```

```sh
python manage.py run_worker
```

## Terminal 4 - Frontend (Vite - NodeJS)

```sh
cd frontend 
npm install . 
npm run dev
```

Vite forwards `/api` requests to Django `127.0.0.1:8000`

---

| Step | What happens | Where to look |
|---|---|---|
| 1. Look up the repository | The New Project page sends the URL to Django. Django queries GitHub for the repository name, canonical URL, and default branch. | [NewProject.jsx](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/frontend/src/pages/NewProject.jsx) · [github.py](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/backend/git_gallery_app/services/github.py) |
| 2. Check compatibility | Django checks default-branch history, discovers HTML pages, and inspects the homepage and its dependencies. The frontend opens setup when `setup_available` is `true`. | [github.py](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/backend/git_gallery_app/services/github.py) · [dependencies.py](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/backend/git_gallery_app/services/dependencies.py) |
| 3. Select a page and commits | The form defaults to the root homepage. It preselects all commits for histories of ten or fewer and ten evenly spaced commits, including the first and last, for longer histories. The user can adjust the selection. | [commit_selection.py](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/backend/git_gallery_app/commit_selection.py) |
| 4. Queue the analysis | Django resolves the current default-branch head, validates the selection against that revision, saves the project and repository snapshot, and creates a queued job. The API returns `202 Accepted` with IDs the frontend uses to open the timeline. | [analysis_setup.py](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/backend/git_gallery_app/services/analysis_setup.py) · [jobs.py](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/backend/git_gallery_app/services/jobs.py) |
| 5. Capture each version | The worker claims the oldest queued job. For each selected SHA, it downloads the commit archive, serves the files locally, and opens the chosen page in Playwright Chromium. It records each outcome before moving to the next commit. | [worker.py](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/backend/git_gallery_app/services/worker.py) · [capture/cli.py](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/backend/git_gallery_app/capture/cli.py) |
| 6. Display the results | The timeline polls project details about every two seconds while the job is queued or processing. Each successful capture has an image URL. The gallery uses project summaries to show progress and a thumbnail. | [useProject.js](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/frontend/src/hooks/useProject.js) · [projects.py](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/backend/git_gallery_app/services/projects.py) |

### Repository and capture rules

- A supported repository has **1–50 commits** on its default branch and one unambiguous root `index.html`, matched case-insensitively. Other regular `.html` and `.htm` files, including nested pages, can appear in the page picker.
- The dependency checker recognizes a limited set of static HTML, CSS, and image resources. A compatibility response can be `accepted`, `rejected`, `pending`, or `unavailable`. `pending` means the checker could not establish compatibility. Inspect the individual check’s `reason` when diagnosing a result.
- One job captures **one page at 1–10 distinct commits**, in repository history order. Page discovery looks at the current snapshot. An older commit can legitimately lack the selected page.
- Chromium captures a full-page PNG with a default viewport of **1440 × 900**. During rendering, it blocks requests outside the locally served site. A page that relies on externally hosted images or fonts can therefore look different in its capture. [Compatibility checks](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/backend/git_gallery_app/services/github.py) · [Capture settings](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/backend/git_gallery_app/models.py) · [Browser capture](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/backend/git_gallery_app/capture/browser.py)

## Data and storage

| Record | What it stores |
|---|---|
| `Project` | The gallery entry, including its name, repository URL, and creation time. |
| `RepositorySnapshot` | The project’s default branch, pinned head SHA, commit metadata, available HTML pages, and default page at submission time. |
| `Job` | The selected page, viewport, processing status, and one embedded `Capture` per selected commit. |
| `Capture` | The commit SHA, position, status, completion time, relative screenshot path, and any capture error. |

MongoDB stores these records in the `git_gallery` database. The PNG files live under `backend/screenshots/`. Moving an installation requires both the MongoDB data and that directory to preserve viewable results. [Models](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/backend/git_gallery_app/models.py) · [Storage settings](https://github.com/FrankB45/csc325-capstone/blob/dac0b18/backend/config/settings.py)


## REST API reference

The frontend sends JSON for `POST` requests. The screenshot endpoint returns PNG data.

| Method | Endpoint | Request or result |
|---|---|---|
| `GET` | `/api/hello/` | Basic API connectivity check. |
| `POST` | `/api/repo/info/` | Send `url`. Returns repository metadata. |
| `POST` | `/api/repo/compatibility/` | Send `url`. Returns `overall_status`, `setup_available`, and individual check results. HTTP `200` can include a rejected or pending report. |
| `POST` | `/api/repo/commits/` | Send `url`. Returns `commits` in oldest-first order and a `preselected` list of SHAs. |
| `POST` | `/api/analyses/` | Send `url`, `page_path`, `commit_shas`, and optional `name`. A successful submission returns `202` with `project_id`, `snapshot_id`, `job_id`, `status`, and `total_captures`. |
| `GET` | `/api/projects/` | Returns the shared gallery’s `projects` array with progress, status, and thumbnail URLs. |
| `GET` | `/api/projects/<project_id>/` | Returns project details and the latest analysis, including per-commit status, error messages, and screenshot URLs. |
| `GET` | `/api/jobs/<job_id>/captures/<position>/image/` | Returns the completed capture as `image/png`. An unavailable image returns `404`. |

Use the `screenshot_url` returned by project details when displaying an image. The `position` in that URL is the capture’s zero-based position within the job’s selected commits.


### Run the backend test suite

Start MongoDB, activate the backend virtual environment, and run the following from `backend/`:

```sh
python manage.py test git_gallery_app --verbosity 2 --noinput
```