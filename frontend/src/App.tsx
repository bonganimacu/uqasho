import { FormEvent, useState } from 'react';

type Room = { name: string; area: string; type: string; price: number; detail: string; description: string };

const rooms: Room[] = [
  { name: 'Sunny en-suite room', area: 'Observatory, Cape Town', type: 'En-suite', price: 4200, detail: 'Furnished · WiFi · Water', description: 'A bright north-facing room with built-in cupboards, a desk, fibre-ready internet and a private bathroom.' },
  { name: 'Garden-facing double room', area: 'Observatory, Cape Town', type: 'Double', price: 3800, detail: 'Furnished · Garden · Parking', description: 'A spacious double room opening onto a quiet garden, with a shared bathroom and kitchen access.' },
  { name: 'Sandton bachelor studio', area: 'Sandton, Johannesburg', type: 'Studio', price: 6500, detail: 'Furnished · Parking · Water', description: 'A secure bachelor studio close to Gautrain Sandton station, with a kitchenette and balcony.' },
  { name: 'Student single room', area: 'Soshanguve, Pretoria', type: 'Single', price: 2500, detail: 'WiFi · Water · Shared home', description: 'An affordable room near TUT Soshanguve with a communal kitchen, study room and WiFi.' },
];

export default function App() {
  const [query, setQuery] = useState('');
  const [roomType, setRoomType] = useState('');
  const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
  const [authPrompt, setAuthPrompt] = useState<string | null>(null);
  const [authMode, setAuthMode] = useState<'login' | 'register' | null>(null);
  const [authEmail, setAuthEmail] = useState('');
  const [currentUser, setCurrentUser] = useState<string | null>(null);
  const [currentRole, setCurrentRole] = useState<'tenant' | 'landlord'>('tenant');
  const [authRole, setAuthRole] = useState<'tenant' | 'landlord'>('tenant');
  const [view, setView] = useState<'home' | 'dashboard'>('home');
  const [catalog, setCatalog] = useState(rooms);
  const [savedRooms, setSavedRooms] = useState<string[]>([]);
  const [conversationRoom, setConversationRoom] = useState<Room | null>(null);
  const [viewingRoom, setViewingRoom] = useState<Room | null>(null);
  const [messageText, setMessageText] = useState('');
  const [viewingSubmitted, setViewingSubmitted] = useState(false);

  const filteredRooms = catalog.filter((room) => {
    const matchesQuery = !query || `${room.name} ${room.area}`.toLowerCase().includes(query.toLowerCase());
    return matchesQuery && (!roomType || room.type === roomType);
  });

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api/v1';
    const params = new URLSearchParams({ q: query, roomType });
    try {
      const response = await fetch(`${apiBase}/rooms?${params.toString()}`);
      if (!response.ok) throw new Error('Room search unavailable');
      const apiRooms = await response.json() as Array<{ id: string; name: string; area: string; roomType: string; monthlyRent: number; details: string; description: string }>;
      setCatalog(apiRooms.map((room) => ({ name: room.name, area: room.area, type: room.roomType, price: room.monthlyRent, detail: room.details, description: room.description })));
    } catch {
      setCatalog(rooms);
    }
    document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' });
  }

  function requestAuth(action: string) {
    setAuthPrompt(action);
  }

  function openAuth(mode: 'login' | 'register') {
    setAuthPrompt(null);
    setAuthMode(mode);
  }

  function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCurrentUser(authEmail || 'Tenant');
    setCurrentRole(authMode === 'register' ? authRole : 'tenant');
    setView(authMode === 'register' && authRole === 'landlord' ? 'dashboard' : 'home');
    setAuthMode(null);
    setAuthEmail('');
  }

  return (
    <main className={view === 'dashboard' ? 'dashboard-mode' : ''}>
      <nav className="nav shell">
        <a className="brand" href="/">Room<span>Rentals</span><small>.co.za</small></a>
        <div className="nav-links">
          <a href="#results">Browse rooms</a>
          <a href="#how-it-works">How it works</a>
          {currentUser && currentRole === 'landlord' && <><button className="button button-quiet" onClick={() => setView('home')} type="button">Browse rooms</button><button className="button" onClick={() => setView('dashboard')} type="button">Dashboard</button><button className="button button-quiet" onClick={() => { setCurrentUser(null); setView('home'); }} type="button">Log out</button></>}
          {currentUser && currentRole !== 'landlord' && <><a href="#saved">Saved ({savedRooms.length})</a><button className="button button-quiet" onClick={() => { setCurrentUser(null); setView('home'); }} type="button">Log out</button></>}
          {!currentUser && <><button className="button button-quiet" onClick={() => openAuth('login')} type="button">Log in</button><button className="button" onClick={() => openAuth('register')} type="button">Sign up free</button></>}
        </div>
      </nav>

      {currentUser && currentRole === 'landlord' && <LandlordDashboard />}

      <section className="hero shell">
        <div className="hero-copy">
          <p className="eyebrow">Find your next room in South Africa</p>
          <h1>Search less. Find a place that feels right.</h1>
          <p className="lede">Browse rooms freely, compare the real costs, and speak to landlords when you are ready.</p>
          <form className="searchbar" id="search" onSubmit={search}>
            <label className="sr-only" htmlFor="location">Search by suburb, city or province</label>
            <input id="location" onChange={(event) => setQuery(event.target.value)} placeholder="Suburb, city or province" value={query} />
            <select aria-label="Room type" onChange={(event) => setRoomType(event.target.value)} value={roomType}>
              <option value="">Any room type</option>
              <option>Single</option>
              <option>Double</option>
              <option>Studio</option>
              <option>En-suite</option>
            </select>
            <button className="button" type="submit">Search rooms</button>
          </form>
          <p className="search-note">No account needed to browse listings.</p>
        </div>
        <div className="hero-stat"><strong>R2,500</strong><span>rooms from</span></div>
      </section>

      <section className="section shell" id="results" aria-labelledby="featured-title">
        <div className="section-heading"><div><p className="eyebrow">Start exploring</p><h2 id="featured-title">Rooms worth a closer look</h2></div><a href="#search">View all rooms</a></div>
        {filteredRooms.length === 0 ? <p className="empty-state">No rooms match that search yet. Try another suburb or room type.</p> : <div className="room-grid">{filteredRooms.map((room) => <article className="room-card" key={room.name}><button className="room-image" onClick={() => setSelectedRoom(room)} type="button">{room.area.split(',')[0]}</button><div className="room-body"><p className="location">{room.area}</p><h3>{room.name}</h3><strong>R{room.price.toLocaleString()} pm</strong><p className="muted">{room.detail}</p><button className="card-link" onClick={() => setSelectedRoom(room)} type="button">View room <span aria-hidden="true">-&gt;</span></button></div></article>)}</div>}
      </section>

      {currentUser && <section className="section shell saved-section" id="saved" aria-labelledby="saved-title"><div className="section-heading"><div><p className="eyebrow">Your shortlist</p><h2 id="saved-title">Saved rooms</h2></div></div>{savedRooms.length ? <div className="saved-list">{savedRooms.map((saved) => <span className="saved-item" key={saved}>{saved}<button aria-label={`Remove ${saved}`} onClick={() => setSavedRooms(savedRooms.filter((room) => room !== saved))} type="button">X</button></span>)}</div> : <p className="empty-state">Rooms you save will appear here.</p>}</section>}

      <section className="trust-band" id="how-it-works"><div className="shell trust-grid"><div><p className="eyebrow">Built around your search</p><h2>Browse freely. Register when you need to interact.</h2></div><p>Save favourites, message landlords, request viewings, and keep everything in one place when you are ready.</p></div></section>
      <footer className="shell footer"><span>RoomRentals.co.za</span><span>South African rooms, made easier to find.</span></footer>

      {selectedRoom && <div className="dialog-backdrop" role="presentation" onClick={() => setSelectedRoom(null)}><section className="dialog" role="dialog" aria-modal="true" aria-labelledby="room-title" onClick={(event) => event.stopPropagation()}><button className="dialog-close" onClick={() => setSelectedRoom(null)} type="button" aria-label="Close room details">X</button><p className="eyebrow">{selectedRoom.area}</p><h2 id="room-title">{selectedRoom.name}</h2><p className="room-price">R{selectedRoom.price.toLocaleString()} pm</p><p>{selectedRoom.description}</p><p className="muted">{selectedRoom.detail} · Available now · Deposit required</p><div className="dialog-actions"><button className="button" onClick={() => currentUser ? setConversationRoom(selectedRoom) : requestAuth('message the landlord')} type="button">Message landlord</button><button className="button button-quiet" onClick={() => { setSavedRooms([...new Set([...savedRooms, selectedRoom.name])]); if (!currentUser) requestAuth('save this room'); }} type="button">{savedRooms.includes(selectedRoom.name) ? 'Saved' : 'Save room'}</button><button className="button button-quiet" onClick={() => currentUser ? setViewingRoom(selectedRoom) : requestAuth('request a viewing')} type="button">Request viewing</button></div></section></div>}
      {authPrompt && <div className="dialog-backdrop" role="presentation" onClick={() => setAuthPrompt(null)}><section className="dialog auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-title" onClick={(event) => event.stopPropagation()}><button className="dialog-close" onClick={() => setAuthPrompt(null)} type="button" aria-label="Close authentication prompt">X</button><p className="eyebrow">One more step</p><h2 id="auth-title">{authPrompt[0].toUpperCase() + authPrompt.slice(1)}</h2><p>Create a free tenant account or log in to continue. You can browse every public listing without an account.</p><div className="dialog-actions"><button className="button" onClick={() => openAuth('register')} type="button">Create account</button><button className="button button-quiet" onClick={() => openAuth('login')} type="button">Log in</button></div></section></div>}
      {authMode && <div className="dialog-backdrop" role="presentation" onClick={() => setAuthMode(null)}><form className="dialog auth-dialog" onClick={(event) => event.stopPropagation()} onSubmit={submitAuth}><button className="dialog-close" onClick={() => setAuthMode(null)} type="button" aria-label="Close authentication form">X</button><p className="eyebrow">RoomRentals account</p><h2 id="auth-form-title">{authMode === 'login' ? 'Welcome back' : 'Create your account'}</h2>{authMode === 'register' && <><label className="form-label" htmlFor="auth-role">I am joining as</label><select className="form-input" id="auth-role" onChange={(event) => setAuthRole(event.target.value as 'tenant' | 'landlord')} value={authRole}><option value="tenant">Tenant looking for a room</option><option value="landlord">Landlord listing rooms</option></select></>}<label className="form-label" htmlFor="auth-email">Email address</label><input className="form-input" id="auth-email" onChange={(event) => setAuthEmail(event.target.value)} required type="email" value={authEmail} /><label className="form-label" htmlFor="auth-password">Password</label><input className="form-input" id="auth-password" minLength={8} required type="password" /><div className="dialog-actions"><button className="button" type="submit">{authMode === 'login' ? 'Log in' : 'Create account'}</button><button className="button button-quiet" onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')} type="button">{authMode === 'login' ? 'Need an account?' : 'Already registered?'}</button></div><p className="form-note">Demo mode: this form will connect to the API during backend migration.</p></form></div>}
      {conversationRoom && <div className="dialog-backdrop" role="presentation" onClick={() => setConversationRoom(null)}><form className="dialog" onClick={(event) => event.stopPropagation()} onSubmit={(event) => { event.preventDefault(); setMessageText(''); }}><button className="dialog-close" onClick={() => setConversationRoom(null)} type="button" aria-label="Close conversation">X</button><p className="eyebrow">New conversation</p><h2>{conversationRoom.name}</h2><p>Ask the landlord a clear question about the room, costs, or availability.</p><label className="form-label" htmlFor="message">Message</label><textarea className="form-input message-input" id="message" onChange={(event) => setMessageText(event.target.value)} placeholder="Hi, is this room still available?" required value={messageText} /><div className="dialog-actions"><button className="button" type="submit">Send message</button></div></form></div>}
      {viewingRoom && <div className="dialog-backdrop" role="presentation" onClick={() => setViewingRoom(null)}><form className="dialog" onClick={(event) => event.stopPropagation()} onSubmit={(event) => { event.preventDefault(); setViewingSubmitted(true); }}><button className="dialog-close" onClick={() => setViewingRoom(null)} type="button" aria-label="Close viewing request">X</button>{viewingSubmitted ? <><p className="eyebrow">Request sent</p><h2>Viewing request submitted</h2><p>The landlord will receive your preferred time and respond through the platform.</p><div className="dialog-actions"><button className="button" onClick={() => { setViewingRoom(null); setViewingSubmitted(false); }} type="button">Done</button></div></> : <><p className="eyebrow">Request a viewing</p><h2>{viewingRoom.name}</h2><label className="form-label" htmlFor="viewing-date">Preferred date</label><input className="form-input" id="viewing-date" required type="date" /><label className="form-label" htmlFor="viewing-time">Preferred time</label><input className="form-input" id="viewing-time" required type="time" /><label className="form-label" htmlFor="viewing-message">Optional message</label><textarea className="form-input message-input" id="viewing-message" placeholder="Anything the landlord should know?" /><div className="dialog-actions"><button className="button" type="submit">Send request</button></div></>}</form></div>}
    </main>
  );
}

