"""
Room Rental Platform — MVP (South Africa)
Self-contained FastAPI application. SQLite database, local image uploads.
Run: uvicorn app:app --host 0.0.0.0 --port 8000
"""
import os, re, sqlite3, uuid, secrets, hashlib, smtplib, urllib.parse, urllib.request, json
from datetime import datetime, timedelta
from pathlib import Path
from io import BytesIO
from email.message import EmailMessage

import bcrypt
from PIL import Image
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates as JinjaTemplates

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = os.environ.get("DB_PATH", str(BASE_DIR / "roomrental.db"))
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@roomrental.co.za")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
SEED_DEMO = os.environ.get("SEED_DEMO", "1") == "1"
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
RESET_BASE_URL = os.environ.get("RESET_BASE_URL", "http://localhost:8000")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USERNAME)

PROVINCES = ["Gauteng","Western Cape","KwaZulu-Natal","Eastern Cape","Limpopo",
             "Mpumalanga","North West","Free State","Northern Cape"]
ROOM_TYPES = ["Single","Double","Bachelor","En-suite","Studio"]
PROP_TYPES = ["House","Apartment","Townhouse","Commune / Shared House","Backyard Dwelling","Student Residence"]
REPORT_REASONS = ["Suspected scam","Fake property","Fake photos","Incorrect price",
                  "Incorrect information","Duplicate listing","Property unavailable",
                  "Suspicious landlord","Harassment","Other"]

