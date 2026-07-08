const API_BASE = "http://localhost:8000";
let authToken = null;

const loginOverlay = document.getElementById("login-overlay");
const app = document.getElementById("app");
const loginButton = document.getElementById("login-button");
const logoutButton = document.getElementById("logout-button");
const loginError = document.getElementById("login-error");
const outputLog = document.getElementById("output-log");
const statusPill = document.getElementById("status-pill");

function log(message, level = "info") {
  const line = document.createElement("div");
  line.className = "log-line" + (level === "ok" ? " ok" : level === "err" ? " err" : "");
  const timestamp = new Date().toLocaleTimeString();
  line.textContent = `[${timestamp}] ${message}`;
  outputLog.appendChild(line);
  outputLog.scrollTop = outputLog.scrollHeight;
}

async function login(username, password) {
  const body = new URLSearchParams();
  body.append("grant_type", "password");
  body.append("username", username);
  body.append("password", password);

  const response = await fetch(`${API_BASE}/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });

  if (!response.ok) {
    throw new Error("Invalid username or password");
  }

  const data = await response.json();
  return data.access_token;
}

async function fetchJSON(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${authToken}` },
  });

  if (!response.ok) {
    throw new Error(`${path} failed with status ${response.status}`);
  }

  return response.json();
}

const PLOTLY_LAYOUT_BASE = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Poppins, sans-serif", color: "#1c1c1c", size: 12 },
  margin: { t: 10, r: 20, b: 40, l: 50 },
};

const PLOTLY_CONFIG = { responsive: true, displayModeBar: false };

async function loadHeadcount() {
  const data = await fetchJSON("/analytics/headcount");
  const x = data.map((d) => d.as_of_date);
  const y = data.map((d) => d.active_headcount);

  Plotly.newPlot(
    "chart-headcount",
    [{
      x, y,
      type: "scatter",
      mode: "lines",
      line: { color: "#4a6fa5", width: 2 },
      fill: "tozeroy",
      fillcolor: "rgba(74,111,165,0.08)",
    }],
    { ...PLOTLY_LAYOUT_BASE, xaxis: { title: "" }, yaxis: { title: "employees" } },
    PLOTLY_CONFIG
  );
  log(`headcount: loaded ${data.length} monthly data points`, "ok");
}

async function loadTurnover() {
  const data = await fetchJSON("/analytics/turnover");
  const x = data.map((d) => d.termination_month);
  const y = data.map((d) => d.terminations);

  Plotly.newPlot(
    "chart-turnover",
    [{
      x, y,
      type: "bar",
      marker: { color: "#c17a67" },
      text: y,
      textposition: "outside",
      textfont: { size: 11, color: "#b3543f" },
      width: 1000 * 60 * 60 * 24 * 20,
    }],
    {
      ...PLOTLY_LAYOUT_BASE,
      yaxis: { title: "terminations", showgrid: true, gridcolor: "#e8e3d8", zeroline: false, dtick: 1 },
      xaxis: { showgrid: false },
      bargap: 0.5,
      height: 300,
    },
    PLOTLY_CONFIG
  );
  log(`turnover: loaded ${data.length} termination months`, "ok");
}

async function loadTenure() {
  const data = await fetchJSON("/analytics/tenure-by-department");
  const top = data.slice(0, 12).reverse();

  const shortLabel = (name) => {
    const parts = name.split("-");
    const cleaned = parts.length > 1 ? parts.slice(1).join("-") : name;
    return cleaned.length > 30 ? cleaned.slice(0, 28) + "…" : cleaned;
  };

  const y = top.map((d) => shortLabel(d.department_name));
  const x = top.map((d) => d.avg_tenure_years);
  const fullNames = top.map((d) => d.department_name);

  Plotly.newPlot(
    "chart-tenure",
    [{
      x, y,
      type: "bar",
      orientation: "h",
      marker: { color: "#8577ab" },
      customdata: fullNames,
      hovertemplate: "%{customdata}<br>%{x} years<extra></extra>",
      text: x.map((v) => v.toFixed(1) + "y"),
      textposition: "outside",
      textfont: { size: 11, color: "#6b5b95" },
    }],
    {
      ...PLOTLY_LAYOUT_BASE,
      margin: { t: 10, r: 50, b: 30, l: 210 },
      xaxis: { title: "", showgrid: true, gridcolor: "#e8e3d8", zeroline: false },
      yaxis: { automargin: true, showgrid: false },
      bargap: 0.35,
      height: 380,
    },
    PLOTLY_CONFIG
  );
  log(`tenure: showing top ${top.length} departments`, "ok");
}

