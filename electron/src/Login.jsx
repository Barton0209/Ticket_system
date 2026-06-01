import React, { useEffect, useState } from "react";
import { api } from "./api";

export default function Login({ onLogin }) {
  const [logins, setLogins] = useState(["Admin"]);
  const [login, setLogin] = useState("Admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .logins()
      .then((r) => setLogins(r.logins || ["Admin"]))
      .catch(() => setLogins(["Admin"]));
  }, []);

  const submit = async (e) => {
    e?.preventDefault();
    setBusy(true);
    setError("");
    try {
      const session = await api.login(login, password);
      sessionStorage.setItem("ticketSession", JSON.stringify(session));
      onLogin(session);
    } catch (err) {
      setError(err.message || "Ошибка входа");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <h1>Система заявок на билеты</h1>
        <p className="hint">Войдите как в desktop-версии (Users+pass / Admin)</p>

        <label>
          Логин
          <select value={login} onChange={(e) => setLogin(e.target.value)}>
            {logins.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </label>

        <label>
          Пароль
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
          />
        </label>

        {error && <p className="hint bad">{error}</p>}

        <button type="submit" disabled={busy}>
          {busy ? "Вход…" : "Войти"}
        </button>
      </form>
    </div>
  );
}
