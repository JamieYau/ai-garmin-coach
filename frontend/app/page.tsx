const metricCards = [
  { label: "Training load", value: "Sync pending" },
  { label: "Recovery", value: "Awaiting Garmin" },
  { label: "Coach insight", value: "Ready for first run" }
];

export default function Home() {
  return (
    <main
    className="min-h-screen p-12 bg-background text-foreground"
    >
      <section style={{ maxWidth: "960px" }}>
        <p style={{ margin: "0 0 12px", color: "#516170", fontSize: "14px"}}>
          AI Garmin Coach
        </p>
        <h1 style={{ margin: "0 0 16px", fontSize: "40px", lineHeight: 1.1 }}>
          Dashboard skeleton is running.
        </h1>
        <p style={{ margin: "0 0 32px", maxWidth: "640px", color: "#516170", lineHeight: 1.6 }}>
          This App Router entry point is ready for Garmin metrics, recovery data, and structured
          coaching recommendations as the frontend phases continue.
        </p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "16px"
          }}
        >
          {metricCards.map((metric) => (
            <article
              key={metric.label}
              style={{
                minHeight: "120px",
                padding: "20px",
                border: "1px solid #d8e0e8",
                borderRadius: "8px",
                background: "#ffffff"
              }}
            >
              <h2 style={{ margin: "0 0 24px", color: "#516170", fontSize: "14px" }}>
                {metric.label}
              </h2>
              <p style={{ margin: 0, fontSize: "20px", fontWeight: 700 }}>{metric.value}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