app = FastAPI(title="Room Rental Platform — SA", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(BASE_DIR/"static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
templates = JinjaTemplates(directory=str(BASE_DIR/"templates"))

# ---------------------------------------------------------------- database
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('tenant','landlord','admin')),
  phone TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS password_reset_tokens(
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    used_at TEXT);
CREATE TABLE IF NOT EXISTS properties(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  landlord_id INTEGER NOT NULL REFERENCES users(id),
  name TEXT NOT NULL, property_type TEXT NOT NULL,
  province TEXT NOT NULL, city TEXT NOT NULL, suburb TEXT NOT NULL,
  general_location TEXT DEFAULT '', address_private TEXT DEFAULT '',
  description TEXT DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rooms(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  name TEXT NOT NULL, room_type TEXT NOT NULL,
  is_shared INTEGER NOT NULL DEFAULT 0, is_furnished INTEGER NOT NULL DEFAULT 0,
  monthly_rent REAL NOT NULL CHECK(monthly_rent BETWEEN 100 AND 100000),
  deposit REAL DEFAULT 0, additional_fees REAL DEFAULT 0,
  available_from TEXT DEFAULT '', occupants INTEGER DEFAULT 1,
  bathroom TEXT DEFAULT 'shared', description TEXT DEFAULT '',
  amenities TEXT DEFAULT '', rules TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'DRAFT',
  created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_rooms_status ON rooms(status);
CREATE INDEX IF NOT EXISTS idx_rooms_prop ON rooms(property_id);
CREATE TABLE IF NOT EXISTS room_images(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  filename TEXT NOT NULL, is_primary INTEGER NOT NULL DEFAULT 0, ord INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS favourites(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL, PRIMARY KEY(user_id, room_id));
CREATE TABLE IF NOT EXISTS conversations(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id INTEGER NOT NULL REFERENCES rooms(id),
  tenant_id INTEGER NOT NULL REFERENCES users(id),
  landlord_id INTEGER NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  sender_id INTEGER NOT NULL REFERENCES users(id),
  body TEXT NOT NULL, read_at TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS viewing_requests(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id INTEGER NOT NULL REFERENCES rooms(id),
  tenant_id INTEGER NOT NULL REFERENCES users(id),
  preferred_date TEXT NOT NULL, preferred_time TEXT NOT NULL,
  message TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'PENDING',
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notifications(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  text TEXT NOT NULL, link TEXT DEFAULT '', read INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reports(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reporter_id INTEGER REFERENCES users(id),
  room_id INTEGER NOT NULL REFERENCES rooms(id),
  reason TEXT NOT NULL, details TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'OPEN', created_at TEXT NOT NULL);
"""

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def now(): return datetime.utcnow().isoformat(timespec="seconds")

def init_db():
    conn = db()
    conn.executescript(SCHEMA)
    if not conn.execute("SELECT 1 FROM users WHERE role='admin' LIMIT 1").fetchone():
        conn.execute("INSERT INTO users(email,password_hash,name,role,created_at) VALUES(?,?,?,?,?)",
                     (ADMIN_EMAIL, bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode(),
                      "Platform Admin", "admin", now()))
    conn.commit(); conn.close()
    if SEED_DEMO:
        seed_demo()

def notify(conn, user_id, text, link=""):
    conn.execute("INSERT INTO notifications(user_id,text,link,created_at) VALUES(?,?,?,?)",
                 (user_id, text, link, now()))

# ---------------------------------------------------------------- seed data
def seed_demo():
    conn = db()
    if conn.execute("SELECT COUNT(*) c FROM properties").fetchone()["c"] > 0:
        conn.close(); return
    demos = [
        ("thabo@example.co.za","Thabo Mokoena","landlord"),
        ("naledi@example.co.za","Naledi Dlamini","landlord"),
        ("sipho@example.co.za","Sipho Nkosi","tenant"),
    ]
    uids = {}
    for email, name, role in demos:
        h = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
        cur = conn.execute("INSERT OR IGNORE INTO users(email,password_hash,name,role,created_at) VALUES(?,?,?,?,?)",
                           (email, h, name, role, now()))
        uids[email] = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]
    props = [
        (uids["thabo@example.co.za"],"Thabo's House in Observatory","House","Western Cape","Cape Town","Observatory",
         "5 min walk to Obz Square taxi stop; close to UCT lower campus","10 Anson Road, Observatory, Cape Town",
         "Large family home with a walled garden, prepaid electricity and fibre-ready rooms."),
        (uids["thabo@example.co.za"],"Sandton Apartment Block","Apartment","Gauteng","Johannesburg","Sandton",
         "Near Gautrain Sandton station and Sandton City","12 Fredman Drive, Sandton, Johannesburg",
         "Secure apartment block with access control, parking bay and rooftop braai area."),
        (uids["naledi@example.co.za"],"Umhlanga Ridge Townhouse","Townhouse","KwaZulu-Natal","Durban","Umhlanga",
         "Close to Gateway Theatre of Shopping and bus routes","45 Palm Boulevard, Umhlanga Ridge, Durban",
         "Modern townhouse complex with pool, 24h security and undercover parking."),
        (uids["naledi@example.co.za"],"Soshanguve Block X Commune","Commune / Shared House","Gauteng","Pretoria","Soshanguve",
         "Near Soshanguve station and TUT Soshanguve campus","88 Block X, Soshanguve, Pretoria",
         "Student-friendly commune with shared kitchen, communal study room and borehole water."),
    ]
    pids = []
    for p in props:
        cur = conn.execute("""INSERT INTO properties(landlord_id,name,property_type,province,city,suburb,
                  general_location,address_private,description,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""", (*p, now()))
        pids.append(cur.lastrowid)
    rooms = [
        (pids[0],"Sunny en-suite room","En-suite",0,1,4200,4200,0,"2026-10-01",1,"private",
         "Bright north-facing en-suite room with built-in cupboards, desk and queen bed. Fibre WiFi and water included; electricity prepaid.",
         "WiFi,Water,Furnished,Parking","No smoking indoors. Visitors until 22:00.","AVAILABLE"),
        (pids[0],"Garden-facing double room","Double",0,1,3800,3800,0,"2026-09-25",2,"shared",
         "Spacious double room opening onto the garden. Shared bathroom with one other room. Water included; electricity shared prepaid.",
         "Water,Garden,Parking","Quiet hours after 21:00.","PUBLISHED"),
        (pids[1],"Sandton bachelor studio","Bachelor",0,1,6500,6500,500,"2026-11-01",1,"private",
         "Bachelor apartment with kitchenette, en-suite bathroom and balcony. Uncapped WiFi, water and one parking bay included. Electricity prepaid.",
         "WiFi,Water,Electricity,Parking,Furnished","No pets. Lease minimum 6 months.","AVAILABLE"),
        (pids[2],"Townhouse double room","Double",0,0,5400,5400,0,"2026-10-15",2,"shared",
         "Furnished double room in secure Umhlanga complex. Shared bathroom, full kitchen access, pool and gym in estate.",
         "WiFi,Water,Parking,Swimming pool,Furnished","Estate rules apply. No loud parties.","PUBLISHED"),
        (pids[3],"Student single room","Single",1,0,2500,2500,0,"2026-09-30",1,"shared",
         "Affordable single room in student commune, 10 min walk to TUT Soshanguve. Communal kitchen, study room and WiFi included; water from borehole.",
         "WiFi,Water","Students preferred. Shared cleaning rota.","AVAILABLE"),
    ]
    for r in rooms:
        conn.execute("""INSERT INTO rooms(property_id,name,room_type,is_shared,is_furnished,monthly_rent,deposit,
            additional_fees,available_from,occupants,bathroom,description,amenities,rules,status,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (*r, now()))
    conn.commit(); conn.close()

# ---------------------------------------------------------------- auth
def current_user(request: Request):
    token = request.cookies.get("rrp_session")
    if not token: return None
    conn = db()
    row = conn.execute("""SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
                          WHERE s.token=? AND s.expires_at>? AND u.status='active'""",
                       (token, now())).fetchone()
    conn.close()
    return row

def require(request: Request, roles=("tenant","landlord","admin")):
    user = current_user(request)
    if not user or user["role"] not in roles:
        next_url = str(request.url.path)
        if request.url.query: next_url += "?" + request.url.query
        return None, RedirectResponse(f"/login?next={next_url}&msg=Please+log+in+to+continue", status_code=303)
    return user, None

def flash_redirect(url, msg): 
    sep = "&" if "?" in url else "?"
    return RedirectResponse(f"{url}{sep}msg={msg}", status_code=303)

# ---------------------------------------------------------------- context
def base_ctx(request: Request, **kw):
    user = current_user(request)
    ctx = {"request": request, "user": user, "msg": request.query_params.get("msg", ""),
           "year": datetime.now().year}
    if user:
        conn = db()
        ctx["unread"] = conn.execute("""SELECT COUNT(*) c FROM messages m JOIN conversations c2 ON c2.id=m.conversation_id
                                        WHERE m.read_at IS NULL AND m.sender_id != ? AND (c2.tenant_id=? OR c2.landlord_id=?)""",
                                     (user["id"], user["id"], user["id"])).fetchone()["c"]
        ctx["notif_unread"] = conn.execute("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND read=0",
                                           (user["id"],)).fetchone()["c"]
        conn.close()
    ctx.update(kw)
    return ctx

def primary_image(conn, room_id):
    row = conn.execute("SELECT filename FROM room_images WHERE room_id=? ORDER BY is_primary DESC, ord, id LIMIT 1",
                       (room_id,)).fetchone()
    return row["filename"] if row else None

# ---------------------------------------------------------------- public pages
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    conn = db()
    rows = conn.execute("""SELECT r.*, p.suburb, p.city, p.province FROM rooms r JOIN properties p ON p.id=r.property_id
                           WHERE r.status IN ('PUBLISHED','AVAILABLE') ORDER BY r.created_at DESC LIMIT 8""").fetchall()
    cards = [dict(r, image=primary_image(conn, r["id"])) for r in rows]
    conn.close()
    return templates.TemplateResponse("index.html", base_ctx(request, cards=cards,
        provinces=PROVINCES, room_types=ROOM_TYPES))

@app.get("/search", response_class=HTMLResponse)
def search(request: Request, q: str = "", province: str = "", room_type: str = "",
           min_price: float = 0, max_price: float = 0, furnished: int = 0,
           wifi: int = 0, parking: int = 0, sort: str = "new"):
    sql = """SELECT r.*, p.suburb, p.city, p.province FROM rooms r JOIN properties p ON p.id=r.property_id
             WHERE r.status IN ('PUBLISHED','AVAILABLE')"""
    params = []
    if q:
        sql += " AND (p.suburb LIKE ? OR p.city LIKE ? OR r.name LIKE ? OR r.description LIKE ?)"
        like = f"%{q}%"; params += [like, like, like, like]
    if province: sql += " AND p.province=?"; params.append(province)
    if room_type: sql += " AND r.room_type=?"; params.append(room_type)
    if min_price: sql += " AND r.monthly_rent>=?"; params.append(min_price)
    if max_price: sql += " AND r.monthly_rent<=?"; params.append(max_price)
    if furnished: sql += " AND r.is_furnished=1"
    if wifi: sql += " AND r.amenities LIKE '%WiFi%'"
    if parking: sql += " AND r.amenities LIKE '%Parking%'"
    sql += {"new": " ORDER BY r.created_at DESC", "plow": " ORDER BY r.monthly_rent ASC",
            "phigh": " ORDER BY r.monthly_rent DESC"}.get(sort, " ORDER BY r.created_at DESC")
    conn = db()
    rows = conn.execute(sql, params).fetchall()
    cards = [dict(r, image=primary_image(conn, r["id"])) for r in rows]
    conn.close()
    return templates.TemplateResponse("search.html", base_ctx(request, cards=cards, q=q, province=province,
        room_type=room_type, min_price=min_price or "", max_price=max_price or "", furnished=furnished,
        wifi=wifi, parking=parking, sort=sort, provinces=PROVINCES, room_types=ROOM_TYPES))

@app.get("/rooms/{room_id}", response_class=HTMLResponse)
def room_detail(request: Request, room_id: int):
    conn = db()
    room = conn.execute("""SELECT r.*, p.name AS prop_name, p.property_type, p.province, p.city, p.suburb,
                           p.general_location, p.description AS prop_description, u.name AS landlord_name,
                           u.created_at AS landlord_since
                           FROM rooms r JOIN properties p ON p.id=r.property_id JOIN users u ON u.id=p.landlord_id
                           WHERE r.id=? AND r.status IN ('PUBLISHED','AVAILABLE','RESERVED')""", (room_id,)).fetchone()
    if not room:
        conn.close()
        raise HTTPException(404, "Listing not found")
    images = conn.execute("SELECT * FROM room_images WHERE room_id=? ORDER BY is_primary DESC, ord, id", (room_id,)).fetchall()
    fav = False
    user = current_user(request)
    if user:
        fav = conn.execute("SELECT 1 FROM favourites WHERE user_id=? AND room_id=?", (user["id"], room_id)).fetchone() is not None
    conv_id = None
    if user:
        c = conn.execute("SELECT id FROM conversations WHERE room_id=? AND tenant_id=?", (room_id, user["id"])).fetchone()
        conv_id = c["id"] if c else None
    conn.close()
    return templates.TemplateResponse("room.html", base_ctx(request, room=dict(room, images=[i["filename"] for i in images]),
        fav=fav, conv_id=conv_id, reasons=REPORT_REASONS))

# ---------------------------------------------------------------- auth pages
@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", base_ctx(request))

@app.post("/register")
def register(request: Request, name: str = Form(...), email: str = Form(...),
             password: str = Form(...), role: str = Form(...)):
    email = email.strip().lower()
    if role not in ("tenant", "landlord") or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return flash_redirect("/register", "Invalid+details")
    if len(password) < 8:
        return flash_redirect("/register", "Password+must+be+at+least+8+characters")
    conn = db()
    try:
        cur = conn.execute("INSERT INTO users(email,password_hash,name,role,created_at) VALUES(?,?,?,?,?)",
                           (email, bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(), name.strip(), role, now()))
        uid = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return flash_redirect("/register", "Email+already+registered")
    conn.commit(); conn.close()
    return do_login(request, email, password)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/"):
    return templates.TemplateResponse("login.html", base_ctx(request, next=next))

def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

def send_password_reset_email(email, reset_url):
    if not SMTP_HOST or not SMTP_FROM:
        return False
    message = EmailMessage()
    message["Subject"] = "Reset your RoomRentals password"
    message["From"] = SMTP_FROM
    message["To"] = email
    message.set_content(f"Use this link to reset your RoomRentals password:\n\n{reset_url}\n\nThis link expires in 30 minutes. If you did not request it, ignore this email.")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        server.starttls()
        if SMTP_USERNAME:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)
    return True

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", base_ctx(request))

@app.post("/forgot-password")
def forgot_password(email: str = Form(...)):
    email = email.strip().lower()
    conn = db()
    user = conn.execute("SELECT id FROM users WHERE email=? AND status='active'", (email,)).fetchone()
    if user:
        raw_token = secrets.token_urlsafe(32)
        conn.execute("DELETE FROM password_reset_tokens WHERE user_id=?", (user["id"],))
        conn.execute("INSERT INTO password_reset_tokens(token_hash,user_id,expires_at) VALUES(?,?,?)",
                     (token_digest(raw_token), user["id"], (datetime.utcnow() + timedelta(minutes=30)).isoformat()))
        conn.commit()
        reset_url = f"{RESET_BASE_URL}/reset-password?token={urllib.parse.quote(raw_token)}"
        try:
            send_password_reset_email(email, reset_url)
        except Exception:
            pass
    conn.close()
    return flash_redirect("/login", "If+that+email+exists,+a+password+reset+link+has+been+sent")

@app.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str = ""):
    conn = db()
    valid = conn.execute("SELECT 1 FROM password_reset_tokens WHERE token_hash=? AND used_at IS NULL AND expires_at>?",
                         (token_digest(token), now())).fetchone() if token else None
    conn.close()
    if not valid:
        return flash_redirect("/login", "That+password+reset+link+is+invalid+or+expired")
    return templates.TemplateResponse("reset_password.html", base_ctx(request, token=token))

@app.post("/reset-password")
def reset_password(token: str = Form(...), password: str = Form(...)):
    if len(password) < 8:
        return flash_redirect(f"/reset-password?token={urllib.parse.quote(token)}", "Password+must+be+at+least+8+characters")
    conn = db()
    reset = conn.execute("SELECT user_id FROM password_reset_tokens WHERE token_hash=? AND used_at IS NULL AND expires_at>?",
                         (token_digest(token), now())).fetchone()
    if not reset:
        conn.close()
        return flash_redirect("/login", "That+password+reset+link+is+invalid+or+expired")
    conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                 (bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(), reset["user_id"]))
    conn.execute("UPDATE password_reset_tokens SET used_at=? WHERE token_hash=?", (now(), token_digest(token)))
    conn.execute("DELETE FROM sessions WHERE user_id=?", (reset["user_id"],))
    conn.commit(); conn.close()
    return flash_redirect("/login", "Password+updated.+You+can+now+log+in")

@app.get("/auth/google")
def google_login(request: Request):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return flash_redirect("/login", "Google+sign-in+is+not+configured+yet")
    state = secrets.token_urlsafe(24)
    params = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID, "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code", "scope": "openid email profile",
        "state": state, "access_type": "offline", "prompt": "select_account"})
    response = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}", status_code=303)
    response.set_cookie("google_oauth_state", state, httponly=True, samesite="lax", secure=request.url.scheme == "https", max_age=600)
    return response

@app.get("/auth/google/callback")
def google_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error or not code or not secrets.compare_digest(state, request.cookies.get("google_oauth_state", "")):
        return flash_redirect("/login", "Google+sign-in+was+cancelled+or+could+not+be+verified")
    try:
        payload = urllib.parse.urlencode({"code": code, "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET, "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"}).encode()
        token_request = urllib.request.Request("https://oauth2.googleapis.com/token", data=payload, method="POST")
        token_data = json.loads(urllib.request.urlopen(token_request, timeout=10).read())
        profile_request = urllib.request.Request("https://openidconnect.googleapis.com/v1/userinfo",
                                                 headers={"Authorization": f"Bearer {token_data['access_token']}"})
        profile = json.loads(urllib.request.urlopen(profile_request, timeout=10).read())
        email = profile.get("email", "").strip().lower()
        if not email or not profile.get("email_verified"):
            raise ValueError("Google email is not verified")
    except Exception:
        return flash_redirect("/login", "Google+sign-in+could+not+be+completed")
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE email=? AND status='active'", (email,)).fetchone()
    if not user:
        conn.execute("INSERT INTO users(email,password_hash,name,role,created_at) VALUES(?,?,?,?,?)",
                     (email, "!google!" + secrets.token_hex(16), profile.get("name") or email.split("@")[0], "tenant", now()))
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return login_response(request, user, "/")

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), next: str = Form("/")):
    return do_login(request, email.strip().lower(), password, next)

def do_login(request, email, password, next_url="/"):
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE email=? AND status='active'", (email,)).fetchone()
    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        conn.close()
        return flash_redirect("/login", "Invalid+email+or+password")
    return login_response(request, user, next_url)

def login_response(request, user, next_url="/"):
    conn = db()
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)",
                 (token, user["id"], (datetime.utcnow()+timedelta(days=30)).isoformat()))
    conn.commit(); conn.close()
    if user["role"] == "admin" and next_url in ("/", ""):
        next_url = "/admin"
    resp = RedirectResponse(next_url or "/", status_code=303)
    resp.set_cookie("rrp_session", token, httponly=True, samesite="lax",
                    secure=request.url.scheme == "https", max_age=30*86400)
    return resp

