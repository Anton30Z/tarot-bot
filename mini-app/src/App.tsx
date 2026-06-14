import "./styles.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export function App() {
  return (
    <main className="app-shell">
      <section className="intro">
        <p className="eyebrow">Telegram Mini App</p>
        <h1>Tarot</h1>
        <p className="description">
          Каркас Mini App готов. Следующий шаг - подключить каталог раскладов и визуальный выбор закрытых карт.
        </p>
        <a className="health-link" href={`${apiBaseUrl}/health`} target="_blank" rel="noreferrer">
          Проверить backend health
        </a>
      </section>
    </main>
  );
}
