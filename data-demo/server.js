const express = require("express");
const { Pool } = require("pg");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3000;
const POLL_INTERVAL_MS = 2000;

const pool = new Pool({
  connectionString:
    process.env.DATABASE_URL ||
    "postgres://localhost/easycron?sslmode=disable",
  ssl:
    process.env.NODE_ENV === "production"
      ? { rejectUnauthorized: false }
      : false,
});

app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

let clients = [];
let lastSnapshotId = 0;

function broadcast(data) {
  clients.forEach((client) => {
    client.res.write(`data: ${JSON.stringify(data)}\n\n`);
  });
}

async function pollForNewSnapshots() {
  try {
    const result = await pool.query(
      "SELECT * FROM price_snapshots WHERE id > $1 ORDER BY id ASC",
      [lastSnapshotId],
    );
    for (const row of result.rows) {
      broadcast({ type: "new-snapshot", snapshot: row });
      lastSnapshotId = row.id;
    }
  } catch (err) {
    console.error("Poll error:", err.message);
  }
}

setInterval(pollForNewSnapshots, POLL_INTERVAL_MS);

app.get("/api/snapshots", async (req, res) => {
  try {
    const range = req.query.range || "24h";
    let interval;
    switch (range) {
      case "1h": interval = "1 hour"; break;
      case "7d": interval = "7 days"; break;
      case "30d": interval = "30 days"; break;
      default: interval = "24 hours";
    }
    const result = await pool.query(
      `SELECT * FROM price_snapshots
       WHERE fetched_at > NOW() - INTERVAL '${interval}'
       ORDER BY fetched_at DESC`,
    );
    if (result.rows.length > 0) {
      lastSnapshotId = result.rows[0].id;
    }
    res.json(result.rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Database error" });
  }
});

app.get("/api/alerts", async (req, res) => {
  try {
    const result = await pool.query(
      "SELECT * FROM price_alerts ORDER BY id DESC LIMIT 20",
    );
    res.json(result.rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Database error" });
  }
});

app.get("/api/executions", async (req, res) => {
  try {
    const result = await pool.query(
      "SELECT * FROM execution_log ORDER BY received_at DESC LIMIT 20",
    );
    res.json(result.rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Database error" });
  }
});

app.get("/api/stats", async (req, res) => {
  try {
    const stats = await pool.query(`
      SELECT
        COUNT(*) as total_executions,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
        SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
        AVG(EXTRACT(EPOCH FROM (received_at - fired_at)) * 1000) as avg_latency_ms
      FROM execution_log
    `);
    res.json(stats.rows[0]);
  } catch (err) {
    console.error("Stats error:", err);
    res.status(500).json({ error: "Database error" });
  }
});

app.get("/api/health", async (req, res) => {
  const easycronUrl = process.env.EASYCRON_URL || "http://localhost:8080";
  const results = { easycron: null, database: null, timestamp: new Date().toISOString() };

  try {
    const dbResult = await pool.query("SELECT 1");
    results.database = { status: "ok", latency: null };
  } catch (err) {
    results.database = { status: "error", error: err.message };
  }

  try {
    const start = Date.now();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    const response = await fetch(`${easycronUrl}/health`, { signal: controller.signal });
    clearTimeout(timeout);
    const latency = Date.now() - start;
    if (response.ok) {
      results.easycron = { status: "ok", latency };
    } else {
      results.easycron = { status: "error", code: response.status };
    }
  } catch (err) {
    results.easycron = { status: "unreachable", error: err.message };
  }

  res.json(results);
});

app.get("/api/events", (req, res) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("Access-Control-Allow-Origin", "*");

  res.write(`data: ${JSON.stringify({ type: "connected" })}\n\n`);

  const clientId = Date.now();
  const client = { id: clientId, res };
  clients.push(client);

  req.on("close", () => {
    clients = clients.filter((c) => c.id !== clientId);
  });
});

app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
