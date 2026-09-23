"""

================================================================================
 ROOM RENTAL PLATFORM — SOUTH AFRICA  ·  SINGLE-FILE EDITION
================================================================================
 Everything is embedded in this one file: application code, all 18 HTML page
 templates, CSS, database schema and demo seed data.

 RUN (pick one):
   pip install fastapi uvicorn jinja2 python-multipart bcrypt Pillow
   uvicorn roomrental:app --host 0.0.0.0 --port 8000

   or simply:
   python roomrental.py            (starts uvicorn automatically)

 HOSTING:
   - VPS: python roomrental.py behind Nginx + certbot (HTTPS activates the
     Secure session cookie automatically).
   - Render/Railway/Fly.io: deploy this file as a Python web service with a
     persistent disk mounted at ./uploads (and ./data when DB_PATH is set).

 DEMO ACCOUNTS (seeded on first run; delete roomrental.db to reseed):
   admin@roomrental.co.za / admin123   (admin)
   thabo@example.co.za / password123   (landlord)
   naledi@example.co.za / password123  (landlord)
   sipho@example.co.za / password123   (tenant)
 Set ADMIN_EMAIL / ADMIN_PASSWORD env vars to override. SEED_DEMO=0 disables
 demo data. DB_PATH env var relocates the SQLite database.
================================================================================
"""