async function loadWorkingHours() {
  const data = await fetchJSON("/analytics/working-hours-summary");
  document.getElementById("stat-daily-hours").textContent = data.overall_avg_hours_per_day;
  document.getElementById("stat-weekly-hours").textContent = data.overall_avg_hours_per_week;
  log("working hours: summary loaded", "ok");
}

async function loadAttendance() {
  const data = await fetchJSON("/analytics/attendance-summary");
  const labels = ["Late Arrival", "Early Departure", "Overtime"];
  const values = [data.late_arrival_rate, data.early_departure_rate, data.overtime_rate];
  const colors = ["#4a6fa5", "#c17a67", "#5c8a6a"];

  Plotly.newPlot(
    "chart-attendance",
    [{
      x: labels,
      y: values,
      type: "bar",
      marker: { color: colors },
      text: values.map((v) => v + "%"),
      textposition: "outside",
      textfont: { size: 13 },
      width: 0.5,
    }],
    {
      ...PLOTLY_LAYOUT_BASE,
      yaxis: { title: "% of assessable punches", showgrid: true, gridcolor: "#e8e3d8", zeroline: false },
      xaxis: { showgrid: false },
      bargap: 0.5,
      height: 320,
    },
    PLOTLY_CONFIG
  );
  log("attendance: late arrival, early departure, overtime rates loaded", "ok");
}

async function loadRollingHours() {
  const data = await fetchJSON("/analytics/rolling-hours-top");
  const x = data.map((d) => d.client_employee_id);

  Plotly.newPlot(
    "chart-rolling",
    [
      {
        x, y: data.map((d) => d.rolling_avg_hours_7day),
        type: "bar", name: "7-day avg",
        marker: { color: "#4a6fa5" },
      },
      {
        x, y: data.map((d) => d.rolling_avg_hours_30day),
        type: "bar", name: "30-day avg",
        marker: { color: "#8577ab" },
      },
    ],
    {
      ...PLOTLY_LAYOUT_BASE,
      barmode: "group",
      yaxis: { title: "hours", showgrid: true, gridcolor: "#e8e3d8", zeroline: false },
      xaxis: { showgrid: false, tickangle: -45 },
      bargap: 0.2,
      bargroupgap: 0.1,
      legend: { orientation: "h", y: -0.25, font: { size: 11 } },
      height: 360,
    },
    PLOTLY_CONFIG
  );
  log(`rolling hours: showing ${data.length} employees`, "ok");
}

async function loadEarlyAttrition() {
  const data = await fetchJSON("/analytics/early-attrition");
  document.getElementById("stat-total-employees").textContent = data.total_employees;
  document.getElementById("stat-attrition-90").textContent = data.left_within_90_days;
  document.getElementById("stat-attrition-6mo").textContent = data.left_within_6_months;
  log("early attrition: summary loaded", "ok");
}

async function loadAllCharts() {
  const loaders = [
    ["headcount", loadHeadcount],
    ["turnover", loadTurnover],
    ["tenure", loadTenure],
    ["working hours", loadWorkingHours],
    ["attendance", loadAttendance],
    ["rolling hours", loadRollingHours],
    ["early attrition", loadEarlyAttrition],
  ];

  for (const [name, fn] of loaders) {
    try {
      await fn();
    } catch (err) {
      log(`${name}: ${err.message}`, "err");
    }
  }
}

loginButton.addEventListener("click", async () => {
  const username = document.getElementById("login-username").value;
  const password = document.getElementById("login-password").value;
  loginError.textContent = "";
  loginButton.textContent = "authorizing...";

  try {
    authToken = await login(username, password);
    loginOverlay.classList.add("hidden");
    app.classList.remove("hidden");
    log(`authenticated as ${username}`, "ok");
    statusPill.textContent = "connected";
    await loadAllCharts();
  } catch (err) {
    loginError.textContent = err.message;
    loginButton.textContent = "authorize";
  }
});

logoutButton.addEventListener("click", () => {
  authToken = null;
  app.classList.add("hidden");
  loginOverlay.classList.remove("hidden");
  outputLog.innerHTML = "";
});