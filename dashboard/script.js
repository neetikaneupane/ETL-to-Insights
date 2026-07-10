const API_BASE = new URLSearchParams(window.location.search).get("api") || "http://localhost:8000";
let authToken = null;

const filters = {
  startDate: "",
  endDate: "",
  department: "",
  employeeId: "",
};

const loginOverlay = document.getElementById("login-overlay");
const app = document.getElementById("app");
const loginButton = document.getElementById("login-button");
const logoutButton = document.getElementById("logout-button");
const loginError = document.getElementById("login-error");
const outputLog = document.getElementById("output-log");
const statusPill = document.getElementById("status-pill");

const filterStart = document.getElementById("filter-start");
const filterEnd = document.getElementById("filter-end");
const filterDept = document.getElementById("filter-dept");
const filterEmployee = document.getElementById("filter-employee");
const employeeSuggestions = document.getElementById("employee-suggestions");
const filterApply = document.getElementById("filter-apply");
const filterReset = document.getElementById("filter-reset");

let employeeSearchTimeout = null;

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

function buildQuery(base, params) {
  const qs = Object.entries(params)
    .filter(([, v]) => v !== "" && v !== null && v !== undefined)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join("&");
  return qs ? `${base}?${qs}` : base;
}

function currentFilterParams() {
  return {
    start_date: filters.startDate || undefined,
    end_date: filters.endDate || undefined,
    department_name: filters.department || undefined,
    employee_id: filters.employeeId || undefined,
  };
}

const PLOTLY_LAYOUT_BASE = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Poppins, sans-serif", color: "#1c1c1c", size: 12 },
  margin: { t: 10, r: 20, b: 40, l: 50 },
};

const PLOTLY_CONFIG = { responsive: true, displayModeBar: false };

async function loadHeadcount() {
  const params = currentFilterParams();
  const data = await fetchJSON(buildQuery("/analytics/headcount", params));
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
  log(`headcount: loaded ${data.length} data points`, "ok");
}

async function loadTurnover() {
  const params = currentFilterParams();
  const data = await fetchJSON(buildQuery("/analytics/turnover", params));

  const formatMonth = (d) => d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
  const parsedDates = data.map((d) => new Date(d.termination_month));
  const countByMonth = new Map(data.map((d) => [formatMonth(new Date(d.termination_month)), d.terminations]));

  const firstMonth = parsedDates.length ? new Date(Math.min(...parsedDates)) : new Date();
  const lastMonth = parsedDates.length ? new Date(Math.max(...parsedDates)) : new Date();
  const allMonths = [];
  const cursor = new Date(firstMonth.getFullYear(), firstMonth.getMonth(), 1);
  const end = new Date(lastMonth.getFullYear(), lastMonth.getMonth(), 1);

  while (cursor <= end) {
    allMonths.push(formatMonth(cursor));
    cursor.setMonth(cursor.getMonth() + 1);
  }

  const x = allMonths;
  const y = allMonths.map((m) => countByMonth.get(m) || 0);

  Plotly.newPlot(
    "chart-turnover",
    [{
      x, y,
      type: "bar",
      marker: { color: "#c17a67" },
      text: y.map((v) => (v > 0 ? v : "")),
      textposition: "outside",
      textfont: { family: "Poppins, sans-serif", size: 12, color: "#1c1c1c" },
    }],
    {
      ...PLOTLY_LAYOUT_BASE,
      margin: { t: 40, r: 20, b: 40, l: 50 },
      xaxis: { type: "category", showgrid: false },
      yaxis: { title: "terminations", showgrid: true, gridcolor: "#e8e3d8", zeroline: false, dtick: 1, range: [0, 2.5] },
      bargap: 0.5,
      height: 300,
    },
    PLOTLY_CONFIG
  );
  log(`turnover: ${allMonths[0]} to ${allMonths[allMonths.length - 1]}`, "ok");
}

async function loadTenure() {
  const params = currentFilterParams();
  const data = await fetchJSON(buildQuery("/analytics/tenure-by-department", params));
  const top = data.slice(0, 12).reverse();

  const shortLabel = (name) => {
    const parts = name.split("-");
    const cleaned = parts.length > 1 ? parts.slice(1).join("-") : name;
    return cleaned.length > 30 ? cleaned.slice(0, 28) + "\u2026" : cleaned;
  };

  const y = top.map((d) => shortLabel(d.department_name));
  const x = top.map((d) => d.avg_tenure_years);
  const fullNames = top.map((d) => d.department_name);

  const chart = document.getElementById("chart-tenure");
  Plotly.newPlot(
    chart,
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
  chart.on("plotly_click", function(evt) {
    if (evt.points && evt.points.length > 0) {
      const dept = evt.points[0].customdata;
      filters.department = dept;
      filterDept.value = dept;
      log(`drill-down: filtering to department "${dept}"`, "ok");
      loadAllCharts();
    }
  });
  log(`tenure: showing top ${top.length} departments`, "ok");
}

async function loadWorkingHours() {
  const params = currentFilterParams();
  const data = await fetchJSON(buildQuery("/analytics/working-hours-summary", params));
  document.getElementById("stat-daily-hours").textContent = data.overall_avg_hours_per_day;
  document.getElementById("stat-weekly-hours").textContent = data.overall_avg_hours_per_week;
  log("working hours: summary loaded", "ok");
}

async function loadAttendance() {
  const params = currentFilterParams();
  const data = await fetchJSON(buildQuery("/analytics/attendance-summary", params));
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
      textfont: { family: "Poppins, sans-serif", size: 13, color: "#1c1c1c" },
    }],
    {
      ...PLOTLY_LAYOUT_BASE,
      margin: { t: 40, r: 20, b: 40, l: 50 },
      yaxis: { title: "% of assessable punches", showgrid: true, gridcolor: "#e8e3d8", zeroline: false, range: [0, 38] },
      xaxis: { type: "category", showgrid: false },
      bargap: 0.5,
      height: 320,
    },
    PLOTLY_CONFIG
  );
  log("attendance: rates loaded", "ok");
}