TPL = {'admin.html': '{% extends "base.html" %}{% import "macros.html" as ui %}\n{% block title %}Admin{% endblock %}\n{% block content %}\n<h1>Administration</h1>\n<div class="statgrid">\n  <div class="stat"><b>{{ stats.users }}</b><span>Users</span></div>\n  <div class="stat"><b>{{ stats.tenants }}</b><span>Tenants</span></div>\n  <div class="stat"><b>{{ stats.landlords }}</b><span>Landlords</span></div>\n  <div class="stat"><b>{{ stats.properties }}</b><span>Properties</span></div>\n  <div class="stat"><b>{{ stats.rooms }}</b><span>Rooms</span></div>\n  <div class="stat"><b>{{ stats.available }}</b><span>Available</span></div>\n  <div class="stat"><b>{{ stats.rented }}</b><span>Rented</span></div>\n  <div class="stat"><b>{{ stats.pending }}</b><span>Pending review</span></div>\n  <div class="stat"><b>{{ stats.open_reports }}</b><span>Open reports</span></div>\n  <div class="stat"><b>{{ stats.viewings }}</b><span>Viewings</span></div>\n</div>\n<h2>Listings pending review</h2>\n{% if pending %}\n<div class="grid">{% for r in pending %}\n<div class="card">{{ ui.card(r) }}\n  <div class="cardactions">\n    <form method="post" action="/admin/rooms/{{ r.id }}/action"><button class="btn small" name="action" value="approve">Approve</button></form>\n    <form method="post" action="/admin/rooms/{{ r.id }}/action"><button class="btn small ghost" name="action" value="reject">Reject</button></form>\n    <form method="post" action="/admin/rooms/{{ r.id }}/action"><button class="btn small danger" name="action" value="suspend">Suspend</button></form>\n  </div>\n  <p class="muted small">by {{ r.landlord_name }}</p>\n</div>\n{% endfor %}</div>\n{% else %}<p class="empty">No listings pending review.</p>{% endif %}\n<h2>Open reports</h2>\n{% if reports %}\n<table class="table">\n  <tr><th>Room</th><th>Reason</th><th>Reported by</th><th></th></tr>\n  {% for r in reports %}<tr>\n    <td>{{ r.room_name }}</td><td>{{ r.reason }}</td><td>{{ r.reporter or \'—\' }}</td>\n    <td><form method="post" action="/admin/reports/{{ r.id }}/resolve" style="display:inline">\n      <button class="btn small" name="action" value="resolve">Dismiss</button>\n      <button class="btn small danger" name="action" value="suspend">Suspend listing</button></form></td>\n  </tr>{% endfor %}\n</table>\n{% else %}<p class="empty">No open reports.</p>{% endif %}\n<h2>Users</h2>\n<table class="table">\n  <tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th></th></tr>\n  {% for u in users %}<tr>\n    <td>{{ u.name }}</td><td>{{ u.email }}</td><td>{{ u.role }}</td><td>{{ u.status }}</td>\n    <td>{% if u.role != \'admin\' %}\n      <form method="post" action="/admin/users/{{ u.id }}/action" style="display:inline">\n      {% if u.status == \'active\' %}<button class="btn small danger" name="action" value="suspend">Suspend</button>\n      {% else %}<button class="btn small" name="action" value="activate">Activate</button>{% endif %}\n      </form>{% endif %}</td>\n  </tr>{% endfor %}\n</table>\n{% endblock %}', 'base.html': '<!DOCTYPE html>\n<html lang="en-ZA">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>{% block title %}Room Rental Platform — South Africa{% endblock %}</title>\n<link rel="stylesheet" href="/static/style.css">\n</head>\n<body>\n<header class="topbar">\n  <div class="wrap nav">\n    <a class="logo" href="/">Room<span>Rentals</span><small>.co.za</small></a>\n    <form class="navsearch" action="/search" method="get">\n      <input name="q" placeholder="Search suburb or city… e.g. Observatory" value="{{ q|default(\'\') }}">\n      <button type="submit">Search</button>\n    </form>\n    <nav class="menu">\n      <a href="/search">Browse rooms</a>\n      {% if user %}\n        <a href="/notifications">🔔{% if notif_unread %}<b class="pill">{{ notif_unread }}</b>{% endif %}</a>\n        <a href="/messages">Messages{% if unread %}<b class="pill">{{ unread }}</b>{% endif %}</a>\n        {% if user.role == \'tenant\' %}\n          <a href="/favourites">Saved</a><a href="/viewings">Viewings</a>\n        {% endif %}\n        {% if user.role == \'landlord\' %}\n          <a href="/l/dashboard">Dashboard</a>\n        {% endif %}\n        {% if user.role == \'admin\' %}<a href="/admin">Admin</a>{% endif %}\n        <a href="/profile">{{ user.name }}</a>\n        <a class="btn ghost" href="/logout">Log out</a>\n      {% else %}\n        <a href="/login">Log in</a>\n        <a class="btn" href="/register">Sign up free</a>\n      {% endif %}\n    </nav>\n  </div>\n</header>\n{% if msg %}<div class="flash">{{ msg.replace(\'+\',\' \') }}</div>{% endif %}\n<main class="wrap">\n{% block content %}{% endblock %}\n</main>\n<footer class="footer">\n  <div class="wrap">\n    <p>Browse freely. Register when you need to interact. · Room Rentals Platform — South Africa · R (ZAR) pricing · © {{ year }}</p>\n  </div>\n</footer>\n</body>\n</html>', 'conversation.html': '{% extends "base.html" %}{% block title %}Conversation{% endblock %}\n{% block content %}\n<h1>Conversation about <a href="/rooms/{{ conv.room_id }}">{{ conv.room_name }}</a></h1>\n<div class="thread">\n{% for m in msgs %}\n  <div class="bubble {{ \'me\' if m.sender_id == user.id else \'\' }}">\n    <div class="bmeta">{{ m.sender_name }} · {{ m.created_at[:16].replace(\'T\',\' \') }}</div>\n    <div>{{ m.body }}</div>\n  </div>\n{% endfor %}\n</div>\n<form method="post" class="composer">\n  <input name="body" placeholder="Type a message…" required autocomplete="off">\n  <button class="btn" type="submit">Send</button>\n</form>\n{% endblock %}', 'favourites.html': '{% extends "base.html" %}{% import "macros.html" as ui %}\n{% block title %}Saved rooms{% endblock %}\n{% block content %}\n<h1>Saved rooms</h1>\n{% if cards %}\n<div class="grid">{% for r in cards %}{{ ui.card(r) }}\n  <form method="post" action="/favourites/{{ r.id }}/delete"><button class="btn small ghost">Remove</button></form>\n{% endfor %}</div>\n{% else %}<p class="empty">You haven\'t saved any rooms yet. Tap ♡ on any listing to save it here.</p>{% endif %}\n{% endblock %}', 'index.html': '{% extends "base.html" %}{% import "macros.html" as ui %}\n{% block content %}\n<section class="hero">\n  <h1>Find your next room, anywhere in South Africa</h1>\n  <p>Search thousands of rooms in Johannesburg, Cape Town, Durban, Pretoria and beyond — no account needed.</p>\n  <form class="bigsearch" action="/search" method="get">\n    <input name="q" placeholder="Suburb, city or area…">\n    <select name="province"><option value="">All provinces</option>\n      {% for p in provinces %}<option>{{ p }}</option>{% endfor %}</select>\n    <select name="room_type"><option value="">Any room type</option>\n      {% for t in room_types %}<option>{{ t }}</option>{% endfor %}</select>\n    <button class="btn big" type="submit">Find a room</button>\n  </form>\n  <p class="hint">Popular: <a href="/search?q=Observatory">Observatory</a> · <a href="/search?q=Sandton">Sandton</a> · <a href="/search?q=Umhlanga">Umhlanga</a> · <a href="/search?q=Soshanguve">Soshanguve</a></p>\n</section>\n<section>\n  <h2>Latest rooms</h2>\n  {% if cards %}\n  <div class="grid">{% for r in cards %}{{ ui.card(r) }}{% endfor %}</div>\n  {% else %}<p class="empty">No rooms published yet. Landlords: <a href="/register">list your first room</a>.</p>{% endif %}\n</section>\n<section class="landlordcta">\n  <div><h2>Own a property with rooms to rent?</h2>\n  <p>Create listings with photos, pricing, deposits and amenities — published to thousands of seekers.</p></div>\n  <a class="btn big" href="/register">List your rooms — free</a>\n</section>\n{% endblock %}', 'l_dashboard.html': '{% extends "base.html" %}{% block title %}Landlord dashboard{% endblock %}\n{% block content %}\n<h1>Landlord dashboard</h1>\n<div class="statgrid">\n  <div class="stat"><b>{{ stats.rooms }}</b><span>Total rooms</span></div>\n  <div class="stat"><b>{{ stats.available }}</b><span>Live listings</span></div>\n  <div class="stat"><b>{{ stats.rented }}</b><span>Rented</span></div>\n  <div class="stat"><b>{{ stats.pending }}</b><span>Pending review</span></div>\n</div>\n<p><a class="btn" href="/l/properties/new">+ Add property</a></p>\n<h2>Your properties</h2>\n{% if props %}\n<table class="table">\n  <tr><th>Name</th><th>Location</th><th>Type</th><th>Rooms</th><th></th></tr>\n  {% for p in props %}<tr>\n    <td>{{ p.name }}</td><td>{{ p.suburb }}, {{ p.city }}</td><td>{{ p.property_type }}</td><td>{{ p.room_count }}</td>\n    <td><a class="btn small" href="/l/properties/{{ p.id }}">Manage</a></td>\n  </tr>{% endfor %}\n</table>\n{% else %}<p class="empty">No properties yet. Add your first property to start listing rooms.</p>{% endif %}\n<h2>Pending viewing requests</h2>\n{% if viewings %}\n<table class="table">\n  <tr><th>Room</th><th>Tenant</th><th>Preferred</th><th></th></tr>\n  {% for v in viewings %}<tr>\n    <td>{{ v.room_name }}</td><td>{{ v.tenant_name }}</td><td>{{ v.preferred_date }} {{ v.preferred_time }}</td>\n    <td><form method="post" action="/l/viewings/{{ v.id }}/action" style="display:inline">\n      <button class="btn small" name="action" value="accept">Accept</button>\n      <button class="btn small ghost" name="action" value="decline">Decline</button></form></td>\n  </tr>{% endfor %}\n</table>\n{% else %}<p class="empty">No pending viewing requests.</p>{% endif %}\n{% endblock %}', 'login.html': '{% extends "base.html" %}{% block title %}Log in{% endblock %}\n{% block content %}\n<div class="authbox">\n  <h1>Welcome back</h1>\n  <form method="post" action="/login">\n    <input type="hidden" name="next" value="{{ next }}">\n    <label>Email <input name="email" type="email" required></label>\n    <label>Password <input name="password" type="password" required></label>\n    <button class="btn big" type="submit">Log in</button>\n  </form>\n  <p>New here? <a href="/register">Create a free account</a> — tenants and landlords welcome.</p>\n</div>\n{% endblock %}', 'macros.html': '{% macro card(r) %}\n<div class="card">\n  <a href="/rooms/{{ r.id }}">\n    {% if r.image %}<img src="/uploads/{{ r.image }}" alt="{{ r.name }}">{% else %}<div class="noimg">No photo yet</div>{% endif %}\n    <div class="cardbody">\n      <div class="price">R{{ \'%.0f\'|format(r.monthly_rent) }} <span>/ month</span></div>\n      <div class="title">{{ r.name }}</div>\n      <div class="loc">{{ r.suburb }}, {{ r.city }}</div>\n      <div class="meta">\n        <span>{{ r.room_type }}</span>\n        {% if r.is_furnished %}<span>Furnished</span>{% endif %}\n        <span class="avail">{{ r.status.title() }}</span>\n      </div>\n    </div>\n  </a>\n</div>\n{% endmacro %}', 'messages.html': '{% extends "base.html" %}{% block title %}Messages{% endblock %}\n{% block content %}\n<h1>Messages</h1>\n{% if convs %}\n<div class="convlist">\n{% for c in convs %}\n  <a class="conv" href="/messages/{{ c.id }}">\n    <div><b>{{ c.landlord_name if user.id == c.tenant_id else c.tenant_name }}</b>\n      <span class="muted">re: {{ c.room_name }}</span></div>\n    <div class="preview">{{ c.last_msg or \'\' }}</div>\n    {% if c.unread %}<span class="pill">{{ c.unread }}</span>{% endif %}\n  </a>\n{% endfor %}\n</div>\n{% else %}<p class="empty">No conversations yet. Find a room and message the landlord.</p>{% endif %}\n{% endblock %}', 'notifications.html': '{% extends "base.html" %}{% block title %}Notifications{% endblock %}\n{% block content %}\n<h1>Notifications</h1>\n{% if rows %}\n<ul class="notiflist">{% for n in rows %}\n  <li class="{{ \'unread\' if not n.read }}">{% if n.link %}<a href="{{ n.link }}">{{ n.text }}</a>{% else %}{{ n.text }}{% endif %}\n  <span class="muted">{{ n.created_at[:16].replace(\'T\',\' \') }}</span></li>\n{% endfor %}</ul>\n{% else %}<p class="empty">No notifications yet.</p>{% endif %}\n{% endblock %}', 'profile.html': '{% extends "base.html" %}{% block title %}Profile{% endblock %}\n{% block content %}\n<h1>My profile</h1>\n<form class="formcard" method="post">\n  <label>Full name <input name="name" value="{{ user.name }}" required></label>\n  <label>Phone <input name="phone" value="{{ user.phone }}" placeholder="e.g. 082 123 4567"></label>\n  <p class="muted">Email: {{ user.email }} · Role: {{ user.role|title }} · Member since {{ user.created_at[:10] }}</p>\n  <button class="btn" type="submit">Save changes</button>\n</form>\n{% endblock %}', 'property.html': '{% extends "base.html" %}{% import "macros.html" as ui %}\n{% block title %}{{ p.name }}{% endblock %}\n{% block content %}\n<h1>{{ p.name }}</h1>\n<p class="muted">{{ p.property_type }} · {{ p.suburb }}, {{ p.city }}, {{ p.province }}</p>\n{% if p.general_location %}<p>📍 {{ p.general_location }}</p>{% endif %}\n<p>{{ p.description }}</p>\n<p><a class="btn" href="/l/properties/{{ p.id }}/rooms/new">+ Add room</a>\n<a class="btn ghost" href="/l/dashboard">← Dashboard</a></p>\n<h2>Rooms</h2>\n{% if rooms %}\n<div class="grid">{% for r in rooms %}\n<div class="card">\n  <a href="/rooms/{{ r.id }}">{% if r.image %}<img src="/uploads/{{ r.image }}">{% else %}<div class="noimg">No photo</div>{% endif %}\n  <div class="cardbody"><div class="price">R{{ \'%.0f\'|format(r.monthly_rent) }} <span>/ month</span></div>\n  <div class="title">{{ r.name }}</div>\n  <span class="status s-{{ r.status|lower }}">{{ r.status.replace(\'_\',\' \') }}</span></div></a>\n  <div class="cardactions">\n  {% if r.status in [\'DRAFT\',\'APPROVED\',\'REJECTED\'] %}\n    <form method="post" action="/l/rooms/{{ r.id }}/action"><button class="btn small" name="action" value="submit">Submit for review</button></form>\n  {% endif %}\n  {% if r.status in [\'APPROVED\',\'DRAFT\',\'PENDING_REVIEW\'] %}\n    <form method="post" action="/l/rooms/{{ r.id }}/action"><button class="btn small" name="action" value="publish">Publish now</button></form>\n  {% endif %}\n  {% if r.status in [\'PUBLISHED\',\'AVAILABLE\'] %}\n    <form method="post" action="/l/rooms/{{ r.id }}/action"><button class="btn small ghost" name="action" value="unpublish">Unpublish</button></form>\n    <form method="post" action="/l/rooms/{{ r.id }}/action"><button class="btn small" name="action" value="rented">Mark rented</button></form>\n  {% endif %}\n  {% if r.status in [\'RENTED\',\'RESERVED\',\'UNAVAILABLE\'] %}\n    <form method="post" action="/l/rooms/{{ r.id }}/action"><button class="btn small" name="action" value="available">Re-list</button></form>\n  {% endif %}\n  </div>\n</div>\n{% endfor %}</div>\n{% else %}<p class="empty">No rooms yet — add your first room.</p>{% endif %}\n{% endblock %}', 'property_form.html': '{% extends "base.html" %}{% block title %}Add property{% endblock %}\n{% block content %}\n<h1>Add a property</h1>\n<form class="formcard" method="post">\n  <label>Property name <input name="name" required placeholder="e.g. Observatory Family Home"></label>\n  <label>Property type <select name="property_type">{% for t in prop_types %}<option>{{ t }}</option>{% endfor %}</select></label>\n  <label>Province <select name="province">{% for p in provinces %}<option>{{ p }}</option>{% endfor %}</select></label>\n  <div class="row">\n    <label>City <input name="city" required placeholder="Cape Town"></label>\n    <label>Suburb <input name="suburb" required placeholder="Observatory"></label>\n  </div>\n  <label>General location (public) <input name="general_location" placeholder="5 min walk to taxi rank; near UCT"></label>\n  <label>Street address (kept private) <input name="address_private" placeholder="10 Anson Road"></label>\n  <label>Description <textarea name="description" rows="3"></textarea></label>\n  <button class="btn big" type="submit">Save property</button>\n</form>\n{% endblock %}', 'register.html': '{% extends "base.html" %}{% block title %}Sign up{% endblock %}\n{% block content %}\n<div class="authbox">\n  <h1>Create your free account</h1>\n  <form method="post" action="/register">\n    <label>Full name <input name="name" required></label>\n    <label>Email <input name="email" type="email" required></label>\n    <label>Password (min 8 characters) <input name="password" type="password" minlength="8" required></label>\n    <label>I am a…\n      <select name="role"><option value="tenant">Tenant — looking for a room</option>\n      <option value="landlord">Landlord — renting out rooms</option></select></label>\n    <button class="btn big" type="submit">Sign up</button>\n  </form>\n  <p>Already registered? <a href="/login">Log in</a></p>\n</div>\n{% endblock %}', 'room.html': '{% extends "base.html" %}\n{% block title %}{{ room.name }} — {{ room.suburb }}, {{ room.city }}{% endblock %}\n{% block content %}\n<div class="crumbs"><a href="/search?q={{ room.city }}">{{ room.city }}</a> › <a href="/search?q={{ room.suburb }}">{{ room.suburb }}</a></div>\n<div class="listing">\n  <div class="gallery">\n    {% for img in room.images %}<img src="/uploads/{{ img }}" alt="{{ room.name }} photo">{% else %}<div class="noimg big">No photos yet</div>{% endfor %}\n  </div>\n  <div class="listinginfo">\n    <h1>{{ room.name }}</h1>\n    <div class="loc">{{ room.suburb }}, {{ room.city }} · {{ room.province }}</div>\n    <div class="bigprice">R{{ \'%.0f\'|format(room.monthly_rent) }} <span>/ month</span></div>\n    <table class="facts">\n      <tr><td>Deposit</td><td>R{{ \'%.0f\'|format(room.deposit) }}</td></tr>\n      {% if room.additional_fees %}<tr><td>Additional fees</td><td>R{{ \'%.0f\'|format(room.additional_fees) }}</td></tr>{% endif %}\n      <tr><td>Available from</td><td>{{ room.available_from or \'Immediately\' }}</td></tr>\n      <tr><td>Room type</td><td>{{ room.room_type }}{% if room.is_shared %} · Shared{% endif %}</td></tr>\n      <tr><td>Furnished</td><td>{{ \'Yes\' if room.is_furnished else \'No\' }}</td></tr>\n      <tr><td>Bathroom</td><td>{{ room.bathroom }}</td></tr>\n      <tr><td>Max occupants</td><td>{{ room.occupants }}</td></tr>\n    </table>\n    {% if room.amenities %}\n    <div class="amenities">{% for a in room.amenities.split(\',\') %}<span class="tag">{{ a.strip() }}</span>{% endfor %}</div>\n    {% endif %}\n    <p class="desc">{{ room.description }}</p>\n    {% if room.rules %}<p class="rules"><b>House rules:</b> {{ room.rules }}</p>{% endif %}\n    <div class="propertybox">\n      <h3>{{ room.prop_name }}</h3>\n      <p>{{ room.property_type }} · {{ room.general_location }}</p>\n      <p class="muted">{{ room.prop_description }}</p>\n    </div>\n    <div class="landlordbox">\n      <b>Listed by {{ room.landlord_name }}</b>\n      <span class="muted">Member since {{ room.landlord_since[:10] }}</span>\n    </div>\n    <div class="actions">\n      {% if user %}\n        {% if conv_id %}\n          <a class="btn big" href="/messages/{{ conv_id }}">Open conversation</a>\n        {% else %}\n          <form method="post" action="/rooms/{{ room.id }}/messages/start">\n            <textarea name="body" rows="2" placeholder="Hi, is this room still available?" required></textarea>\n            <button class="btn big" type="submit">Message landlord</button>\n          </form>\n        {% endif %}\n        {% if user.role in [\'tenant\',\'admin\'] %}\n        <form method="post" action="/rooms/{{ room.id }}/viewings" class="viewingform">\n          <b>Request a viewing</b>\n          <input type="date" name="date" required>\n          <input type="time" name="time" required>\n          <input name="message" placeholder="Optional message">\n          <button class="btn" type="submit">Request viewing</button>\n        </form>\n        <form method="post" action="/rooms/{{ room.id }}/favourite">\n          <button class="btn ghost" type="submit">{{ \'♥ Saved\' if fav else \'♡ Save room\' }}</button>\n        </form>\n        {% endif %}\n        <details class="reportbox"><summary>Report this listing</summary>\n          <form method="post" action="/rooms/{{ room.id }}/report">\n            <select name="reason">{% for r in reasons %}<option>{{ r }}</option>{% endfor %}</select>\n            <input name="details" placeholder="Details (optional)">\n            <button class="btn danger" type="submit">Submit report</button>\n          </form>\n        </details>\n      {% else %}\n        <p class="gate"><a class="btn big" href="/login?next=/rooms/{{ room.id }}">Log in to message the landlord</a>\n        <a class="btn ghost" href="/register?next=/rooms/{{ room.id }}">Create a free account</a></p>\n        <p class="muted">You can browse freely — an account is only needed to contact landlords, request viewings or save rooms.</p>\n      {% endif %}\n      <button class="btn ghost" onclick="navigator.clipboard.writeText(location.href);this.textContent=\'Link copied!\'">Share listing</button>\n    </div>\n  </div>\n</div>\n{% endblock %}', 'room_form.html': '{% extends "base.html" %}{% block title %}Add room{% endblock %}\n{% block content %}\n<h1>Add a room</h1>\n<form class="formcard" method="post" enctype="multipart/form-data">\n  <label>Room name <input name="name" required placeholder="e.g. Sunny en-suite room"></label>\n  <div class="row">\n    <label>Room type <select name="room_type">{% for t in room_types %}<option>{{ t }}</option>{% endfor %}</select></label>\n    <label>Bathroom <select name="bathroom"><option value="private">Private</option><option value="shared">Shared</option></select></label>\n    <label>Max occupants <input name="occupants" type="number" min="1" max="6" value="1"></label>\n  </div>\n  <div class="row">\n    <label>Monthly rent (R) <input name="monthly_rent" type="number" min="100" max="100000" required></label>\n    <label>Deposit (R) <input name="deposit" type="number" min="0" value="0"></label>\n    <label>Additional fees (R) <input name="additional_fees" type="number" min="0" value="0"></label>\n  </div>\n  <div class="row">\n    <label>Available from <input name="available_from" type="date"></label>\n    <label class="check"><input type="checkbox" name="is_shared" value="1"> Shared room</label>\n    <label class="check"><input type="checkbox" name="is_furnished" value="1"> Furnished</label>\n  </div>\n  <label>Description <textarea name="description" rows="4" placeholder="What\'s included, condition, vibe of the place…"></textarea></label>\n  <label>Amenities (comma separated) <input name="amenities" placeholder="WiFi, Water, Electricity, Parking, Furnished"></label>\n  <label>House rules <input name="rules" placeholder="No smoking, quiet hours…"></label>\n  <label>Photos (first photo becomes the cover) <input name="images" type="file" accept="image/*" multiple></label>\n  <button class="btn big" type="submit">Save room (draft)</button>\n  <p class="muted">Tip: add at least one photo, then publish or submit for review.</p>\n</form>\n{% endblock %}', 'search.html': '{% extends "base.html" %}{% import "macros.html" as ui %}\n{% block title %}Search rooms — Room Rentals{% endblock %}\n{% block content %}\n<h1>Find a room{% if q %} in “{{ q }}”{% endif %}</h1>\n<form class="filters" action="/search" method="get">\n  <input name="q" value="{{ q }}" placeholder="Suburb / city / keyword">\n  <select name="province"><option value="">All provinces</option>\n    {% for p in provinces %}<option {% if p==province %}selected{% endif %}>{{ p }}</option>{% endfor %}</select>\n  <select name="room_type"><option value="">Any type</option>\n    {% for t in room_types %}<option {% if t==room_type %}selected{% endif %}>{{ t }}</option>{% endfor %}</select>\n  <input name="min_price" type="number" min="0" placeholder="Min R" value="{{ min_price }}">\n  <input name="max_price" type="number" min="0" placeholder="Max R" value="{{ max_price }}">\n  <label><input type="checkbox" name="furnished" value="1" {% if furnished %}checked{% endif %}> Furnished</label>\n  <label><input type="checkbox" name="wifi" value="1" {% if wifi %}checked{% endif %}> WiFi</label>\n  <label><input type="checkbox" name="parking" value="1" {% if parking %}checked{% endif %}> Parking</label>\n  <select name="sort">\n    <option value="new" {% if sort==\'new\' %}selected{% endif %}>Newest</option>\n    <option value="plow" {% if sort==\'plow\' %}selected{% endif %}>Price: low → high</option>\n    <option value="phigh" {% if sort==\'phigh\' %}selected{% endif %}>Price: high → low</option>\n  </select>\n  <button class="btn" type="submit">Filter</button>\n</form>\n<p class="resultcount">{{ cards|length }} room{{ \'s\' if cards|length != 1 }} found</p>\n{% if cards %}\n<div class="grid">{% for r in cards %}{{ ui.card(r) }}{% endfor %}</div>\n{% else %}\n<div class="empty"><p>No rooms match your search. Try:</p>\n<ul><li>A nearby suburb or the city name</li><li>Widening the price range</li><li>Removing some filters</li></ul></div>\n{% endif %}\n{% endblock %}', 'viewings.html': '{% extends "base.html" %}{% block title %}Viewing requests{% endblock %}\n{% block content %}\n<h1>{{ \'Viewing requests received\' if mode == \'landlord\' else \'My viewing requests\' }}</h1>\n{% if rows %}\n<table class="table">\n  <tr><th>Room</th><th>{{ \'Tenant\' if mode == \'landlord\' else \'Location\' }}</th><th>Preferred date</th><th>Status</th>\n  {% if mode == \'tenant\' and rows %}<th>Address</th>{% endif %}</tr>\n  {% for v in rows %}<tr>\n    <td>{{ v.room_name }}</td>\n    <td>{{ v.tenant_name if mode == \'landlord\' else (v.suburb ~ \', \' ~ v.city) }}</td>\n    <td>{{ v.preferred_date }} {{ v.preferred_time }}</td>\n    <td><span class="status s-{{ v.status|lower }}">{{ v.status }}</span></td>\n    {% if mode == \'tenant\' %}<td>{{ v.address_private if v.status == \'ACCEPTED\' else \'Shared when accepted\' }}</td>{% endif %}\n  </tr>{% endfor %}\n</table>\n{% else %}<p class="empty">No viewing requests yet.</p>{% endif %}\n{% endblock %}'}

