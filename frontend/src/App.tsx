import { useEffect, useState } from 'react';
import * as api from './api';
import LoginForm from './components/LoginForm';
import CommandPanel from './components/CommandPanel';
import type { Device, ShadowDocument } from './types';

const POLL_INTERVAL_MS = 3000;

function formatUptime(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return `${h}h ${m}m ${s}s`;
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(2)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export default function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('jwt'));
  const [devices, setDevices] = useState<Device[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [shadow, setShadow] = useState<ShadowDocument | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingIface, setPendingIface] = useState<string | null>(null);
  const [editingIface, setEditingIface] = useState<string | null>(null);
  const [draftDescription, setDraftDescription] = useState('');

  const handleLogin = () => {
    setToken(localStorage.getItem('jwt'));
  };

  const handleLogout = () => {
    localStorage.removeItem('jwt');
    setToken(null);
    setDevices([]);
    setSelected(null);
    setShadow(null);
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

  useEffect(() => {
    if (!selected || !token) {
      setShadow(null);
      return;
    }
    let cancelled = false;
    const refresh = async () => {
      try {
        const s = await api.getShadow(selected);
        if (!cancelled) {
          setShadow(s);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    };
    refresh();
    const id = setInterval(refresh, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [selected, token]);

  if (!token) {
    return <LoginForm onLogin={handleLogin} />;
  }

  const reported = shadow?.state.reported;
  const desired = shadow?.state.desired;

  const toggleInterface = async (name: string, enabled: boolean) => {
    if (!selected) return;
    setPendingIface(name);
    try {
      const updated = await api.setInterfaceEnabled(selected, name, enabled);
      setShadow(updated);
    } catch (e) {
      setError(String(e));
    } finally {
      setPendingIface(null);
    }
  };

  const saveDescription = async (name: string) => {
    if (!selected) return;
    try {
      const updated = await api.setInterfaceDescription(selected, name, draftDescription);
      setShadow(updated);
      setEditingIface(null);
    } catch (e) {
      setError(String(e));
    }
  };

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

        {selected && reported && (
          <>
            <header>
              <h1>{reported.hostname ?? selected}</h1>
              <span className="muted">version {shadow?.version}</span>
            </header>

            <section>
              <h3>System</h3>
              <dl className="stats">
                <dt>Uptime</dt>
                <dd>{formatUptime(reported.system.uptime_sec)}</dd>
                <dt>CPU</dt>
                <dd>{reported.system.cpu_percent}%</dd>
                <dt>Memory</dt>
                <dd>{reported.system.memory_percent}%</dd>
              </dl>
            </section>

            <section>
              <h3>Interfaces</h3>
              <table className="interfaces">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Description</th>
                    <th>State</th>
                    <th>Rx</th>
                    <th>Tx</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(reported.interfaces).map(([name, iface]) => {
                    const desiredEnabled = desired?.interfaces?.[name]?.enabled;
                    const inFlight =
                      desiredEnabled !== undefined && desiredEnabled !== iface.enabled;
                    const isEditing = editingIface === name;
                    return (
                      <tr key={name}>
                        <td><code>{name}</code></td>
                        <td>
                          {isEditing ? (
                            <span className="edit">
                              <input
                                value={draftDescription}
                                onChange={(e) => setDraftDescription(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') saveDescription(name);
                                  if (e.key === 'Escape') setEditingIface(null);
                                }}
                                autoFocus
                              />
                              <button onClick={() => saveDescription(name)}>Save</button>
                              <button onClick={() => setEditingIface(null)}>Cancel</button>
                            </span>
                          ) : (
                            <span
                              className="editable"
                              onClick={() => {
                                setEditingIface(name);
                                setDraftDescription(iface.description);
                              }}
                            >
                              {iface.description || <em className="muted">(none)</em>}
                            </span>
                          )}
                        </td>
                        <td>
                          <label className="toggle">
                            <input
                              type="checkbox"
                              checked={iface.enabled}
                              disabled={pendingIface === name}
                              onChange={(e) => toggleInterface(name, e.target.checked)}
                            />
                            <span className={iface.enabled ? 'up' : 'down'}>
                              {iface.enabled ? 'up' : 'down'}
                              {inFlight && <em className="muted"> (pending)</em>}
                            </span>
                          </label>
                        </td>
                        <td>{formatBytes(iface.rx_bytes)}</td>
                        <td>{formatBytes(iface.tx_bytes)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </section>

            <CommandPanel thingName={selected} />
          </>
        )}

        {selected && !reported && !error && <div className="muted">Loading…</div>}
        {!selected && <div className="muted">Select a device.</div>}
      </main>
    </div>
  );
}