async function loadRollingHours() {
  const params = currentFilterParams();
  const data = await fetchJSON(buildQuery("/analytics/rolling-hours-top", { ...params, limit: filters.employeeId ? 5 : 15 }));
  const x = data.map((d) => d.client_employee_id);

  const chart = document.getElementById("chart-rolling");
  Plotly.newPlot(
    chart,
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
      xaxis: { type: "category", showgrid: false, tickangle: -45 },
      bargap: 0.2,
      bargroupgap: 0.15,
      legend: { orientation: "h", y: -0.3, font: { size: 11 } },
      height: 380,
    },
    PLOTLY_CONFIG
  );
  chart.on("plotly_click", function(evt) {
    if (evt.points && evt.points.length > 0) {
      const empId = evt.points[0].x;
      filters.employeeId = empId;
      filterEmployee.value = empId;
      log(`drill-down: filtering to employee "${empId}"`, "ok");
      loadAllCharts();
    }
  });
  log(`rolling hours: ${data.length} employees`, "ok");
}

async function loadEarlyAttrition() {
  const params = currentFilterParams();
  const data = await fetchJSON(buildQuery("/analytics/early-attrition", params));
  document.getElementById("stat-total-employees").textContent = data.total_employees;
  document.getElementById("stat-attrition-90").textContent = data.left_within_90_days;
  document.getElementById("stat-attrition-6mo").textContent = data.left_within_6_months;
  log("early attrition: summary loaded", "ok");
}

async function loadDepartments() {
  try {
    const depts = await fetchJSON("/analytics/departments");
    filterDept.innerHTML = '<option value="">All departments</option>';
    depts.forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      filterDept.appendChild(opt);
    });
    log(`departments: ${depts.length} loaded`, "ok");
  } catch (err) {
    log(`departments: ${err.message}`, "err");
  }
}

function setupEmployeeSearch() {
  filterEmployee.addEventListener("input", function() {
    clearTimeout(employeeSearchTimeout);
    employeeSuggestions.classList.add("hidden");

    const q = this.value.trim();
    if (q.length < 1) return;

    employeeSearchTimeout = setTimeout(async () => {
      try {
        const results = await fetchJSON(`/analytics/employees?q=${encodeURIComponent(q)}&limit=10`);
        employeeSuggestions.innerHTML = "";
        if (results.length === 0) {
          employeeSuggestions.classList.add("hidden");
          return;
        }
        results.forEach((emp) => {
          const div = document.createElement("div");
          div.className = "suggestion-item";
          div.innerHTML = `${emp.client_employee_id} <span class="sug-meta">${emp.full_name} &mdash; ${emp.department_name || ""}</span>`;
          div.addEventListener("click", function() {
            filters.employeeId = emp.client_employee_id;
            filterEmployee.value = `${emp.client_employee_id} (${emp.full_name})`;
            employeeSuggestions.classList.add("hidden");
            log(`employee selected: ${emp.client_employee_id}`, "ok");
            loadAllCharts();
          });
          employeeSuggestions.appendChild(div);
        });
        employeeSuggestions.classList.remove("hidden");
      } catch (err) {
        log(`employee search: ${err.message}`, "err");
      }
    }, 200);
  });

  filterEmployee.addEventListener("blur", function() {
    setTimeout(() => employeeSuggestions.classList.add("hidden"), 200);
  });

  filterEmployee.addEventListener("focus", function() {
    if (employeeSuggestions.children.length > 0) {
      employeeSuggestions.classList.remove("hidden");
    }
  });
}

function setupFilterButtons() {
  filterApply.addEventListener("click", function() {
    filters.startDate = filterStart.value;
    filters.endDate = filterEnd.value;
    filters.department = filterDept.value;
    const empVal = filterEmployee.value.trim();
    if (empVal && !empVal.includes("(") && empVal !== filters.employeeId) {
      filters.employeeId = empVal;
    } else if (!empVal) {
      filters.employeeId = "";
    }
    log("filters applied", "ok");
    loadAllCharts();
  });

  filterReset.addEventListener("click", function() {
    filterStart.value = "";
    filterEnd.value = "";
    filterDept.value = "";
    filterEmployee.value = "";
    filters.startDate = "";
    filters.endDate = "";
    filters.department = "";
    filters.employeeId = "";
    log("filters reset", "ok");
    loadAllCharts();
  });
}

async function loadAllCharts() {
  document.getElementById("output-state").textContent = "loading...";
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
  document.getElementById("output-state").textContent = "ready";
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
    await loadDepartments();
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

setupEmployeeSearch();
setupFilterButtons();