CSS = ":root{--green:#0e7a4f;--dark:#14211b;--muted:#6b7a72;--bg:#f4f6f5;--card:#fff;--line:#e2e8e4;--danger:#b3362b}\n*{box-sizing:border-box}body{margin:0;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--dark);line-height:1.55}\na{color:var(--green);text-decoration:none}a:hover{text-decoration:underline}\n.wrap{max-width:1100px;margin:0 auto;padding:0 16px}\n.topbar{background:var(--dark);position:sticky;top:0;z-index:10}\n.nav{display:flex;align-items:center;gap:14px;padding:10px 16px;flex-wrap:wrap}\n.logo{color:#fff;font-size:1.2rem;font-weight:800}.logo span{color:#37c98e}.logo small{font-weight:400;color:#9fb3a9;margin-left:2px}\n.navsearch{display:flex;flex:1;min-width:200px;max-width:420px}\n.navsearch input{flex:1;border:0;border-radius:8px 0 0 8px;padding:8px 12px}\n.navsearch button{border:0;background:var(--green);color:#fff;border-radius:0 8px 8px 0;padding:8px 14px;cursor:pointer}\n.menu{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-left:auto}\n.menu a{color:#dfe9e4;font-size:.92rem}.menu a:hover{color:#fff}\n.pill{background:var(--danger);color:#fff;border-radius:999px;padding:0 6px;font-size:.72rem;margin-left:3px}\n.btn{display:inline-block;background:var(--green);color:#fff;border:0;border-radius:8px;padding:9px 16px;font-weight:600;cursor:pointer;font-size:.95rem}\n.btn:hover{opacity:.92;text-decoration:none}.btn.big{padding:12px 24px;font-size:1.02rem}\n.btn.ghost{background:#fff;color:var(--green);border:1.5px solid var(--green)}\n.btn.small{padding:5px 10px;font-size:.82rem}.btn.danger{background:var(--danger)}\n.flash{background:#e7f6ee;border:1px solid #b7e2cc;color:var(--green);padding:10px 16px;text-align:center;font-weight:600}\n.hero{background:linear-gradient(135deg,var(--dark),#1d3a2d);color:#fff;border-radius:0 0 24px 24px;padding:56px 16px 44px;text-align:center;margin:0 -16px 28px}\n.hero h1{font-size:2.1rem;margin:0 0 8px}.hero p{color:#c8d8d0;max-width:560px;margin:0 auto 22px}\n.bigsearch{display:flex;gap:8px;max-width:720px;margin:0 auto;flex-wrap:wrap;justify-content:center}\n.bigsearch input{flex:2;min-width:220px;padding:12px;border-radius:10px;border:0}\n.bigselect,.bigsearch select{padding:12px;border-radius:10px;border:0}\n.hint{margin-top:14px;color:#9fb3a9;font-size:.9rem}.hint a{color:#7fd8ae}\nh2{margin:28px 0 12px}\n.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:18px}\n.card{background:var(--card);border-radius:14px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);display:flex;flex-direction:column}\n.card>a{display:block;color:inherit}.card img{width:100%;height:160px;object-fit:cover}\n.noimg{height:160px;display:flex;align-items:center;justify-content:center;background:#dde5e1;color:var(--muted)}\n.noimg.big{height:320px;border-radius:14px}\n.cardbody{padding:12px 14px}\n.price{font-size:1.25rem;font-weight:800}.price span{font-size:.8rem;color:var(--muted);font-weight:500}\n.title{font-weight:600;margin-top:2px}.loc{color:var(--muted);font-size:.88rem}\n.meta{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}\n.meta span{background:#eef3f0;border-radius:6px;padding:2px 8px;font-size:.75rem}\n.meta .avail{background:#dcf3e7;color:var(--green);font-weight:700}\n.cardactions{display:flex;gap:6px;padding:10px;border-top:1px solid var(--line);flex-wrap:wrap}\n.status{display:inline-block;border-radius:6px;padding:2px 9px;font-size:.75rem;font-weight:700;background:#eee}\n.s-available,.s-published{background:#dcf3e7;color:var(--green)}\n.s-pending_review{background:#fff3d6;color:#8a6d00}.s-rented{background:#e3e7e5;color:var(--muted)}\n.s-draft{background:#eee}.s-suspended{background:#fbe3e0;color:var(--danger)}.s-reserved{background:#e2e8fd;color:#2b4acb}\n.filters{display:flex;gap:8px;flex-wrap:wrap;align-items:center;background:#fff;padding:12px;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.06)}\n.filters input,.filters select{padding:8px;border:1px solid var(--line);border-radius:8px}\n.filters label{font-size:.85rem;display:flex;gap:4px;align-items:center}\n.resultcount{color:var(--muted);font-size:.9rem}\n.empty{background:#fff;border-radius:12px;padding:24px;color:var(--muted)}\n.landlordcta{display:flex;justify-content:space-between;align-items:center;gap:20px;background:#e7f6ee;border-radius:14px;padding:24px;margin:34px 0}\n.listing{display:grid;grid-template-columns:1.1fr 1fr;gap:26px;margin-top:16px}\n@media(max-width:820px){.listing{grid-template-columns:1fr}}\n.gallery img{width:100%;border-radius:12px;margin-bottom:10px;display:block}\n.bigprice{font-size:2rem;font-weight:800;margin:8px 0}.bigprice span{font-size:1rem;color:var(--muted);font-weight:500}\n.facts{width:100%;border-collapse:collapse;margin:10px 0}\n.facts td{padding:7px 4px;border-bottom:1px solid var(--line)}.facts td:first-child{color:var(--muted);width:42%}\n.amenities{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}\n.tag{background:#dcf3e7;color:var(--green);border-radius:999px;padding:3px 12px;font-size:.8rem;font-weight:600}\n.desc{white-space:pre-line}\n.propertybox,.landlordbox{background:#fff;border-radius:12px;padding:14px 16px;margin:12px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}\n.landlordbox{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}\n.actions{margin-top:14px;display:flex;flex-direction:column;gap:10px}\n.actions textarea{width:100%;border:1px solid var(--line);border-radius:8px;padding:8px;font-family:inherit}\n.actions input,.actions select{border:1px solid var(--line);border-radius:8px;padding:8px}\n.viewingform{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}\n.gate{display:flex;gap:10px;flex-wrap:wrap}\n.reportbox{background:#fff3f1;border-radius:10px;padding:10px}\n.reportbox form{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}\n.authbox,.formcard{max-width:460px;margin:30px auto;background:#fff;padding:28px;border-radius:16px;box-shadow:0 2px 10px rgba(0,0,0,.07)}\n.formcard{max-width:640px}\n.authbox label,.formcard label{display:block;margin-bottom:12px;font-weight:600;font-size:.92rem}\n.authbox input,.authbox select,.formcard input,.formcard select,.formcard textarea{width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;margin-top:4px;font-family:inherit}\n.row{display:flex;gap:12px;flex-wrap:wrap}.row label{flex:1;min-width:140px}\nlabel.check{display:flex!important;align-items:center;gap:6px;font-weight:400!important}\nlabel.check input{width:auto!important;margin-top:0!important}\n.statgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin:14px 0}\n.stat{background:#fff;border-radius:12px;padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.05)}\n.stat b{display:block;font-size:1.6rem;color:var(--green)}.stat span{color:var(--muted);font-size:.82rem}\n.table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.05)}\n.table th{background:var(--dark);color:#fff;text-align:left;padding:10px;font-size:.85rem}\n.table td{padding:10px;border-bottom:1px solid var(--line);font-size:.9rem}\n.convlist{display:flex;flex-direction:column;gap:8px}\n.conv{background:#fff;border-radius:12px;padding:14px 16px;display:flex;justify-content:space-between;align-items:center;gap:10px;color:inherit;box-shadow:0 1px 3px rgba(0,0,0,.05)}\n.preview{color:var(--muted);font-size:.88rem;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}\n.thread{display:flex;flex-direction:column;gap:10px;margin:16px 0;max-width:640px}\n.bubble{background:#fff;border-radius:14px;padding:10px 14px;box-shadow:0 1px 3px rgba(0,0,0,.05);max-width:85%}\n.bubble.me{background:var(--green);color:#fff;align-self:flex-end}\n.bubble.me .bmeta{color:#c8ecd9}\n.bmeta{font-size:.72rem;color:var(--muted);margin-bottom:3px}\n.composer{display:flex;gap:8px;max-width:640px}\n.composer input{flex:1;padding:12px;border:1px solid var(--line);border-radius:10px}\n.notiflist{list-style:none;padding:0}\n.notiflist li{background:#fff;padding:12px 16px;border-radius:10px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,.04)}\n.notiflist li.unread{border-left:4px solid var(--green);font-weight:600}\n.notiflist .muted{float:right;font-size:.78rem}\n.muted{color:var(--muted);font-size:.85rem}\n.footer{margin-top:50px;background:var(--dark);color:#9fb3a9;padding:22px 0;font-size:.85rem;text-align:center}\n.crumbs{font-size:.85rem;color:var(--muted);margin-top:14px}\n.small{font-size:.8rem}"

