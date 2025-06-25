# 🐞 Biodiversity Tracker

## Executive Summary

This project is a **web-based platform for biodiversity tracking and visualization**, with a particular focus on insect observations. It allows **citizen scientists** and researchers to explore species data, contribute their own observations, and visualize biodiversity patterns across different regions. The platform fetches and stores real-time data from the [iNaturalist API](https://api.inaturalist.org/v1/docs/), and offers an interactive UI for data exploration and contribution. In addition to data automatically synced from iNaturalist, **manual entries** can also be submitted directly through the platform by users.

---

## 🎓 Academic Context

* **University**: Universitat Autònoma de Barcelona (UAB)
* **Department**: Escola d'Enginyeria
* **Degree**: Grau en Enginyeria Informàtica
* **Tutor**: Mehmet Oguz Mulayim ([@omulayim](https://github.com/omulayim))
* **Student**: Ruth Mary Kurian Chandy ([@ruthie-2003](https://github.com/ruthie-2003))
* **TFG Title**: *Development of a Web-Based Platform for Biodiversity Tracking and Visualization*

---

## 📁 Folder Structure

```bash
biodiversity-tracker/
│
├── backend/                     # Django backend API and task scheduler
│   ├── api/                    # Django app for handling species, observations, etc.
│   ├── backend/                # Django project settings and Celery integration
│   ├── media/                  # Uploaded media files
│   ├── Dockerfile              # Dockerfile for backend
│   ├── docker-compose.yml      # Docker Compose config for full stack
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # Vue.js frontend
│   ├── public/                 # Static frontend files
│   ├── vite.config.ts          # Vite bundler config
│   └── package.json            # Frontend dependencies
│
├── LICENSE                     # Project license
├── README.md                   # Project documentation
└── .gitignore                  # Git ignore rules
```

---

## 🚀 Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/ruthie-2003/biodiversity-tracker.git
cd biodiversity-tracker
```

### 2. Configure environment variables

Create `backend/.env` with these required variables:

```bash
# Django
SECRET_KEY="your-django-secret-key-here"  # Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG=True

# Database
MONGO_DB_URI=mongodb://mongodb:27017/biodiversity_tracking

# Email (for user functionality)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

#### 🔐 Important notes:

* Generate a new secret key using the provided Python command
* For email setup:

  * Use an app-specific password if using Gmail
  * Keep DEBUG=True during development to view emails in console
* Never commit the .env file to version control

### 3. Launch with Docker

```bash
cd backend
docker-compose up --build
```

This will start:

* Django + Gunicorn
* MongoDB
* Celery worker and beat

### 4. Run the project

#### Run the backend with full background task support:

```bash
docker compose start
```

#### Run only the backend services (without API data insertion):

```bash
docker compose start web mongodb
```

#### Run the frontend (not dockerized):

```bash
cd frontend
npm install
npm run dev
```

### 5. Access the application

* **Frontend**: [http://localhost:5173](http://localhost:5173)
* **Backend API**: [http://localhost:8000/api/](http://localhost:8000/api/)

### 6. Run tests

**Backend:**

```bash
cd backend
docker-compose exec web python manage.py test api.tests --verbosity=2
```
---

## 🌿 Data Sources: iNaturalist

This platform integrates data from [iNaturalist](https://www.inaturalist.org/), a global community of naturalists and scientists sharing biodiversity observations.

Data is retrieved using the [iNaturalist API](https://api.inaturalist.org/v1/docs/) to:

- Fetch insect species metadata
- Sync observations and location information
- Enrich records with common names, media, and taxonomy

In addition to the iNaturalist-sourced data, users can contribute their own **manual entries** through the platform.

---

## 🛡 License

This project is licensed under the **MIT License**. See the [LICENSE](https://github.com/ruthie-2003/biodiversity-tracker/blob/main/LICENSE) file for details.

---

## ℹ Additional Notes

* Media uploads (images/audio) are stored in `/media/uploads`.
* The database auto-generates fields like `_id`, and avoids duplicates using fields like `species`, `source_id`, and `username`.
* Observations and counts are synced periodically using Celery tasks.
* Frontend is currently not containerized, so you must install and run it manually with `npm install && npm run dev`.
