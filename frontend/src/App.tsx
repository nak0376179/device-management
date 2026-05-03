import { useEffect, useState } from 'react';
import * as api from './api';
import LoginForm from './components/LoginForm';
import CommandPanel from './components/CommandPanel';
import type { Device } from './types';

export default function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('jwt'));
  const [devices, setDevices] = useState<Device[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = () => {
    setToken(localStorage.getItem('jwt'));
  };

  const handleLogout = () => {
    localStorage.removeItem('jwt');
    setToken(null);
    setDevices([]);
    setSelected(null);
  };

  useEffect(() => {
    if (!token) return;
    api
      .listDevices()
      .then((res) => {
        setDevices(res.devices);
        setSelected((cur) => cur ?? res.devices[0]?.thingName ?? null);
      })
      .catch((e) => setError(String(e)));
  }, [token]);

  if (!token) {
    return <LoginForm onLogin={handleLogin} />;
  }

  return (
    <div className="app">
      <aside>
        <h2>Devices</h2>
        <ul className="device-list">
          {devices.map((d) => (
            <li key={d.thingName}>
              <button
                className={selected === d.thingName ? 'selected' : ''}
                onClick={() => setSelected(d.thingName)}
              >
                <span className={`dot ${d.connected ? 'online' : 'offline'}`} />
                {d.thingName}
              </button>
            </li>
          ))}
          {devices.length === 0 && <li className="muted">No devices</li>}
        </ul>
        <button className="logout-btn" onClick={handleLogout}>ログアウト</button>
      </aside>

      <main>
        {error && <div className="error">{error}</div>}
        {selected
          ? <CommandPanel thingName={selected} />
          : <div className="muted">Select a device.</div>
        }
      </main>
    </div>
  );
}