"""
Room Rental Platform — MVP (South Africa)
Self-contained FastAPI application. SQLite database, local image uploads.
Run: uvicorn app:app --host 0.0.0.0 --port 8000
"""
import os, re, sqlite3, uuid, secrets
from datetime import datetime, timedelta
from pathlib import Path
from io import BytesIO

import bcrypt
from PIL import Image
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import jinja2
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = os.environ.get("DB_PATH", str(BASE_DIR / "roomrental.db"))
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@roomrental.co.za")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
SEED_DEMO = os.environ.get("SEED_DEMO", "1") == "1"

PROVINCES = ["Gauteng","Western Cape","KwaZulu-Natal","Eastern Cape","Limpopo",
             "Mpumalanga","North West","Free State","Northern Cape"]
ROOM_TYPES = ["Single","Double","Bachelor","En-suite","Studio"]
PROP_TYPES = ["House","Apartment","Townhouse","Commune / Shared House","Backyard Dwelling","Student Residence"]
REPORT_REASONS = ["Suspected scam","Fake property","Fake photos","Incorrect price",
                  "Incorrect information","Duplicate listing","Property unavailable",
                  "Suspicious landlord","Harassment","Other"]

app = FastAPI(title="Room Rental Platform — SA", docs_url=None, redoc_url=None)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
templates = Jinja2Templates(env=jinja2.Environment(loader=jinja2.DictLoader(TPL), autoescape=True))

from fastapi.responses import Response
@app.get("/static/style.css")
def _style(): return Response(CSS, media_type="text/css")

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

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), next: str = Form("/")):
    return do_login(request, email.strip().lower(), password, next)

def do_login(request, email, password, next_url="/"):
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE email=? AND status='active'", (email,)).fetchone()
    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        conn.close()
        return flash_redirect("/login", "Invalid+email+or+password")
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