@app.get("/logout")
def logout(request: Request):
    token = request.cookies.get("rrp_session")
    if token:
        conn = db(); conn.execute("DELETE FROM sessions WHERE token=?", (token,)); conn.commit(); conn.close()
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie("rrp_session")
    return resp

@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request):
    user, redir = require(request)
    if redir: return redir
    return templates.TemplateResponse("profile.html", base_ctx(request))

@app.post("/profile")
def profile_update(request: Request, name: str = Form(...), phone: str = Form("")):
    user, redir = require(request)
    if redir: return redir
    conn = db()
    conn.execute("UPDATE users SET name=?, phone=? WHERE id=?", (name.strip(), phone.strip(), user["id"]))
    conn.commit(); conn.close()
    return flash_redirect("/profile", "Profile+updated")

# ---------------------------------------------------------------- favourites
@app.post("/rooms/{room_id}/favourite")
def favourite(request: Request, room_id: int):
    user, redir = require(request, ("tenant","admin"))
    if redir: return redir
    conn = db()
    conn.execute("INSERT OR IGNORE INTO favourites(user_id,room_id,created_at) VALUES(?,?,?)",
                 (user["id"], room_id, now()))
    conn.commit(); conn.close()
    return flash_redirect(f"/rooms/{room_id}", "Saved+to+favourites")

