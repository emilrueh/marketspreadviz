const theme = {
    // backgrounds
    pageBg: "#131722",
    panelBg: "#1e222d",
    headerBg: "#0b0e14",

    // borders & grid
    border: "#2a2e39",
    grid: "#1e222d",

    // text
    textPrimary: "#d1d4dc",
    textSecondary: "#787b86",
    textMuted: "#9598a1",

    // accent
    accent: "#2962ff",
    link: "#42a5f5",
    error: "#ef5350",

    // chart lines
    colorBrent: "rgba(38, 255, 136, 0.6)",
    colorWTI: "rgba(201, 38, 255, 0.6)",
    colorSpread: "rgba(66, 179, 245, 0.9)",

    // chart line widths
    tickerLineWidth: 1.5,
    spreadLineWidth: 2.0,

    // spike crosshair
    spikeColor: "#787b86",
    spikeThickness: 1,
    spikeDash: "dot",
};

const state = { tab: "oil" };
const newsCache = {};
let tooltipMouseHandler = null;

function escapeHtml(str) {
    const el = document.createElement("span");
    el.textContent = str;
    return el.innerHTML;
}

function formatDate(dateStr) {
    const [y, m, d] = dateStr.split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

function cleanupTooltipHandler() {
    if (tooltipMouseHandler) {
        document.removeEventListener("mousemove", tooltipMouseHandler);
        tooltipMouseHandler = null;
    }
    hoverTooltip.style.display = "none";
}

const tabBar = document.getElementById("tab-bar");
const sensitivitySlider = document.getElementById("sensitivity");
const sensitivityDisplay = document.getElementById("sensitivity-display");
const periodSelect = document.getElementById("period");
const windowSlider = document.getElementById("window");
const windowDisplay = document.getElementById("window-display");

const windowDefaults = { "1mo": 2, "3mo": 2, "6mo": 5, "1y": 30, "2y": 60, "5y": 120 };
const newsPanel = document.getElementById("news-panel");
const newsPanelTitle = document.getElementById("news-panel-title");
const newsPanelBody = document.getElementById("news-panel-body");
const newsPanelClose = document.getElementById("news-panel-close");
const hoverTooltip = document.getElementById("hover-tooltip");

const darkLayout = {
    paper_bgcolor: theme.pageBg,
    plot_bgcolor: theme.pageBg,
    font: { color: theme.textPrimary },
    xaxis: {
        gridcolor: theme.grid,
        linecolor: theme.border,
        showspikes: true,
        spikemode: "across",
        spikesnap: "cursor",
        spikecolor: theme.spikeColor,
        spikethickness: theme.spikeThickness,
        spikedash: theme.spikeDash,
    },
    yaxis: { gridcolor: theme.grid, linecolor: theme.border },
    dragmode: "pan",
    hovermode: "closest",
    margin: { t: 48, r: 64, b: 48, l: 64 },
};

newsPanelClose.addEventListener("click", () => {
    newsPanel.classList.remove("open");
    document.getElementById("chart").style.width = "100%";
    Plotly.Plots.resize("chart");
});

function closeNewsPanel() {
    newsPanel.classList.remove("open");
    document.getElementById("chart").style.width = "100%";
    Plotly.Plots.resize("chart");
}

function showLoadingSkeleton() {
    newsPanelBody.innerHTML = Array(3).fill(
        '<div class="skeleton-card"><div class="skeleton-line"></div><div class="skeleton-line"></div><div class="skeleton-line"></div></div>'
    ).join("");
}

function renderNewsPanel(data) {
    let html = "";
    if (data.single_exact_reason) {
        html += `<div class="news-synthesis" style="font-weight:600">${escapeHtml(data.single_exact_reason)}</div>`;
    }
    if (data.detailed_summary) {
        html += `<div class="news-detailed_summary" style="font-size:13px;line-height:1.5;color:${theme.textMuted};padding:0 2px 12px;">${escapeHtml(data.detailed_summary)}</div>`;
    }
    for (const a of (data.articles || [])) {
        const hasMetadata = a.title && a.title !== a.url;
        html += `<div class="news-card">`;
        html += `<a href="${escapeHtml(a.url)}" target="_blank" rel="noopener">${escapeHtml(hasMetadata ? a.title : new URL(a.url).hostname)}</a>`;
        if (a.date) html += `<div class="news-date">${escapeHtml(formatDate(a.date))}</div>`;
        if (a.snippet) html += `<div class="news-snippet">${escapeHtml(a.snippet)}</div>`;
        html += `</div>`;
    }
    if (!(data.articles || []).length && !data.single_exact_reason) {
        html = `<div style="color:${theme.textSecondary};font-size:13px;padding:12px;">No news found for this event.</div>`;
    }
    newsPanelBody.innerHTML = html;
}

async function fetchSpikeNews(pair, date, direction) {
    const key = `${pair}_${date}`;
    if (newsCache[key]) return newsCache[key];
    try {
        const res = await fetch(`/api/news/${pair}/${date}?direction=${direction}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        newsCache[key] = data;
        return data;
    } catch (err) {
        return { single_exact_reason: "Failed to load news", detailed_summary: err.message, articles: [] };
    }
}

tabBar.querySelectorAll("button").forEach(btn => {
    btn.addEventListener("click", () => {
        tabBar.querySelectorAll("button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        state.tab = btn.dataset.tab;
        closeNewsPanel();
        fetchAndRender();
    });
});

sensitivitySlider.addEventListener("input", () => {
    sensitivityDisplay.textContent = sensitivitySlider.value;
    closeNewsPanel();
    fetchAndRender();
});
periodSelect.addEventListener("change", () => {
    const defaultWindow = windowDefaults[periodSelect.value] || 30;
    windowSlider.max = Math.max(defaultWindow * 2, 10);
    windowSlider.value = defaultWindow;
    windowDisplay.textContent = defaultWindow;
    closeNewsPanel();
    fetchAndRender();
});
windowSlider.addEventListener("input", () => {
    windowDisplay.textContent = windowSlider.value;
    closeNewsPanel();
    fetchAndRender();
});

async function fetchAndRender() {
    cleanupTooltipHandler();
    const sensitivity = sensitivitySlider.value;
    const period = periodSelect.value;
    const url = `/api/spread/${state.tab}?sensitivity=${sensitivity}&window=${windowSlider.value}&period=${period}`;

    let res, json;
    try {
        res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        json = await res.json();
    } catch (err) {
        document.getElementById("chart").innerHTML =
            `<div style="color:${theme.error};padding:48px;text-align:center;">Failed to load data: ${escapeHtml(err.message)}</div>`;
        return;
    }

    const dates = json.data.map(d => d.date);
    const growthA = json.data.map(d => d.growth_a);
    const growthB = json.data.map(d => d.growth_b);
    const growthSpread = json.data.map(d => d.growth_spread);

    const traceA = {
        x: dates, y: growthA,
        type: "scatter", mode: "lines",
        line: { color: theme.colorBrent, width: theme.tickerLineWidth },
        name: json.name_a,
    };
    const traceB = {
        x: dates, y: growthB,
        type: "scatter", mode: "lines",
        line: { color: theme.colorWTI, width: theme.tickerLineWidth },
        name: json.name_b,
    };
    const traceSpread = {
        x: dates, y: growthSpread,
        type: "scatter", mode: "lines",
        line: { color: theme.colorSpread, width: theme.spreadLineWidth },
        name: "Relative",
        yaxis: "y2",
    };

    const spreadByDate = Object.fromEntries(json.data.map(d => [d.date, d.growth_spread]));
    const spreadRange = Math.max(...growthSpread) - Math.min(...growthSpread);
    const arrowOffset = spreadRange * 0.04;
    const upSpikes = json.spikes.filter(s => s.direction === "up");
    const downSpikes = json.spikes.filter(s => s.direction === "down");

    const traceUp = {
        x: upSpikes.map(s => s.date),
        y: upSpikes.map(s => spreadByDate[s.date] - arrowOffset),
        customdata: upSpikes.map(s => ({ date: s.date, value: s.value, direction: "up" })),
        type: "scatter", mode: "markers",
        marker: { symbol: "triangle-up", size: 13, color: theme.colorBrent },
        showlegend: false,
        hoverinfo: "none",
        yaxis: "y2",
        meta: "arrow_up",
    };
    const traceDown = {
        x: downSpikes.map(s => s.date),
        y: downSpikes.map(s => spreadByDate[s.date] + arrowOffset),
        customdata: downSpikes.map(s => ({ date: s.date, value: s.value, direction: "down" })),
        type: "scatter", mode: "markers",
        marker: { symbol: "triangle-down", size: 13, color: theme.colorWTI },
        showlegend: false,
        hoverinfo: "none",
        yaxis: "y2",
        meta: "arrow_down",
    };

    const yAB = [...growthA, ...growthB];
    const yABMin = Math.min(...yAB);
    const yABMax = Math.max(...yAB);
    const yABPad = (yABMax - yABMin) * 0.1;

    const ySpread = growthSpread;
    const ySpreadMin = Math.min(...ySpread);
    const ySpreadMax = Math.max(...ySpread);
    const ySpreadPad = (ySpreadMax - ySpreadMin) * 0.1;

    const layout = {
        ...darkLayout,
        title: { text: json.label, font: { size: 16, color: theme.textPrimary } },
        yaxis: {
            ...darkLayout.yaxis,
            title: "Price Change %",
            range: [yABMin - yABPad * 2, yABMax + yABPad * 2],
        },
        yaxis2: {
            title: json.label.replace(" / ", " vs ") + " %",
            side: "right",
            overlaying: "y",
            gridcolor: "transparent",
            linecolor: theme.border,
            font: { color: theme.textPrimary },
            range: [ySpreadMin - ySpreadPad * 2, ySpreadMax + ySpreadPad * 2],
        },
        showlegend: true,
        legend: { x: 0, y: 1.12, orientation: "h", font: { size: 12, color: theme.textPrimary } },
    };

    Plotly.newPlot("chart", [traceA, traceB, traceSpread, traceUp, traceDown], layout, { responsive: true });

    const chartEl = document.getElementById("chart");

    chartEl.on("plotly_click", async (eventData) => {
        const point = eventData.points[0];
        const meta = point.data.meta;
        if (meta !== "arrow_up" && meta !== "arrow_down") return;
        const direction = meta === "arrow_up" ? "up" : "down";
        const date = point.x;

        newsPanelTitle.textContent = `${json.label} — ${formatDate(date)}`;
        newsPanel.classList.add("open");
        document.getElementById("chart").style.width = "calc(100% - 380px)";
        Plotly.Plots.resize("chart");
        showLoadingSkeleton();

        const data = await fetchSpikeNews(state.tab, date, direction);
        renderNewsPanel(data);
    });

    chartEl.on("plotly_hover", (eventData) => {
        const point = eventData.points[0];
        const meta = point.data.meta;
        if (meta !== "arrow_up" && meta !== "arrow_down") return;

        const spike = point.customdata;
        const key = `${state.tab}_${spike.date}`;
        const cached = newsCache[key];
        const arrow = spike.direction === "up"
            ? `▲ ${json.name_a} leading`
            : `▼ ${json.name_b} leading`;

        let html = `<div style="font-weight:600;margin-bottom:4px">${escapeHtml(formatDate(spike.date))}</div>`;
        html += `<div style="color:${theme.textSecondary};font-size:11px">${spike.value.toFixed(2)}% &middot; ${arrow}</div>`;
        if (cached?.single_exact_reason) {
            html += `<div style="margin-top:6px;border-top:1px solid ${theme.border};padding-top:6px">${escapeHtml(cached.single_exact_reason)}</div>`;
        } else {
            html += `<div style="margin-top:6px;color:${theme.textSecondary};font-style:italic">Click for news</div>`;
        }
        hoverTooltip.innerHTML = html;

        if (tooltipMouseHandler) {
            document.removeEventListener("mousemove", tooltipMouseHandler);
        }
        tooltipMouseHandler = (e) => {
            hoverTooltip.style.left = (e.clientX + 16) + "px";
            hoverTooltip.style.top = (e.clientY - 10) + "px";
        };
        document.addEventListener("mousemove", tooltipMouseHandler);
        hoverTooltip.style.display = "block";
    });

    chartEl.on("plotly_unhover", () => {
        cleanupTooltipHandler();
    });
}

// sync window slider to initial period default
(function initWindowSlider() {
    const defaultWindow = windowDefaults[periodSelect.value] || 30;
    windowSlider.max = Math.max(defaultWindow * 2, 10);
    windowSlider.value = defaultWindow;
    windowDisplay.textContent = defaultWindow;
})();

fetchAndRender();