function LandlordDashboard() {
  const properties = [
    { name: "Thabo's House in Observatory", area: 'Observatory, Cape Town', rooms: 2, available: 2, status: 'Published' },
    { name: 'Sandton Apartment Block', area: 'Sandton, Johannesburg', rooms: 1, available: 1, status: 'Published' },
  ];

  return <section className="dashboard shell" aria-labelledby="dashboard-title">
    <div className="dashboard-header"><div><p className="eyebrow">Landlord workspace</p><h1 id="dashboard-title">Good morning, Thabo.</h1><p className="dashboard-lede">Keep your rooms accurate, respond quickly, and stay on top of viewings.</p></div><button className="button" type="button">+ Add property</button></div>
    <div className="dashboard-stats"><div><strong>2</strong><span>Properties</span></div><div><strong>3</strong><span>Total rooms</span></div><div><strong>3</strong><span>Available</span></div><div><strong>1</strong><span>Viewing request</span></div></div>
    <div className="dashboard-grid"><section className="dashboard-panel"><div className="panel-heading"><div><p className="eyebrow">Your portfolio</p><h2>Properties</h2></div><button className="text-action" type="button">Manage all</button></div><div className="property-list">{properties.map((property) => <article className="property-row" key={property.name}><div className="property-thumb" aria-hidden="true">{property.area.split(',')[0]}</div><div className="property-info"><h3>{property.name}</h3><p>{property.area}</p><span>{property.rooms} rooms · {property.available} available</span></div><b className="status-badge">{property.status}</b><button className="row-action" type="button">Manage</button></article>)}</div></section><section className="dashboard-panel viewing-panel"><div className="panel-heading"><div><p className="eyebrow">Needs attention</p><h2>Viewing requests</h2></div><span className="count-badge">1</span></div><div className="request-card"><div className="request-avatar">SN</div><div><h3>Sipho Nkosi</h3><p>Sunny en-suite room</p><strong>Thursday, 26 September · 14:00</strong></div><div className="request-actions"><button className="button small-button" type="button">Accept</button><button className="button button-quiet small-button" type="button">Decline</button></div></div></section></div>
    <section className="dashboard-panel quick-panel"><div className="panel-heading"><div><p className="eyebrow">Keep moving</p><h2>Quick actions</h2></div></div><div className="quick-actions"><button type="button">Add a room <span>-&gt;</span></button><button type="button">View messages <span>-&gt;</span></button><button type="button">Update availability <span>-&gt;</span></button><button type="button">Open notifications <span>-&gt;</span></button></div></section>
  </section>;
}