@app.get("/favourites", response_class=HTMLResponse)
def favourites(request: Request):
    user, redir = require(request, ("tenant","admin"))
    if redir: return redir
    conn = db()
    rows = conn.execute("""SELECT r.*, p.suburb, p.city FROM favourites f JOIN rooms r ON r.id=f.room_id
                           JOIN properties p ON p.id=r.property_id WHERE f.user_id=? ORDER BY f.created_at DESC""",
                        (user["id"],)).fetchall()
    cards = [dict(r, image=primary_image(conn, r["id"])) for r in rows]
    conn.close()
    return templates.TemplateResponse("favourites.html", base_ctx(request, cards=cards))

@app.post("/favourites/{room_id}/delete")
def unfavourite(request: Request, room_id: int):
    user, redir = require(request, ("tenant","admin"))
    if redir: return redir
    conn = db()
    conn.execute("DELETE FROM favourites WHERE user_id=? AND room_id=?", (user["id"], room_id))
    conn.commit(); conn.close()
    return flash_redirect("/favourites", "Removed+from+favourites")

# ---------------------------------------------------------------- messaging
@app.post("/rooms/{room_id}/messages/start")
def start_conversation(request: Request, room_id: int, body: str = Form(...)):
    user, redir = require(request, ("tenant","admin"))
    if redir: return redir
    conn = db()
    room = conn.execute("SELECT r.*, p.landlord_id FROM rooms r JOIN properties p ON p.id=r.property_id WHERE r.id=?", (room_id,)).fetchone()
    if not room:
        conn.close(); raise HTTPException(404)
    conv = conn.execute("SELECT id FROM conversations WHERE room_id=? AND tenant_id=?", (room_id, user["id"])).fetchone()
    if conv:
        cid = conv["id"]
    else:
        cur = conn.execute("INSERT INTO conversations(room_id,tenant_id,landlord_id,created_at,updated_at) VALUES(?,?,?,?,?)",
                           (room_id, user["id"], room["landlord_id"], now(), now()))
        cid = cur.lastrowid
    conn.execute("INSERT INTO messages(conversation_id,sender_id,body,created_at) VALUES(?,?,?,?)",
                 (cid, user["id"], body.strip()[:2000], now()))
    conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now(), cid))
    notify(conn, room["landlord_id"], f"New enquiry about '{room['name']}'", f"/messages/{cid}")
    conn.commit(); conn.close()
    return RedirectResponse(f"/messages/{cid}", status_code=303)

