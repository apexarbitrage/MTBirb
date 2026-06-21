import { useEffect, useState } from "react";

type ApiStatus = "checking" | "ok" | "unreachable";

export function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    fetch("/api/health")
      .then((res) => (res.ok ? setApiStatus("ok") : setApiStatus("unreachable")))
      .catch(() => setApiStatus("unreachable"));
  }, []);

  return (
    <main>
      <h1>MTBirb</h1>
      <p>Trails worth riding, and worth watching.</p>
      <p>API status: {apiStatus}</p>
    </main>
  );
}
