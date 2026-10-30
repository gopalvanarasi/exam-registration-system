import os, sqlite3, hashlib, hmac, secrets
from pathlib import Path
from datetime import date, datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Exam Registration System", page_icon="🎓", layout="wide")
DB = Path(__file__).parent / "exam_registration.db"

def connect():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def hash_pw(p):
    salt = secrets.token_bytes(16)
    return salt.hex()+"$"+hashlib.pbkdf2_hmac("sha256",p.encode(),salt,260000).hex()

def check_pw(p, saved):
    try:
        salt, digest = saved.split("$")
        actual = hashlib.pbkdf2_hmac("sha256",p.encode(),bytes.fromhex(salt),260000).hex()
        return hmac.compare_digest(actual,digest)
    except Exception: return False

def uid(prefix):
    return f"{prefix}-{datetime.now():%y%m%d%H%M%S}-{secrets.token_hex(3).upper()}"

def init():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL,created TEXT);
        CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY,user_id INTEGER UNIQUE REFERENCES users(id),roll_no TEXT UNIQUE,course TEXT,semester INTEGER,phone TEXT);
        CREATE TABLE IF NOT EXISTS exams(id INTEGER PRIMARY KEY,code TEXT UNIQUE,title TEXT,course TEXT,semester INTEGER,exam_date TEXT,exam_time TEXT,venue TEXT,reg_open INTEGER DEFAULT 1,deadline TEXT);
        CREATE TABLE IF NOT EXISTS registrations(id INTEGER PRIMARY KEY,reg_no TEXT UNIQUE,student_id INTEGER REFERENCES students(id),exam_id INTEGER REFERENCES exams(id),status TEXT DEFAULT 'Pending',applied TEXT,reviewed TEXT,UNIQUE(student_id,exam_id));
        CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY,registration_id INTEGER UNIQUE REFERENCES registrations(id),ticket_no TEXT UNIQUE,created TEXT);
        """)
        email=st.secrets.get("ADMIN_EMAIL",os.getenv("ADMIN_EMAIL","admin@examportal.local"))
        password=st.secrets.get("ADMIN_PASSWORD",os.getenv("ADMIN_PASSWORD","Admin@12345"))
        if not c.execute("SELECT id FROM users WHERE email=?",(email.lower(),)).fetchone():
            c.execute("INSERT INTO users(name,email,password,role,created) VALUES(?,?,?,?,?)",
                      ("System Administrator",email.lower(),hash_pw(password),"admin",datetime.now().isoformat()))

def register(name,email,password,roll,course,semester,phone):
    if len(password)<8: raise ValueError("Password must be at least 8 characters.")
    with connect() as c:
        cur=c.execute("INSERT INTO users(name,email,password,role,created) VALUES(?,?,?,?,?)",
                      (name,email.lower(),hash_pw(password),"student",datetime.now().isoformat()))
        c.execute("INSERT INTO students(user_id,roll_no,course,semester,phone) VALUES(?,?,?,?,?)",
                  (cur.lastrowid,roll,course,int(semester),phone))

def login_page():
    st.title("🎓 Exam Registration System")
    st.caption("College examination management portal · No payment gateway")
    a,b=st.columns([1,1])
    with a:
        st.markdown("## Your examinations, organised.")
        st.write("Students can apply for eligible examinations, track approvals and access hall tickets. Administrators manage exams and applications.")
        st.info("Applications are free. Hall tickets are available after admin approval.")
    with b:
        t1,t2=st.tabs(["Sign in","Student registration"])
        with t1:
            with st.form("login"):
                email=st.text_input("Email")
                pw=st.text_input("Password",type="password")
                go=st.form_submit_button("Sign in",use_container_width=True)
            if go:
                with connect() as c: u=c.execute("SELECT * FROM users WHERE email=?",(email.lower().strip(),)).fetchone()
                if u and check_pw(pw,u["password"]):
                    st.session_state.user=dict(u); st.rerun()
                else: st.error("Invalid email or password.")
        with t2:
            with st.form("register"):
                name=st.text_input("Full name")
                em=st.text_input("Email")
                p=st.text_input("Password (8+ characters)",type="password")
                roll=st.text_input("Roll number")
                course=st.text_input("Course (e.g. AIML)")
                sem=st.number_input("Semester",1,12,5)
                phone=st.text_input("Phone (optional)")
                go=st.form_submit_button("Create student account",use_container_width=True)
            if go:
                try:
                    if not all([name.strip(),em.strip(),roll.strip(),course.strip()]): raise ValueError("Fill all required fields.")
                    register(name.strip(),em.strip(),p,roll.strip(),course.strip(),sem,phone.strip())
                    st.success("Account created. Sign in now.")
                except sqlite3.IntegrityError: st.error("Email or roll number already exists.")
                except ValueError as e: st.error(str(e))
    st.divider()
    st.caption("Demo admin: admin@examportal.local | Password: Admin@12345 (change before real use)")

def student_page(u):
    with connect() as c:
        s=c.execute("SELECT * FROM students WHERE user_id=?",(u["id"],)).fetchone()
    if not s: st.error("Student profile not found."); return
    st.title(f"Welcome, {u['name']}")
    st.caption(f"{s['roll_no']} · {s['course']} · Semester {s['semester']}")
    with connect() as c:
        exams=c.execute("SELECT * FROM exams ORDER BY exam_date").fetchall()
        regs=c.execute("""SELECT r.*,e.code,e.title,e.exam_date,e.exam_time,e.venue,t.ticket_no
          FROM registrations r JOIN exams e ON e.id=r.exam_id LEFT JOIN tickets t ON t.registration_id=r.id
          WHERE r.student_id=? ORDER BY r.id DESC""",(s["id"],)).fetchall()
    x,y,z=st.columns(3)
    x.metric("Applications",len(regs)); y.metric("Pending",sum(r["status"]=="Pending" for r in regs)); z.metric("Approved",sum(r["status"]=="Approved" for r in regs))
    st.subheader("Available examinations")
    available=[e for e in exams if e["reg_open"] and e["course"].lower()==s["course"].lower() and int(e["semester"])==int(s["semester"])]
    if not available: st.info("No open examinations match your course and semester.")
    for e in available:
        with st.container(border=True):
            l,r=st.columns([4,1])
            l.markdown(f"**{e['title']}** · `{e['code']}`")
            l.write(f"{e['exam_date']} · {e['exam_time']} · {e['venue']}")
            if r.button("Apply",key=f"apply{e['id']}"):
                try:
                    with connect() as c: c.execute("INSERT INTO registrations(reg_no,student_id,exam_id,status,applied) VALUES(?,?,?,?,?)",
                        (uid("REG"),s["id"],e["id"],"Pending",datetime.now().isoformat()))
                    st.success("Application submitted and awaiting approval."); st.rerun()
                except sqlite3.IntegrityError: st.warning("You already applied for this examination.")
    st.subheader("My registrations")
    if not regs: st.info("No applications yet.")
    for r in regs:
        with st.container(border=True):
            st.markdown(f"**{r['title']}** — {r['status']}")
            st.caption(f"{r['reg_no']} · {r['exam_date']} · {r['exam_time']} · {r['venue']}")
            if r["status"]=="Approved":
                with connect() as c:
                    ticket=c.execute("SELECT * FROM tickets WHERE registration_id=?",(r["id"],)).fetchone()
                    if not ticket:
                        c.execute("INSERT INTO tickets(registration_id,ticket_no,created) VALUES(?,?,?)",
                                  (r["id"],uid("HT"),datetime.now().isoformat()))
                        ticket=c.execute("SELECT * FROM tickets WHERE registration_id=?",(r["id"],)).fetchone()
                txt=f"""EXAMINATION HALL TICKET