@app.get("/messages", response_class=HTMLResponse)
def messages(request: Request):
    user, redir = require(request)
    if redir: return redir
    conn = db()
    convs = conn.execute("""SELECT c.*, r.name AS room_name, tu.name AS tenant_name, lu.name AS landlord_name,
                            (SELECT body FROM messages m WHERE m.conversation_id=c.id ORDER BY m.id DESC LIMIT 1) AS last_msg,
                            (SELECT COUNT(*) FROM messages m WHERE m.conversation_id=c.id AND m.read_at IS NULL AND m.sender_id!=?) AS unread
                            FROM conversations c JOIN rooms r ON r.id=c.room_id
                            JOIN users tu ON tu.id=c.tenant_id JOIN users lu ON lu.id=c.landlord_id
                            WHERE c.tenant_id=? OR c.landlord_id=? ORDER BY c.updated_at DESC""",
                         (user["id"], user["id"], user["id"])).fetchall()
    conn.close()
    return templates.TemplateResponse("messages.html", base_ctx(request, convs=convs))

@app.get("/messages/{conv_id}", response_class=HTMLResponse)
def conversation(request: Request, conv_id: int):
    user, redir = require(request)
    if redir: return redir
    conn = db()
    conv = conn.execute("""SELECT c.*, r.name AS room_name, r.id AS room_id FROM conversations c
                           JOIN rooms r ON r.id=c.room_id WHERE c.id=? AND (c.tenant_id=? OR c.landlord_id=?)""",
                        (conv_id, user["id"], user["id"])).fetchone()
    if not conv:
        conn.close(); raise HTTPException(404)
    msgs = conn.execute("""SELECT m.*, u.name AS sender_name FROM messages m JOIN users u ON u.id=m.sender_id
                           WHERE m.conversation_id=? ORDER BY m.id""", (conv_id,)).fetchall()
    conn.execute("UPDATE messages SET read_at=? WHERE conversation_id=? AND sender_id!=? AND read_at IS NULL",
                 (now(), conv_id, user["id"]))
    conn.commit(); conn.close()
    return templates.TemplateResponse("conversation.html", base_ctx(request, conv=conv, msgs=msgs))

@app.post("/messages/{conv_id}")
def send_message(request: Request, conv_id: int, body: str = Form(...)):
    user, redir = require(request)
    if redir: return redir
    conn = db()
    conv = conn.execute("SELECT * FROM conversations WHERE id=? AND (tenant_id=? OR landlord_id=?)",
                        (conv_id, user["id"], user["id"])).fetchone()
    if not conv:
        conn.close(); raise HTTPException(404)
    body = body.strip()
    if body:
        conn.execute("INSERT INTO messages(conversation_id,sender_id,body,created_at) VALUES(?,?,?,?)",
                     (conv_id, user["id"], body[:2000], now()))
        conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now(), conv_id))
        other = conv["landlord_id"] if user["id"] == conv["tenant_id"] else conv["tenant_id"]
        notify(conn, other, f"New message from {user['name']}", f"/messages/{conv_id}")
    conn.commit(); conn.close()
    return RedirectResponse(f"/messages/{conv_id}", status_code=303)

