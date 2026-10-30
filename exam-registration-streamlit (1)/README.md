# Exam Registration System — Streamlit

A Software Engineering Lab mini project with student/admin roles, examination management, registration approval, hall ticket generation and reports. No payment gateway is included.

## Run locally

1. Install Python 3.10+.
2. Extract the ZIP and open this folder in VS Code.
3. In the terminal run:

   `pip install -r requirements.txt`

4. Run:

   `streamlit run streamlit_app.py`

5. Open the local URL shown in the terminal (usually http://localhost:8501).

## Demo admin login

- Email: `admin@examportal.local`
- Password: `Admin@12345`

Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in Streamlit secrets before first run if deploying publicly. The demo credentials are only for classroom testing.

## Deploy to Streamlit Community Cloud

1. Push these files to GitHub.
2. In Streamlit Community Cloud choose New app.
3. Select your repository and branch.
4. Set Main file path to exactly `streamlit_app.py`.
5. Deploy.

## Important data persistence note

This version uses SQLite in a local file named `exam_registration.db`. It is convenient for local development and demos. Streamlit Community Cloud does not guarantee persistence of local app files across restarts or redeployments. For a reliable public deployment, connect a managed database such as Supabase PostgreSQL.

## Included features

- Student registration and login
- Admin dashboard and login
- Create exams and open/close registration
- Course and semester eligibility check
- Duplicate application prevention
- Pending/Approved/Rejected workflow
- Hall ticket number and downloadable ticket after approval
- Student list and CSV reports
- No payment gateway