Student: {u['name']}
Roll number: {s['roll_no']}
Course: {s['course']} | Semester: {s['semester']}
Examination: {r['title']} ({r['code']})
Date: {r['exam_date']} | Time: {r['exam_time']}
Venue: {r['venue']}
Registration ID: {r['reg_no']}
Hall ticket: {ticket['ticket_no']}
"""
                st.download_button("Download hall ticket",txt,file_name=f"hall-ticket-{ticket['ticket_no']}.txt",key=f"ticket{r['id']}")

def admin_page(u):
    st.title("Administrator dashboard")
    with connect() as c:
        stats=c.execute("SELECT COUNT(*) total,SUM(status='Pending') pending,SUM(status='Approved') approved,SUM(status='Rejected') rejected FROM registrations").fetchone()
        students=c.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        exams_count=c.execute("SELECT COUNT(*) FROM exams").fetchone()[0]
    cols=st.columns(5)
    for col,label,val in zip(cols,["Students","Exams","Applications","Pending","Approved"],[students,exams_count,stats["total"] or 0,stats["pending"] or 0,stats["approved"] or 0]): col.metric(label,val)
    te,ta,ts,tr=st.tabs(["Manage exams","Review applications","Students","Reports"])
    with te:
        st.subheader("Create examination")
        with st.form("examform"):
            a,b=st.columns(2)
            code=a.text_input("Exam code"); title=b.text_input("Exam title")
            course=a.text_input("Course"); sem=b.number_input("Semester",1,12,5)
            d=a.date_input("Exam date",date.today()); tm=b.time_input("Exam time")
            venue=a.text_input("Venue"); deadline=b.date_input("Registration deadline",date.today())
            opened=st.checkbox("Registration open",True)
            submit=st.form_submit_button("Create examination")
        if submit:
            try:
                if not all([code.strip(),title.strip(),course.strip(),venue.strip()]): raise ValueError("Complete all fields.")
                with connect() as c: c.execute("INSERT INTO exams(code,title,course,semester,exam_date,exam_time,venue,reg_open,deadline) VALUES(?,?,?,?,?,?,?,?,?)",
                    (code.strip(),title.strip(),course.strip(),int(sem),d.isoformat(),tm.strftime("%H:%M"),venue.strip(),int(opened),deadline.isoformat()))
                st.success("Exam created."); st.rerun()
            except sqlite3.IntegrityError: st.error("Exam code already exists.")
            except ValueError as e: st.error(str(e))
        with connect() as c: ex=c.execute("SELECT * FROM exams ORDER BY exam_date").fetchall()
        for e in ex:
            a,b,cx=st.columns([4,1,1])
            a.write(f"**{e['title']}** ({e['code']}) · {e['course']} / Sem {e['semester']}")
            b.write("Open" if e["reg_open"] else "Closed")
            if cx.button("Toggle",key=f"toggle{e['id']}"):
                with connect() as con: con.execute("UPDATE exams SET reg_open=? WHERE id=?",(1-e["reg_open"],e["id"]))
                st.rerun()
    with ta:
        with connect() as c:
            rows=c.execute("""SELECT r.id,r.reg_no,r.status,r.applied,u.name,s.roll_no,s.course,s.semester,e.title exam_title,e.code
              FROM registrations r JOIN students s ON s.id=r.student_id JOIN users u ON u.id=s.user_id JOIN exams e ON e.id=r.exam_id ORDER BY r.id DESC""").fetchall()
        if not rows: st.info("No applications yet.")
        for r in rows:
            with st.container(border=True):
                l,rr=st.columns([4,2])
                l.markdown(f"**{r['name']}** · {r['roll_no']} · {r['course']} / Sem {r['semester']}")
                l.write(f"{r['exam_title']} ({r['code']}) · {r['reg_no']} · **{r['status']}**")
                if r["status"]=="Pending":
                    if rr.button("Approve",key=f"ok{r['id']}"):
                        with connect() as c: c.execute("UPDATE registrations SET status='Approved',reviewed=? WHERE id=? AND status='Pending'",(datetime.now().isoformat(),r["id"]))
                        st.rerun()
                    if rr.button("Reject",key=f"no{r['id']}"):
                        with connect() as c: c.execute("UPDATE registrations SET status='Rejected',reviewed=? WHERE id=? AND status='Pending'",(datetime.now().isoformat(),r["id"]))
                        st.rerun()
    with ts:
        with connect() as c: rows=c.execute("SELECT u.name,u.email,s.roll_no,s.course,s.semester,s.phone FROM students s JOIN users u ON u.id=s.user_id").fetchall()
        if rows: st.dataframe(pd.DataFrame([dict(r) for r in rows]),use_container_width=True,hide_index=True)
        else: st.info("No students registered.")
    with tr:
        with connect() as c:
            rows=c.execute("""SELECT e.code,e.title,COUNT(r.id) total,
              SUM(r.status='Approved') approved,SUM(r.status='Pending') pending,SUM(r.status='Rejected') rejected
              FROM exams e LEFT JOIN registrations r ON r.exam_id=e.id GROUP BY e.id ORDER BY e.exam_date""").fetchall()
        if rows:
            df=pd.DataFrame([dict(r) for r in rows]).fillna(0)
            st.dataframe(df,use_container_width=True,hide_index=True)
            st.download_button("Download CSV report",df.to_csv(index=False),"exam-registration-report.csv","text/csv")
        else: st.info("No exam data to report.")

def main():
    init()
    st.sidebar.title("🎓 ExamPortal")
    st.sidebar.caption("Exam Registration System")
    if "user" not in st.session_state:
        login_page(); return
    u=st.session_state.user
    st.sidebar.write(f"**{u['name']}**")
    st.sidebar.caption(u["role"].title())
    if st.sidebar.button("Logout"):
        del st.session_state.user; st.rerun()
    if u["role"]=="admin": admin_page(u)
    else: student_page(u)
    st.sidebar.divider()
    st.sidebar.caption("No payment gateway")

if __name__=="__main__":
    main()