# ---------------------------------------------------------------- viewing requests
@app.post("/rooms/{room_id}/viewings")
def create_viewing(request: Request, room_id: int, date: str = Form(...), time: str = Form(...),
                   message: str = Form("")):
    user, redir = require(request, ("tenant","admin"))
    if redir: return redir
    conn = db()
    room = conn.execute("SELECT r.*, p.landlord_id FROM rooms r JOIN properties p ON p.id=r.property_id WHERE r.id=?", (room_id,)).fetchone()
    if not room:
        conn.close(); raise HTTPException(404)
    conn.execute("""INSERT INTO viewing_requests(room_id,tenant_id,preferred_date,preferred_time,message,status,created_at)
                    VALUES(?,?,?,?,?,'PENDING',?)""", (room_id, user["id"], date, time, message.strip()[:500], now()))
    notify(conn, room["landlord_id"], f"Viewing request for '{room['name']}' on {date} {time}", "/l/viewings")
    conn.commit(); conn.close()
    return flash_redirect(f"/rooms/{room_id}", "Viewing+request+sent")

@app.get("/viewings", response_class=HTMLResponse)
def my_viewings(request: Request):
    user, redir = require(request, ("tenant","admin"))
    if redir: return redir
    conn = db()
    rows = conn.execute("""SELECT v.*, r.name AS room_name, p.suburb, p.city, p.address_private
                           FROM viewing_requests v JOIN rooms r ON r.id=v.room_id
                           JOIN properties p ON p.id=r.property_id
                           WHERE v.tenant_id=? ORDER BY v.created_at DESC""", (user["id"],)).fetchall()
    conn.close()
    return templates.TemplateResponse("viewings.html", base_ctx(request, rows=rows, mode="tenant"))

# ---------------------------------------------------------------- landlord
@app.get("/l/dashboard", response_class=HTMLResponse)
def l_dashboard(request: Request):
    user, redir = require(request, ("landlord","admin"))
    if redir: return redir
    conn = db()
    props = conn.execute("""SELECT p.*, (SELECT COUNT(*) FROM rooms r WHERE r.property_id=p.id) AS room_count
                            FROM properties p WHERE p.landlord_id=? ORDER BY p.created_at DESC""", (user["id"],)).fetchall()
    stats = dict(
        rooms=conn.execute("""SELECT COUNT(*) c FROM rooms r JOIN properties p ON p.id=r.property_id
                              WHERE p.landlord_id=?""", (user["id"],)).fetchone()["c"],
        available=conn.execute("""SELECT COUNT(*) c FROM rooms r JOIN properties p ON p.id=r.property_id
                              WHERE p.landlord_id=? AND r.status IN ('PUBLISHED','AVAILABLE')""", (user["id"],)).fetchone()["c"],
        rented=conn.execute("""SELECT COUNT(*) c FROM rooms r JOIN properties p ON p.id=r.property_id
                              WHERE p.landlord_id=? AND r.status='RENTED'""", (user["id"],)).fetchone()["c"],
        pending=conn.execute("""SELECT COUNT(*) c FROM rooms r JOIN properties p ON p.id=r.property_id
                              WHERE p.landlord_id=? AND r.status='PENDING_REVIEW'""", (user["id"],)).fetchone()["c"])
    viewings = conn.execute("""SELECT v.*, r.name AS room_name, u.name AS tenant_name FROM viewing_requests v
                               JOIN rooms r ON r.id=v.room_id JOIN properties p ON p.id=r.property_id
                               JOIN users u ON u.id=v.tenant_id
                               WHERE p.landlord_id=? AND v.status='PENDING' ORDER BY v.created_at DESC""",
                            (user["id"],)).fetchall()
    conn.close()
    return templates.TemplateResponse("l_dashboard.html", base_ctx(request, props=props, stats=stats, viewings=viewings))

@app.get("/l/properties/new", response_class=HTMLResponse)
def property_new(request: Request):
    user, redir = require(request, ("landlord","admin"))
    if redir: return redir
    return templates.TemplateResponse("property_form.html", base_ctx(request, p=None,
        provinces=PROVINCES, prop_types=PROP_TYPES))

@app.post("/l/properties/new")
def property_create(request: Request, name: str = Form(...), property_type: str = Form(...),
                    province: str = Form(...), city: str = Form(...), suburb: str = Form(...),
                    general_location: str = Form(""), address_private: str = Form(""), description: str = Form("")):
    user, redir = require(request, ("landlord","admin"))
    if redir: return redir
    conn = db()
    cur = conn.execute("""INSERT INTO properties(landlord_id,name,property_type,province,city,suburb,
                          general_location,address_private,description,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                       (user["id"], name.strip(), property_type, province, city.strip(), suburb.strip(),
                        general_location.strip(), address_private.strip(), description.strip(), now()))
    conn.commit(); conn.close()
    return RedirectResponse(f"/l/properties/{cur.lastrowid}", status_code=303)

@app.get("/l/properties/{pid}", response_class=HTMLResponse)
def property_detail(request: Request, pid: int):
    user, redir = require(request, ("landlord","admin"))
    if redir: return redir
    conn = db()
    prop = conn.execute("SELECT * FROM properties WHERE id=? AND landlord_id=?", (pid, user["id"])).fetchone()
    if not prop:
        conn.close(); raise HTTPException(404)
    rooms = conn.execute("SELECT * FROM rooms WHERE property_id=? ORDER BY id DESC", (pid,)).fetchall()
    rooms = [dict(r, image=primary_image(conn, r["id"])) for r in rooms]
    conn.close()
    return templates.TemplateResponse("property.html", base_ctx(request, p=prop, rooms=rooms, room_types=ROOM_TYPES))

@app.get("/l/properties/{pid}/rooms/new", response_class=HTMLResponse)
def room_new(request: Request, pid: int):
    user, redir = require(request, ("landlord","admin"))
    if redir: return redir
    conn = db()
    prop = conn.execute("SELECT * FROM properties WHERE id=? AND landlord_id=?", (pid, user["id"])).fetchone()
    conn.close()
    if not prop: raise HTTPException(404)
    return templates.TemplateResponse("room_form.html", base_ctx(request, pid=pid, r=None, room_types=ROOM_TYPES))

def save_images(files, room_id):
    saved = []
    for i, f in enumerate(files):
        if not f.filename: continue
        raw = f.file.read()
        if len(raw) > 10*1024*1024: continue
        try:
            img = Image.open(BytesIO(raw)); img.verify()
            img = Image.open(BytesIO(raw))
            if img.format not in ("JPEG","PNG","WEBP"): continue
            img.thumbnail((1600,1600))
            img = img.convert("RGB")
            fname = f"{uuid.uuid4().hex}.jpg"
            img.save(UPLOAD_DIR/fname, "JPEG", quality=82)
            saved.append((fname, 1 if i == 0 else 0, i))
        except Exception:
            continue
    return saved

@app.post("/l/properties/{pid}/rooms/new")
def room_create(request: Request, pid: int, name: str = Form(...), room_type: str = Form(...),
                is_shared: int = Form(0), is_furnished: int = Form(0),
                monthly_rent: float = Form(...), deposit: float = Form(0),
                additional_fees: float = Form(0), available_from: str = Form(""),
                occupants: int = Form(1), bathroom: str = Form("shared"),
                description: str = Form(""), amenities: str = Form(""), rules: str = Form(""),
                images: list[UploadFile] = File(default=[])):
    user, redir = require(request, ("landlord","admin"))
    if redir: return redir
    conn = db()
    prop = conn.execute("SELECT id FROM properties WHERE id=? AND landlord_id=?", (pid, user["id"])).fetchone()
    if not prop:
        conn.close(); raise HTTPException(404)
    if not (100 <= monthly_rent <= 100000):
        conn.close(); return flash_redirect(f"/l/properties/{pid}/rooms/new", "Rent+must+be+between+R100+and+R100000")
    cur = conn.execute("""INSERT INTO rooms(property_id,name,room_type,is_shared,is_furnished,monthly_rent,deposit,
        additional_fees,available_from,occupants,bathroom,description,amenities,rules,status,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,'DRAFT',?)""",
        (pid, name.strip(), room_type, is_shared, is_furnished, monthly_rent, deposit, additional_fees,
         available_from, occupants, bathroom, description.strip(), amenities.strip(), rules.strip(), now()))
    rid = cur.lastrowid
    for fname, prim, ordv in save_images(images, rid):
        conn.execute("INSERT INTO room_images(room_id,filename,is_primary,ord) VALUES(?,?,?,?)", (rid, fname, prim, ordv))
    conn.commit(); conn.close()
    return RedirectResponse(f"/l/properties/{pid}", status_code=303)

@app.post("/l/rooms/{rid}/action")
def room_action(request: Request, rid: int, action: str = Form(...)):
    user, redir = require(request, ("landlord","admin"))
    if redir: return redir
    conn = db()
    room = conn.execute("""SELECT r.*, p.landlord_id FROM rooms r JOIN properties p ON p.id=r.property_id
                           WHERE r.id=? AND p.landlord_id=?""", (rid, user["id"])).fetchone()
    if not room:
        conn.close(); raise HTTPException(404)
    transitions = {
        "submit": (("DRAFT","APPROVED","REJECTED"), "PENDING_REVIEW"),
        "publish": (("APPROVED","DRAFT","PENDING_REVIEW"), "PUBLISHED"),
        "unpublish": (("PUBLISHED","AVAILABLE"), "DRAFT"),
        "rented": (("PUBLISHED","AVAILABLE","RESERVED"), "RENTED"),
        "available": (("RENTED","UNAVAILABLE","RESERVED"), "AVAILABLE"),
    }
    allowed, target = transitions.get(action, ((), None))
    if target and room["status"] in allowed:
        if action == "publish":
            has_img = conn.execute("SELECT 1 FROM room_images WHERE room_id=? LIMIT 1", (rid,)).fetchone()
            if not has_img:
                conn.close(); return flash_redirect(f"/l/properties/{room['property_id']}", "Add+at+least+one+image+before+publishing")
        conn.execute("UPDATE rooms SET status=? WHERE id=?", (target, rid))
    conn.commit(); conn.close()
    return flash_redirect(f"/l/properties/{room['property_id']}", f"Room+{action}ed")

@app.get("/l/viewings", response_class=HTMLResponse)
def l_viewings(request: Request):
    user, redir = require(request, ("landlord","admin"))
    if redir: return redir
    conn = db()
    rows = conn.execute("""SELECT v.*, r.name AS room_name, u.name AS tenant_name, u.phone AS tenant_phone
                           FROM viewing_requests v JOIN rooms r ON r.id=v.room_id
                           JOIN properties p ON p.id=r.property_id JOIN users u ON u.id=v.tenant_id
                           WHERE p.landlord_id=? ORDER BY v.created_at DESC""", (user["id"],)).fetchall()
    conn.close()
    return templates.TemplateResponse("viewings.html", base_ctx(request, rows=rows, mode="landlord"))

@app.post("/l/viewings/{vid}/action")
def viewing_action(request: Request, vid: int, action: str = Form(...)):
    user, redir = require(request, ("landlord","admin"))
    if redir: return redir
    conn = db()
    v = conn.execute("""SELECT v.*, r.name AS room_name FROM viewing_requests v JOIN rooms r ON r.id=v.room_id
                        JOIN properties p ON p.id=r.property_id WHERE v.id=? AND p.landlord_id=?""",
                     (vid, user["id"])).fetchone()
    if not v:
        conn.close(); raise HTTPException(404)
    mapping = {"accept": "ACCEPTED", "decline": "DECLINED", "cancel": "CANCELLED"}
    if action in mapping and v["status"] in ("PENDING","ACCEPTED"):
        status = mapping[action]
        conn.execute("UPDATE viewing_requests SET status=? WHERE id=?", (status, vid))
        notify(conn, v["tenant_id"], f"Your viewing for '{v['room_name']}' was {status.lower()}", "/viewings")
    conn.commit(); conn.close()
    return flash_redirect("/l/viewings", "Viewing+updated")

# ---------------------------------------------------------------- reporting
@app.post("/rooms/{room_id}/report")
def report(request: Request, room_id: int, reason: str = Form(...), details: str = Form("")):
    user, redir = require(request)
    if redir: return redir
    conn = db()
    conn.execute("INSERT INTO reports(reporter_id,room_id,reason,details,status,created_at) VALUES(?,?,?,?,'OPEN',?)",
                 (user["id"], room_id, reason, details.strip()[:1000], now()))
    conn.commit(); conn.close()
    return flash_redirect(f"/rooms/{room_id}", "Report+submitted.+Our+team+will+review+it.")

# ---------------------------------------------------------------- notifications
@app.get("/notifications", response_class=HTMLResponse)
def notifications(request: Request):
    user, redir = require(request)
    if redir: return redir
    conn = db()
    rows = conn.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 50", (user["id"],)).fetchall()
    conn.execute("UPDATE notifications SET read=1 WHERE user_id=?", (user["id"],))
    conn.commit(); conn.close()
    return templates.TemplateResponse("notifications.html", base_ctx(request, rows=rows))

# ---------------------------------------------------------------- admin
@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    user, redir = require(request, ("admin",))
    if redir: return redir
    conn = db()
    stats = {k: conn.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"] for k, t in [
        ("users","users"),("landlords","users WHERE role='landlord'"),("tenants","users WHERE role='tenant'"),
        ("properties","properties"),("rooms","rooms"),
        ("available","rooms WHERE status IN ('PUBLISHED','AVAILABLE')"),
        ("rented","rooms WHERE status='RENTED'"),("pending","rooms WHERE status='PENDING_REVIEW'"),
        ("open_reports","reports WHERE status='OPEN'"),("viewings","viewing_requests")]}
    pending = conn.execute("""SELECT r.*, p.suburb, p.city, u.name AS landlord_name FROM rooms r
                              JOIN properties p ON p.id=r.property_id JOIN users u ON u.id=p.landlord_id
                              WHERE r.status='PENDING_REVIEW' ORDER BY r.created_at""").fetchall()
    pending = [dict(r, image=primary_image(conn, r["id"])) for r in pending]
    reports = conn.execute("""SELECT rep.*, u.name AS reporter, r.name AS room_name FROM reports rep
                              LEFT JOIN users u ON u.id=rep.reporter_id JOIN rooms r ON r.id=rep.room_id
                              WHERE rep.status='OPEN' ORDER BY rep.created_at DESC LIMIT 20""").fetchall()
    users = conn.execute("SELECT id,name,email,role,status,created_at FROM users ORDER BY created_at DESC LIMIT 20").fetchall()
    conn.close()
    return templates.TemplateResponse("admin.html", base_ctx(request, stats=stats, pending=pending,
        reports=reports, users=users))

@app.post("/admin/rooms/{rid}/action")
def admin_room(request: Request, rid: int, action: str = Form(...)):
    user, redir = require(request, ("admin",))
    if redir: return redir
    mapping = {"approve": "APPROVED", "reject": "DRAFT", "suspend": "SUSPENDED", "remove": "SUSPENDED"}
    if action in mapping:
        conn = db()
        room = conn.execute("SELECT r.*, p.landlord_id FROM rooms r JOIN properties p ON p.id=r.property_id WHERE r.id=?", (rid,)).fetchone()
        if room:
            conn.execute("UPDATE rooms SET status=? WHERE id=?", (mapping[action], rid))
            notify(conn, room["landlord_id"], f"Your listing '{room['name']}' was {action}d by moderation.", "/l/dashboard")
            conn.commit()
        conn.close()
    return flash_redirect("/admin", "Listing+updated")

@app.post("/admin/reports/{rep_id}/resolve")
def admin_resolve(request: Request, rep_id: int, action: str = Form(...)):
    user, redir = require(request, ("admin",))
    if redir: return redir
    conn = db()
    rep = conn.execute("SELECT * FROM reports WHERE id=? AND status='OPEN'", (rep_id,)).fetchone()
    if rep:
        conn.execute("UPDATE reports SET status='RESOLVED' WHERE id=?", (rep_id,))
        if action == "suspend":
            conn.execute("UPDATE rooms SET status='SUSPENDED' WHERE id=?", (rep["room_id"],))
        if rep["reporter_id"]:
            notify(conn, rep["reporter_id"], "Thank you — your report has been reviewed and action taken.", "/")
        conn.commit()
    conn.close()
    return flash_redirect("/admin", "Report+resolved")

@app.post("/admin/users/{uid}/action")
def admin_user(request: Request, uid: int, action: str = Form(...)):
    user, redir = require(request, ("admin",))
    if redir: return redir
    if action in ("suspend","activate"):
        conn = db()
        conn.execute("UPDATE users SET status=? WHERE id=?", ("suspended" if action=="suspend" else "active", uid))
        if action == "suspend":
            conn.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
        conn.commit(); conn.close()
    return flash_redirect("/admin", "User+updated")

# ---------------------------------------------------------------- boot
@app.on_event("startup")
def startup():
    UPLOAD_DIR.mkdir(exist_ok=True)
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
