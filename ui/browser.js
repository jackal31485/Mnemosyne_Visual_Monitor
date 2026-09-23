/*
 * Mnemosyne Browser — Phase 7 operational Browser.
 *
 * The Browser is a control and review surface. It never writes directly to
 * source Mnemosyne databases and never stores raw memory content in the
 * collective database.
 */
const API_BASE = "";

const state = {
    profiles: [],
    selectedProfile: null,
    graph: {nodes: [], edges: {}},
    entityGraph: {nodes: [], edges: []},
    selectedNode: null,
    selectedEntityNode: null,
    selectedEntityEdge: null,
    entityGraphLoaded: false,
    entityGraphLoading: false,
    entityGraphViewInitialized: false,
    viewMode: "tiles",
    informationView: "overview",
    edgeLimit: 5,
    zoom: 1, panX: 0, panY: 0,
    dragging: false,
    dragStartX: 0, dragStartY: 0, panStartX: 0, panStartY: 0,
    agents: [],
    scanning: false,
    agentMap: new Map(),
    localAgentId: null,

    globalFilter: {
        search: "",
        dateFrom: "",
        dateTo: "",
        profileScope: "all",
    },
    globalEvents: null,
    hybridResults: [],
    hybridSearchLoading: false,
};

function $(id) { return document.getElementById(id); }

function setStatus(message, error = false) {
    const element = $("status-message");
    if (element) {
        element.textContent = message;
        element.style.color = error ? "var(--danger)" : "";
    }
}

function setSelectionStatus(message = "") {
    const element = $("status-selection");
    if (element) element.textContent = message;
}

async function fetchJSON(path, options = {}) {
    const response = await fetch(
        path.startsWith("http") ? path : `${API_BASE}${path}`,
        options
    );
    if (!response.ok) {
        let detail = "";
        try {
            const body = await response.json();
            detail = body.detail ? `: ${body.detail}` : "";
        } catch (_) {}
        throw new Error(`${response.status} ${response.statusText}${detail}`);
    }
    return response.json();
}

async function postJSON(path) {
    return fetchJSON(path, {method: "POST", headers: {"Accept": "application/json"}});
}

function normalizeProfiles(data) {
    if (!Array.isArray(data)) throw new Error("Invalid profile response.");

    return data.map((entry) => {
        const profile = Array.isArray(entry)
            ? {
                id: entry[0],
                name: entry[1],
                memory_count: entry[2],
            }
            : {
                id: entry.id,
                name: entry.name,
                memory_count: entry.memory_count,
            };

        const rawName = String(profile.name || profile.id || "unknown");
        const displayName = profileLabel(rawName);

        return {
            ...profile,
            name: displayName.charAt(0).toUpperCase() + displayName.slice(1),
        };
    });
}

async function fetchProfiles() {
    return normalizeProfiles(await fetchJSON("/api/collective/profiles"));
}

async function fetchHermesRuntime() {
    return fetchJSON("/api/runtime/hermes");
}

function renderHermesRuntime(runtime) {
    const value = (value) => {
        if (value === null || value === undefined || value === "") {
            return "—";
        }
        return String(value);
    };

    const profiles = Array.isArray(runtime?.profile_names)
        ? runtime.profile_names
        : [];

    $("hermes-runtime-version").textContent = value(runtime?.version);
    $("hermes-runtime-current-profile").textContent =
        value(runtime?.current_profile);
    $("hermes-runtime-profiles").textContent =
        profiles.length ? profiles.join(", ") : "—";
    $("hermes-runtime-config").textContent = value(runtime?.config_path);
    $("hermes-runtime-installation").textContent =
        value(runtime?.installation_path);
    $("hermes-runtime-executable").textContent =
        value(runtime?.executable_path);
    $("hermes-runtime-venv").textContent = value(runtime?.venv_path);

    const status = $("hermes-runtime-status");
    status.textContent = "Connected";
    status.classList.remove("error");
}

async function loadHermesRuntime() {
    const status = $("hermes-runtime-status");

    try {
        const runtime = await fetchHermesRuntime();
        renderHermesRuntime(runtime);
    } catch (error) {
        status.textContent = `Unavailable — ${error.message}`;
        status.classList.add("error");
    }
}

async function fetchGraph(profile = null) {
    const params = new URLSearchParams();
    if (profile) params.set("source_profile", profile);
    if (state.edgeLimit !== null) params.set("edge_limit", String(state.edgeLimit));
    const query = params.toString();
    return fetchJSON(query ? `/api/graph?${query}` : "/api/graph");
}

async function fetchEntityGraph() {
    return fetchJSON("/api/entity-graph");
}

async function fetchDiagnostics() {
    const [profiles, graph] = await Promise.all([
        fetchJSON("/profiles/diag"),
        fetchJSON("/graph/diag"),
    ]);
    return {profiles, graph};
}

async function fetchAgents() {
    return fetchJSON("/api/discovery");
}

async function fetchHybridSearch() {
    const query = String(state.globalFilter.search || "").trim();

    if (!query) {
        throw new Error("Enter a search query before running Hybrid Search.");
    }

    const params = new URLSearchParams();
    params.set("q", query);
    params.set("top_k", "10");
    params.set("candidate_limit", "20");

    const profile = String(state.globalFilter.profileScope || "all").trim();
    if (profile && profile !== "all") {
        params.set("profile", profile);
    }

    const dateFrom = state.globalFilter.dateFrom;
    const dateTo = state.globalFilter.dateTo;
    if (dateFrom || dateTo) {
        if (!dateFrom || !dateTo) {
            throw new Error("Hybrid Search requires both From and To dates.");
        }
        params.set("date_from", dateFrom);
        params.set("date_to", dateTo);
    }

    params.set("rerank", "true");

    return fetchJSON(`/api/search/hybrid?${params.toString()}`);
}

function countEdges(edges) {
    if (!edges || typeof edges !== "object") return 0;

    return Object.values(edges).reduce((total, connections) => {
        if (Array.isArray(connections)) {
            return total + connections.length;
        }

        if (connections && typeof connections === "object") {
            return total + Object.keys(connections).length;
        }

        return total;
    }, 0);
}

function profileLabel(sourceProfile) {
    const value = String(sourceProfile || "unknown");
    const colon = value.indexOf(":");
    return colon >= 0 ? value.slice(colon + 1) : value;
}

const DEFAULT_PROFILE_COLORS = [
    "#6ea8fe",
    "#7bd88f",
    "#f6c85f",
    "#f08a8a",
    "#b58cff",
    "#5fd3d3",
    "#ff9f68",
    "#d0d0d0",
];

const COLOR_STORAGE_KEY = "mnemosyne-profile-colours";

function loadProfileColours() {
    try {
        const stored = JSON.parse(localStorage.getItem(COLOR_STORAGE_KEY) || "{}");
        if (!stored || typeof stored !== "object") return {};

        return Object.fromEntries(
            Object.entries(stored).filter(
                ([, value]) => typeof value === "string" &&
                    /^#[0-9a-fA-F]{6}$/.test(value)
            )
        );
    } catch (_) {
        return {};
    }
}

const profileColours = loadProfileColours();

function defaultColourForProfile(profile) {
    const value = profileLabel(profile);
    let hash = 0;

    for (let i = 0; i < value.length; i += 1) {
        hash = ((hash << 5) - hash) + value.charCodeAt(i);
        hash |= 0;
    }

    return DEFAULT_PROFILE_COLORS[
        Math.abs(hash) % DEFAULT_PROFILE_COLORS.length
    ];
}

function colorForProfile(profile) {
    const label = profileLabel(profile);
    return profileColours[label] || defaultColourForProfile(label);
}

function saveProfileColours() {
    localStorage.setItem(
        COLOR_STORAGE_KEY,
        JSON.stringify(profileColours),
    );
}

function renderGlobalProfileFilter() {
    const select = $("global-profile-scope");

    if (!select) {
        return;
    }

    const currentValue = state.globalFilter.profileScope || "all";

    select.innerHTML = "";

    const allOption = document.createElement("option");
    allOption.value = "all";
    allOption.textContent = "All Profiles";
    select.appendChild(allOption);

    const profiles = Array.isArray(state.profiles)
        ? state.profiles
        : [];

    for (const profile of profiles) {
        const id = String(profile?.id || "").trim();

        if (!id) {
            continue;
        }

        const option = document.createElement("option");
        option.value = profileLabel(id);
        option.textContent =
            profile?.name || profileLabel(id);

        select.appendChild(option);
    }

    const validValues = new Set(
        Array.from(select.options).map(option => option.value)
    );

    state.globalFilter.profileScope =
        validValues.has(currentValue)
            ? currentValue
            : "all";

    select.value = state.globalFilter.profileScope;
}


function renderProfiles(profiles) {
    const list = $("profile-list");
    list.innerHTML = "";

    renderGlobalProfileFilter();

    const addProfile = (profile, all = false) => {
        const item = document.createElement("li");
        const button = document.createElement("button");
        button.type = "button";
        button.className = "profile-button";
        if ((all && state.selectedProfile === null) ||
            (!all && state.selectedProfile === profile.id)) {
            button.classList.add("active");
        }

        const main = document.createElement("span");
        main.className = "profile-main";
        const dot = document.createElement("span");
        dot.className = "profile-dot";
        dot.style.background = all ? "var(--accent)" : colorForProfile(profile.id);
        const name = document.createElement("span");
        name.className = "profile-name";
        name.textContent = all ? "All profiles" : profile.name;
        main.append(dot, name);

        const count = document.createElement("span");
        count.className = "profile-count";
        count.textContent = String(all
            ? profiles.reduce((sum,p) => sum + Number(p.memory_count || 0), 0)
            : profile.memory_count);

        button.append(main, count);
        button.addEventListener("click", () => selectProfile(all ? null : profile.id));
        item.appendChild(button);
        list.appendChild(item);
    };

    addProfile(null, true);
    for (const profile of profiles) addProfile(profile);
    renderLegend(profiles);
}

function renderLegend(profiles) {
    const legend = $("profile-legend");
    if (!legend) return;
    legend.innerHTML = "";
    for (const profile of profiles) {
        const item = document.createElement("div");
        item.className = "legend-item";
        const dot = document.createElement("span");
        dot.className = "profile-dot";
        dot.style.background = colorForProfile(profile.id);
        item.append(dot, document.createTextNode(profile.name));
        legend.appendChild(item);
    }
}

function flattenEdges(edges) {
    const result = [];
    if (!edges || typeof edges !== "object") return result;
    for (const [sourceKey, outgoing] of Object.entries(edges)) {
        if (!Array.isArray(outgoing)) continue;
        for (const edge of outgoing) {
            if (!edge || typeof edge !== "object" || !edge.target_id) continue;
            result.push({
                source_id: edge.source_id || sourceKey,
                target_id: edge.target_id,
                similarity_score: typeof edge.similarity_score === "number"
                    ? edge.similarity_score : null,
                relationship_type: edge.relationship_type || "related",
            });
        }
    }
    return result;
}

function renderGraph3D(graph) {
    const container = $("graph-view");

    if (window.Mnemosyne3D?.render) {
        window.Mnemosyne3D.render(
            container,
            graph,
            state,
            (node, selectedGraph) => selectNode(node, selectedGraph),
        );
        return;
    }

    container.innerHTML =
        '<div class="loading-state">Loading 3D constellation…</div>';

    if (!window.__mnemosyne3d_waiting) {
        window.__mnemosyne3d_waiting = true;

        window.addEventListener(
            "mnemosyne-3d-ready",
            () => {
                window.__mnemosyne3d_waiting = false;
                renderGraph3D(state.graph);
            },
            { once: true },
        );
    }
}



function calculateLayout(nodes, width, height) {
    const centerX = width / 2, centerY = height / 2;
    const grouped = new Map();
    for (const node of nodes) {
        const profile = profileLabel(node.source_profile);
        if (!grouped.has(profile)) grouped.set(profile, []);
        grouped.get(profile).push(node);
    }
    const profiles = Array.from(grouped.keys()).sort();
    const positions = new Map();
    if (nodes.length === 1) {
        positions.set(nodes[0].graph_id, {x:centerX,y:centerY});
        return positions;
    }
    const baseRadius = Math.max(90, Math.min(width,height) * .28);
    profiles.forEach((profile, pi) => {
        const members = grouped.get(profile);
        const pa = pi / Math.max(profiles.length,1) * Math.PI * 2;
        const gx = centerX + Math.cos(pa) * baseRadius * .35;
        const gy = centerY + Math.sin(pa) * baseRadius * .35;
        const gr = Math.max(50, Math.min(width,height) *
            (.08 + Math.min(members.length,150) / 1500));
        members.forEach((node,i) => {
            const angle = i / Math.max(members.length,1) * Math.PI * 2 + pi * .37;
            const ring = gr * (1 + Math.floor(i/80) * .35);
            positions.set(node.graph_id, {
                x: gx + Math.cos(angle)*ring,
                y: gy + Math.sin(angle)*ring,
            });
        });
    });
    return positions;
}

function createSVGElement(name, attributes = {}) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [key, value] of Object.entries(attributes)) {
        element.setAttribute(key, value);
    }
    return element;
}

function bindGraphInteraction(container) {
    container.onwheel = e => {
        e.preventDefault();
        state.zoom = Math.max(.2,Math.min(8,state.zoom*(e.deltaY < 0 ? 1.15 : .87)));
        applyTransform();
    };
    container.onmousedown = e => {
        if(e.target.closest(".graph-node, .entity-graph-node, .entity-graph-edge")) return;
        state.dragging=true; state.dragStartX=e.clientX; state.dragStartY=e.clientY;
        state.panStartX=state.panX; state.panStartY=state.panY;
        container.classList.add("dragging");
    };
    window.onmousemove = e => {
        if(!state.dragging) return;
        state.panX=state.panStartX+(e.clientX-state.dragStartX);
        state.panY=state.panStartY+(e.clientY-state.dragStartY);
        applyTransform();
    };
    window.onmouseup = () => {
        state.dragging=false; container.classList.remove("dragging");
    };
}

function renderGraph2D(graph) {

    const container = $("graph-view");
    container.innerHTML = "";
    if (!graph?.nodes?.length) {
        container.innerHTML = '<div class="loading-state">No graph data available.</div>';
        renderStatistics();
        return;
    }

    const rect = container.getBoundingClientRect();
    const width = Math.max(rect.width,800), height = Math.max(rect.height,600);
    const svg = createSVGElement("svg", {
        class:"graph-svg", viewBox:`0 0 ${width} ${height}`,
        preserveAspectRatio:"xMidYMid meet",
    });
    const viewport = createSVGElement("g",{class:"graph-viewport"});
    svg.appendChild(viewport);
    const positions = calculateLayout(graph.nodes,width,height);

    fit2DGraphToViewport(
        positions,
        width,
        height,
    );
    const edges = flattenEdges(graph.edges);

    const edgeGroup = createSVGElement("g",{class:"graph-edges"});
    for (const edge of edges) {
        const source = positions.get(edge.source_id), target = positions.get(edge.target_id);
        if (!source || !target) continue;
        const score = edge.similarity_score ?? 0;
        edgeGroup.appendChild(createSVGElement("line",{
            class:score >= .85 ? "graph-edge strong" : "graph-edge",
            x1:source.x,y1:source.y,x2:target.x,y2:target.y,
            "stroke-width":Math.max(.5,score*2),
            "data-source":edge.source_id,"data-target":edge.target_id,
        }));
    }
    viewport.appendChild(edgeGroup);

    const nodeGroup = createSVGElement("g",{class:"graph-nodes"});
    for (const node of graph.nodes) {
        const pos = positions.get(node.graph_id);
        if (!pos) continue;
        const selected = state.selectedNode?.graph_id === node.graph_id;
        const circle = createSVGElement("circle",{
            class:`graph-node${selected ? " selected" : ""}`,
            cx:pos.x,cy:pos.y,r:selected ? 7 : 5,tabindex:"0",
            "aria-label":`${profileLabel(node.source_profile)}: ${node.origin_memory_id}`,
        });
        circle.style.fill = colorForProfile(profileLabel(node.source_profile));
        circle.dataset.graphId = node.graph_id;
        circle.addEventListener("click",e => {e.stopPropagation();selectNode(node,graph);});
        circle.addEventListener("keydown",e => {
            if(e.key==="Enter" || e.key===" "){e.preventDefault();selectNode(node,graph);}
        });
        nodeGroup.appendChild(circle);
    }
    viewport.appendChild(nodeGroup);
    container.appendChild(svg);
    bindGraphInteraction(container);
    applyTransform();
}

/* Tile View helpers */

const INFORMATION_VIEW_TYPES = [
    {
        id: "2d",
        label: "2D Constellation",
        scope: "all",
    },
    {
        id: "3d",
        label: "3D Constellation",
        scope: "all",
    },
    {
        id: "table",
        label: "Data Table",
        scope: "all",
    },
    {
        id: "profile-views",
        label: "Profile Views",
        scope: "all",
    },
    {
        id: "activity",
        label: "Activity",
        scope: "all",
    },
    {
        id: "status",
        label: "Collective Status",
        scope: "all",
    },
    {
        id: "validation",
        label: "Validation",
        scope: "all",
    },
];

const PROFILE_TILE_VIEW_TYPES = INFORMATION_VIEW_TYPES.slice();

const tileEventCache = new Map();

async function fetchTileEvents(profileId) {
    if (!profileId) {
        return [];
    }

    if (tileEventCache.has(profileId)) {
        return tileEventCache.get(profileId);
    }

    const response = await fetch(
        `/api/events?profile=${encodeURIComponent(profileId)}`
    );

    if (!response.ok) {
        throw new Error(`Event request failed: ${response.status}`);
    }

    const data = await response.json();
    const events = Array.isArray(data.events) ? data.events : [];

    tileEventCache.set(profileId, events);
    return events;
}

async function fetchTileGraph(profileId) {
    if (!profileId) {
        return { nodes: [], edges: {} };
    }

    const params = new URLSearchParams();
    params.set("source_profile", profileId);

    if (state.edgeLimit !== null) {
        params.set("edge_limit", String(state.edgeLimit));
    }

    return fetchJSON(`/api/graph?${params.toString()}`);
}

function flattenTileEdges(edges) {
    if (Array.isArray(edges)) {
        return edges;
    }

    if (!edges || typeof edges !== "object") {
        return [];
    }

    const result = [];

    for (const [sourceId, values] of Object.entries(edges)) {
        if (!Array.isArray(values)) {
            continue;
        }

        for (const edge of values) {
            if (!edge || typeof edge !== "object") {
                continue;
            }

            result.push({
                ...edge,
                source_id: edge.source_id ?? sourceId,
            });
        }
    }

    return result;
}

function sortProfilesByMemoryCount(a, b) {
    return Number(b.memory_count || 0) - Number(a.memory_count || 0);
}

function getDefaultTileProfiles(profiles, count) {
    return [...profiles]
        .sort(sortProfilesByMemoryCount)
        .slice(0, count)
        .map(profile => ({
            profileId: profile.id,
            viewType: "profile-views",
        }));
}

function loadTileConfiguration(profiles) {
    const requestedCount =
        Number(localStorage.getItem("mnemosyne-tile-view-count")) || 4;

    const count = Math.max(
        1,
        Math.min(requestedCount, Math.max(profiles.length, 1)),
    );

    let saved = null;

    try {
        saved = JSON.parse(
            localStorage.getItem("mnemosyne-tile-configuration") || "null"
        );
    } catch (_) {
        saved = null;
    }

    if (!Array.isArray(saved) || saved.length === 0) {
        return getDefaultTileProfiles(profiles, count);
    }

    const validIds = new Set(profiles.map(profile => profile.id));

    const defaults = getDefaultTileProfiles(profiles, count);

    const configuration = saved
        .slice(0, count)
        .map((tile, index) => ({
            profileId: validIds.has(tile?.profileId)
                ? tile.profileId
                : (defaults[index]?.profileId || null),
            viewType: INFORMATION_VIEW_TYPES.some(
                type => type.id === tile?.viewType
            )
                ? tile.viewType
                : (defaults[index]?.viewType || "profile-views"),
        }));

    while (configuration.length < count) {
        configuration.push(
            defaults[configuration.length] || {
                profileId: null,
                viewType: "profile-views",
            }
        );
    }

    return configuration;
}

function saveTileConfiguration() {
    localStorage.setItem(
        "mnemosyne-tile-view-count",
        String(state.tileViewCount),
    );

    localStorage.setItem(
        "mnemosyne-tile-configuration",
        JSON.stringify(state.tileProfiles),
    );
}

function initTiles(profiles) {
    state.tileViewCount =
        Number(localStorage.getItem("mnemosyne-tile-view-count")) || 4;

    state.tileViewCount = Math.max(
        1,
        Math.min(state.tileViewCount, Math.max(profiles.length, 1)),
    );

    state.tileProfiles = loadTileConfiguration(profiles);

    // Persist repaired/default tile assignments so stale null
    // profile IDs do not return on the next page load.
    saveTileConfiguration();

    renderTileView();
}

function setTileCount(count) {
    const nextCount = Math.max(
        1,
        Math.min(Number(count) || 4, Math.max(state.profiles.length, 1)),
    );

    state.tileViewCount = nextCount;

    const current = Array.isArray(state.tileProfiles)
        ? state.tileProfiles
        : [];

    const next = current.slice(0, nextCount);

    while (next.length < nextCount) {
        const profile = [...state.profiles]
            .sort(sortProfilesByMemoryCount)
            .find(candidate =>
                !next.some(tile => tile.profileId === candidate.id)
            );

        next.push({
            profileId: profile?.id || null,
            viewType: "profile-views",
        });
    }

    state.tileProfiles = next;
    saveTileConfiguration();
    renderTileView();
}

function updateTile(index, field, value) {
    if (!state.tileProfiles[index]) {
        return;
    }

    state.tileProfiles[index][field] = value;
    saveTileConfiguration();
    renderTileView();
}

function formatTileDate(value) {
    if (!value) {
        return "Not recorded";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleString();
}

function renderTileOverview(body, profile, events) {
    const total = Number(profile.memory_count || 0);
    const collectiveTotal = state.profiles.reduce(
        (sum, candidate) => sum + Number(candidate.memory_count || 0),
        0,
    );

    const share = collectiveTotal
        ? ((total / collectiveTotal) * 100).toFixed(1)
        : "0.0";

    body.innerHTML = `
        <h3>${escapeHTML(profile.name)}</h3>
        <div class="tile-memory-count">${total.toLocaleString()}</div>
        <div class="tile-memory-label">collective memories</div>
        <div class="tile-stat-row">
            <span>Collective share</span>
            <strong>${share}%</strong>
        </div>
        <div class="tile-progress">
            <div class="tile-progress-fill" style="width:${Math.max(3, Number(share))}%"></div>
        </div>
    `;
}

function renderTileActivity(body, profile, events) {
    const promoted = events.filter(event => event.is_promoted).length;
    const revoked = events.filter(event => event.is_revoked).length;
    const validated = events.filter(event => event.validated_at).length;

    const latest = events.length
        ? events[events.length - 1]
        : null;

    body.innerHTML = `
        <h3>${escapeHTML(profile.name)}</h3>
        <div class="tile-kpi">${events.length.toLocaleString()}</div>
        <div class="tile-memory-label">collective events</div>
        <div class="tile-stat-grid">
            <div><strong>${promoted}</strong><span>Promoted</span></div>
            <div><strong>${validated}</strong><span>Validated</span></div>
            <div><strong>${revoked}</strong><span>Revoked</span></div>
        </div>
        <div class="tile-latest">
            <span>Latest entry</span>
            <strong>${latest ? `#${latest.id}` : "None"}</strong>
        </div>
    `;
}

function renderTileStatus(body, profile, events) {
    const promoted = events.filter(event => event.is_promoted).length;
    const revoked = events.filter(event => event.is_revoked).length;
    const pending = events.filter(
        event => !event.is_promoted && !event.is_revoked
    ).length;

    body.innerHTML = `
        <h3>${escapeHTML(profile.name)}</h3>
        <div class="tile-status-primary">
            <strong>${promoted.toLocaleString()}</strong>
            <span>promoted to collective</span>
        </div>
        <div class="tile-stat-grid">
            <div><strong>${pending}</strong><span>Pending</span></div>
            <div><strong>${revoked}</strong><span>Revoked</span></div>
        </div>
        <div class="tile-status-message">
            ${revoked === 0 && pending === 0
                ? "All recorded memories are currently promoted."
                : "Collective entries have mixed lifecycle states."}
        </div>
    `;
}

function renderTileValidation(body, profile, events) {
    const scored = events.filter(
        event => event.validation_score !== null &&
                 event.validation_score !== undefined
    );

    const validated = events.filter(event => event.validated_at).length;

    if (!scored.length && !validated) {
        body.innerHTML = `
            <h3>${escapeHTML(profile.name)}</h3>
            <div class="tile-kpi">—</div>
            <div class="tile-memory-label">validation score</div>
            <div class="tile-status-message">
                No validation data recorded yet.
            </div>
        `;
        return;
    }

    const average = scored.reduce(
        (sum, event) => sum + Number(event.validation_score || 0),
        0,
    ) / scored.length;

    body.innerHTML = `
        <h3>${escapeHTML(profile.name)}</h3>
        <div class="tile-kpi">${average.toFixed(2)}</div>
        <div class="tile-memory-label">average validation score</div>
        <div class="tile-stat-row">
            <span>Validated entries</span>
            <strong>${validated}</strong>
        </div>
        <div class="tile-stat-row">
            <span>Scored entries</span>
            <strong>${scored.length}</strong>
        </div>
    `;
}




function renderTileProfileViews(body, profile, events) {
    const total = Number(profile.memory_count || 0);

    const latest = events.length
        ? events[events.length - 1]
        : null;

    body.innerHTML = `
        <h3>${escapeHTML(profile.name)}</h3>

        <div class="tile-memory-count">
            ${total.toLocaleString()}
        </div>

        <div class="tile-memory-label">
            memories
        </div>

        <div class="tile-stat-grid">
            <div>
                <strong>${events.length.toLocaleString()}</strong>
                <span>Collective events</span>
            </div>

            <div>
                <strong>${events.filter(e => e.validated_at).length}</strong>
                <span>Validated</span>
            </div>
        </div>

        <div class="tile-latest">
            <span>Latest event</span>
            <strong>
                ${latest ? `#${escapeHTML(String(latest.id))}` : "None"}
            </strong>
        </div>
    `;
}


function renderTileDataTable(body, profile, events) {
    const recent = events.slice(-8).reverse();

    const lifecycleState = event => {
        if (event?.lifecycle_state) {
            return event.lifecycle_state;
        }

        if (event?.is_revoked) {
            return "Revoked";
        }

        if (event?.is_promoted) {
            return "Promoted";
        }

        if (event?.validated_at) {
            return "Validated";
        }

        return "Pending";
    };

    body.innerHTML = "";

    const heading = document.createElement("h3");
    heading.textContent = profile.name;
    body.appendChild(heading);

    const label = document.createElement("div");
    label.className = "tile-memory-label";
    label.textContent = "Recent entries";
    body.appendChild(label);

    const wrapper = document.createElement("div");
    wrapper.className = "tile-data-table-wrapper";

    const table = document.createElement("table");
    table.className = "data-table tile-data-table";

    table.innerHTML = `
        <thead>
            <tr>
                <th>Memory Content</th>
                <th>Agent / Profile</th>
                <th>Date / Time</th>
                <th>Lifecycle</th>
                <th>Memory ID</th>
            </tr>
        </thead>
        <tbody></tbody>
    `;

    const tableBody = table.querySelector("tbody");

    for (const event of recent) {
        const row = document.createElement("tr");

        const contentCell = document.createElement("td");
        contentCell.className = "memory-preview";
        contentCell.textContent =
            event?.memory_content ||
            "No memory content available.";

        const profileCell = document.createElement("td");
        profileCell.textContent =
            event?.profile ||
            profile?.name ||
            profileLabel(event?.source_profile);

        const dateCell = document.createElement("td");
        dateCell.className = "memory-date";
        dateCell.textContent = formatMemoryDate(event);

        const lifecycleCell = document.createElement("td");
        lifecycleCell.textContent = lifecycleState(event);

        const idCell = document.createElement("td");
        idCell.className = "memory-id";
        idCell.textContent =
            `#${String(event?.id ?? "")}`;

        row.appendChild(contentCell);
        row.appendChild(profileCell);
        row.appendChild(dateCell);
        row.appendChild(lifecycleCell);
        row.appendChild(idCell);

        row.addEventListener("click", () => {
            const graphNode = state.graph.nodes.find(node =>
                String(node?.source_profile || "").trim() ===
                    String(event?.source_profile || "").trim() &&
                String(node?.origin_memory_id || "").trim() ===
                    String(event?.origin_memory_id || "").trim()
            );

            if (graphNode) {
                selectNode(graphNode, state.graph);
            }
        });

        tableBody.appendChild(row);
    }

    if (!recent.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 5;
        cell.className = "tile-empty";
        cell.textContent = "No entries.";

        row.appendChild(cell);
        tableBody.appendChild(row);
    }

    wrapper.appendChild(table);
    body.appendChild(wrapper);
}

function renderTileConstellation3D(body, profile, graph) {
    body.innerHTML = "";

    const heading = document.createElement("h3");
    heading.textContent = profile.name;
    heading.className = "tile-3d-title";

    const host = document.createElement("div");
    host.className = "tile-3d-host";

    body.classList.add("tile-3d-constellation");

    body.appendChild(heading);
    body.appendChild(host);

    if (!window.Mnemosyne3D?.createInstance) {
        host.innerHTML =
            '<div class="loading-state">3D constellation unavailable.</div>';
        return;
    }

    const instance = window.Mnemosyne3D.createInstance(
        host,
        graph,
        state,
        (node, selectedGraph) => selectNode(node, selectedGraph),
        { compact: true },
    );

    body._mnemosyne3dInstance = instance;
}

async function renderTileCardBody(body, profile, viewType) {
    if (!profile) {
        body.innerHTML =
            '<div class="tile-empty">Select a profile for this tile.</div>';
        return;
    }

    if (body._mnemosyne3dInstance?.destroy) {
        body._mnemosyne3dInstance.destroy();
        body._mnemosyne3dInstance = null;
    }

    body.innerHTML =
        '<div class="tile-loading">Loading tile data…</div>';

    try {
        if (viewType === "2d" || viewType === "3d") {
            let graph = await fetchTileGraph(profile.id);

            const hasFilters =
                Boolean(state.globalFilter.search?.trim()) ||
                Boolean(state.globalFilter.dateFrom) ||
                Boolean(state.globalFilter.dateTo) ||
                (
                    state.globalFilter.profileScope !== "all" &&
                    Boolean(state.globalFilter.profileScope)
                );

            if (hasFilters) {
                graph = await getGloballyFilteredGraph(graph);
            }

            if (viewType === "2d") {
                renderTileConstellation2D(
                    body,
                    profile,
                    graph,
                );
            } else {
                renderTileConstellation3D(
                    body,
                    profile,
                    graph,
                );
            }

            return;
        }

        const rawEvents = await fetchTileEvents(profile.id);
        const events = filterTimelineEvents(rawEvents);

        switch (viewType) {
            case "table":
                renderTileDataTable(body, profile, events);
                break;

            case "profile-views":
                renderTileProfileViews(body, profile, events);
                break;

            case "activity":
                renderTileActivity(body, profile, events);
                break;

            case "status":
                renderTileStatus(body, profile, events);
                break;

            case "validation":
                renderTileValidation(body, profile, events);
                break;

            default:
                renderTileProfileViews(body, profile, events);
                break;
        }
    } catch (error) {
        console.error("Tile data error:", error);

        body.innerHTML =
            '<div class="tile-empty">Unable to load tile data.</div>';
    }
}


function renderTileView() {
    const container = $("tile-view");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    const toolbar = document.createElement("div");
    toolbar.className = "tile-toolbar";

    const title = document.createElement("div");
    title.className = "tile-toolbar-title";
    title.innerHTML =
        "<strong>Profile Dashboard</strong>" +
        "<span>Configure what information each tile displays.</span>";

    const countLabel = document.createElement("label");
    countLabel.className = "tile-count-control";
    countLabel.innerHTML = "<span>Tiles</span>";

    const countSelect = document.createElement("select");

    [1, 2, 4, 6, 8].forEach(count => {
        if (count > Math.max(state.profiles.length, 1)) {
            return;
        }

        const option = document.createElement("option");
        option.value = String(count);
        option.textContent = String(count);

        if (count === state.tileViewCount) {
            option.selected = true;
        }

        countSelect.appendChild(option);
    });

    countSelect.addEventListener("change", event => {
        setTileCount(event.target.value);
    });

    countLabel.appendChild(countSelect);
    toolbar.appendChild(title);
    toolbar.appendChild(countLabel);
    container.appendChild(toolbar);

    const grid = document.createElement("div");
    grid.className = "tile-grid";

    if (!state.profiles.length) {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent = "No profiles available.";
        grid.appendChild(empty);
        container.appendChild(grid);
        return;
    }

    state.tileProfiles.forEach((tile, index) => {
        const profile = state.profiles.find(
            candidate => candidate.id === tile.profileId
        );

        const card = document.createElement("article");
        card.className = "tile-card";

        const header = document.createElement("div");
        header.className = "tile-card-header";

        const number = document.createElement("span");
        number.className = "tile-number";
        number.textContent = `Tile ${index + 1}`;

        const profileSelect = document.createElement("select");
        profileSelect.className = "tile-profile-select";

        state.profiles
            .slice()
            .sort(sortProfilesByMemoryCount)
            .forEach(candidate => {
                const option = document.createElement("option");
                option.value = candidate.id;
                option.textContent = candidate.name;

                if (candidate.id === tile.profileId) {
                    option.selected = true;
                }

                profileSelect.appendChild(option);
            });

        profileSelect.addEventListener("change", event => {
            updateTile(index, "profileId", event.target.value);
        });

        header.appendChild(number);
        header.appendChild(profileSelect);

        const controls = document.createElement("div");
        controls.className = "tile-card-controls";

        const viewSelect = document.createElement("select");
        viewSelect.className = "tile-view-select";

        INFORMATION_VIEW_TYPES.forEach(type => {
            const option = document.createElement("option");
            option.value = type.id;
            option.textContent = type.label;

            if (type.id === tile.viewType) {
                option.selected = true;
            }

            viewSelect.appendChild(option);
        });

        viewSelect.addEventListener("change", event => {
            updateTile(index, "viewType", event.target.value);
        });

        controls.appendChild(viewSelect);

        const body = document.createElement("div");
        body.className = "tile-card-body";

        card.appendChild(header);
        card.appendChild(controls);
        card.appendChild(body);

        card.addEventListener("click", event => {
            if (
                event.target.closest("select") ||
                !profile
            ) {
                return;
            }

            selectProfile(profile.id);
        });

        grid.appendChild(card);

        renderTileCardBody(body, profile, tile.viewType);
    });

    container.appendChild(grid);
}


function renderInspector(node, graph) {
    const container = $("inspector-content");

    if (!node) {
        container.innerHTML =
            '<div class="empty-state">' +
            '<strong>No selection</strong>' +
            '<p>Select a node to inspect its memory.</p>' +
            '</div>';
        return;
    }

    const outgoing = Array.isArray(graph.edges?.[node.graph_id])
        ? graph.edges[node.graph_id]
        : [];

    const incoming = flattenEdges(graph.edges)
        .filter(e => e.target_id === node.graph_id);

    container.innerHTML = "";

    const title = document.createElement("section");
    title.className = "inspector-section";
    title.innerHTML = `
        <h3>${escapeHTML(
            INFORMATION_VIEW_TYPES.find(
                type => type.id === state.informationView
            )?.label || "Profile Overview"
        )}</h3>
    `;
    container.appendChild(title);

    if (state.informationView === "2d") {
        renderGraph2D(graph);
    } else if (state.informationView === "3d") {
        renderGraph3D(graph);
    } else if (state.informationView === "table") {
        renderTable(graph);
    } else if (state.informationView === "activity") {
        renderInspectorActivity(container, node, graph);
    } else if (state.informationView === "status") {
        renderInspectorStatus(container, node, graph);
    } else if (state.informationView === "validation") {
        renderInspectorValidation(container, node, graph);
    } else {
        renderInspectorOverview(container, node, graph, outgoing, incoming);
    }
}

function inspectorSection(title) {
    const section = document.createElement("section");
    section.className = "inspector-section";

    const heading = document.createElement("h3");
    heading.textContent = title;

    section.appendChild(heading);
    return section;
}

function renderInspectorOverview(container, node, graph, outgoing, incoming) {
    const memorySection = inspectorSection("Memory Content");
    memorySection.innerHTML +=
        '<div id="memory-content" class="memory-loading">' +
        'Loading source memory…</div>';
    container.appendChild(memorySection);

    const identity = inspectorSection("Identity");
    identity.innerHTML += `
        <dl class="inspector-grid">
            <dt>Graph ID</dt><dd>${escapeHTML(node.graph_id)}</dd>
            <dt>Profile</dt><dd>${escapeHTML(node.source_profile)}</dd>
            <dt>Memory ID</dt><dd>${escapeHTML(node.origin_memory_id)}</dd>
        </dl>`;
    container.appendChild(identity);

    const lifecycle = inspectorSection("Lifecycle");
    lifecycle.innerHTML += `
        <dl class="inspector-grid">
            <dt>State</dt><dd>${escapeHTML(node.lifecycle_state)}</dd>
            <dt>Proposed</dt><dd>${escapeHTML(node.proposed_at)}</dd>
            <dt>Validated</dt><dd>${escapeHTML(node.validated_at)}</dd>
            <dt>Validator</dt><dd>${escapeHTML(node.validator_profile)}</dd>
            <dt>Validation score</dt><dd>${formatScore(node.validation_score)}</dd>
        </dl>`;
    container.appendChild(lifecycle);

    const relationships = inspectorSection("Relationships");
    relationships.innerHTML +=
        `<div class="relationship-count">${outgoing.length} outgoing · ${incoming.length} incoming</div>`;

    for (const edge of outgoing) {
        const item = document.createElement("div");
        item.className = "relationship";
        item.innerHTML = `
            <div>
                <span class="relationship-type">
                    ${escapeHTML(edge.relationship_type)}
                </span>
            </div>
            <div>→ ${escapeHTML(edge.target_id)}</div>
            <div>similarity: ${formatScore(edge.similarity_score)}</div>`;
        relationships.appendChild(item);
    }

    if (!outgoing.length) {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent = "No outgoing relationships in this view.";
        relationships.appendChild(empty);
    }

    container.appendChild(relationships);
    loadMemoryContent(node);
}

function renderInspectorActivity(container, node, graph) {
    const outgoing = Array.isArray(graph.edges?.[node.graph_id])
        ? graph.edges[node.graph_id]
        : [];

    const section = inspectorSection("Activity");
    section.innerHTML += `
        <div class="tile-stat-grid">
            <div>
                <strong>${outgoing.length}</strong>
                <span>Outgoing relationships</span>
            </div>
            <div>
                <strong>${flattenEdges(graph.edges)
                    .filter(e => e.target_id === node.graph_id).length}</strong>
                <span>Incoming relationships</span>
            </div>
        </div>

        <dl class="inspector-grid">
            <dt>Lifecycle</dt>
            <dd>${escapeHTML(node.lifecycle_state)}</dd>
            <dt>Proposed</dt>
            <dd>${escapeHTML(node.proposed_at)}</dd>
            <dt>Validated</dt>
            <dd>${escapeHTML(node.validated_at)}</dd>
        </dl>`;
    container.appendChild(section);

    const memory = inspectorSection("Memory Content");
    memory.innerHTML +=
        '<div id="memory-content" class="memory-loading">' +
        'Loading source memory…</div>';
    container.appendChild(memory);
    loadMemoryContent(node);
}

function renderInspectorStatus(container, node) {
    const section = inspectorSection("Collective Status");

    const promoted = node.is_promoted !== false;
    const revoked = Boolean(node.is_revoked);

    section.innerHTML += `
        <div class="tile-status-primary">
            <strong>${revoked ? "Revoked" : promoted ? "Promoted" : "Pending"}</strong>
            <span>current collective lifecycle</span>
        </div>

        <dl class="inspector-grid">
            <dt>Profile</dt>
            <dd>${escapeHTML(node.source_profile)}</dd>
            <dt>Lifecycle state</dt>
            <dd>${escapeHTML(node.lifecycle_state)}</dd>
            <dt>Revoked</dt>
            <dd>${revoked ? "Yes" : "No"}</dd>
        </dl>`;

    container.appendChild(section);
}

function renderInspectorValidation(container, node) {
    const section = inspectorSection("Validation");

    section.innerHTML += `
        <dl class="inspector-grid">
            <dt>Validation score</dt>
            <dd>${formatScore(node.validation_score)}</dd>
            <dt>Validated</dt>
            <dd>${escapeHTML(node.validated_at)}</dd>
            <dt>Validator</dt>
            <dd>${escapeHTML(node.validator_profile)}</dd>
        </dl>`;

    if (
        node.validation_score === null ||
        node.validation_score === undefined
    ) {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent = "No validation data recorded yet.";
        section.appendChild(empty);
    }

    container.appendChild(section);
}
async function loadMemoryContent(node) {
    const target = $("memory-content");
    if (!target) return;

    try {
        const source = String(node.source_profile || "");
        let data;

        if (source.includes(":")) {
            const separator = source.indexOf(":");
            const agentId = source.slice(0, separator);
            const profile = source.slice(separator + 1);

            if (agentId === state.localAgentId) {
                data = await fetchJSON(
                    `/api/memories/${encodeURIComponent(profile)}/${encodeURIComponent(node.origin_memory_id)}`
                );
            } else {
                const agent = state.agentMap.get(agentId);

                if (!agent?.base_url) {
                    throw new Error(
                        `Source agent ${agentId} is not available through LAN discovery.`
                    );
                }

                data = await fetchJSON(
                    `${agent.base_url}/api/memories/${encodeURIComponent(profile)}/${encodeURIComponent(node.origin_memory_id)}`
                );
            }
        } else {
            data = await fetchJSON(
                `/api/memories/${encodeURIComponent(source)}/${encodeURIComponent(node.origin_memory_id)}`
            );
        }

        target.className = "memory-content";
        target.textContent = data.content;
    } catch (error) {
        target.className = "error-state";
        target.textContent =
            `Unable to retrieve source memory: ${error.message}`;
    }
}


function entityGraphNodeLabel(node) {
    if (!node) return "Unknown";

    if (node.node_type === "entity") {
        return (
            node.canonical_name ||
            node.entity_id ||
            node.node_id ||
            "Entity"
        );
    }

    if (node.node_type === "memory") {
        const profile = node.source_profile || "Unknown profile";
        const memory = node.origin_memory_id || "Unknown memory";
        return `${profile}:${memory}`;
    }

    return node.node_id || "Unknown";
}

function entityGraphEdgeKey(edge) {
    if (!edge) return "";

    return [
        edge.source_id || "",
        edge.target_id || "",
        edge.edge_type || "",
        edge.collective_entry_id ?? "",
        edge.relationship_id || "",
        edge.relationship_kind || "",
    ].join("|");
}

function entityGraphNodeClass(node, selected) {
    const type = node?.node_type || "unknown";

    return [
        "entity-graph-node",
        `entity-graph-node-${type}`,
        selected ? "selected" : "",
    ].filter(Boolean).join(" ");
}

function entityGraphPositions(nodes, width, height) {
    const positions = new Map();
    const centerX = width / 2;
    const centerY = height / 2;

    const entities = nodes.filter(
        node => node.node_type === "entity",
    );

    const memories = nodes.filter(
        node => node.node_type === "memory",
    );

    const entityRadius = Math.max(
        110,
        Math.min(width, height) * 0.24,
    );

    entities.forEach((node, index) => {
        const angle =
            index / Math.max(entities.length, 1) * Math.PI * 2 -
            Math.PI / 2;

        positions.set(node.node_id, {
            x: centerX + Math.cos(angle) * entityRadius,
            y: centerY + Math.sin(angle) * entityRadius,
        });
    });

    const memoryRadius = Math.max(
        220,
        Math.min(width, height) * 0.39,
    );

    memories.forEach((node, index) => {
        const angle =
            index / Math.max(memories.length, 1) * Math.PI * 2 -
            Math.PI / 2;

        positions.set(node.node_id, {
            x: centerX + Math.cos(angle) * memoryRadius,
            y: centerY + Math.sin(angle) * memoryRadius,
        });
    });

    return positions;
}

function renderEntityGraph(
    graph = state.entityGraph,
    fitToViewport = false,
) {
    const container = $("graph-view");

    if (!container) return;

    container.innerHTML = "";

    if (!graph?.nodes?.length) {
        container.innerHTML =
            '<div class="loading-state">No entity graph data available.</div>';
        renderStatistics();
        return;
    }

    const rect = container.getBoundingClientRect();
    const width = Math.max(rect.width, 800);
    const height = Math.max(rect.height, 600);

    const svg = createSVGElement("svg", {
        class: "graph-svg entity-graph-svg",
        viewBox: `0 0 ${width} ${height}`,
        preserveAspectRatio: "xMidYMid meet",
        "aria-label": "Mnemosyne entity graph",
    });

    const viewport = createSVGElement(
        "g",
        {class: "graph-viewport"},
    );

    svg.appendChild(viewport);

    const positions = entityGraphPositions(
        graph.nodes,
        width,
        height,
    );

    if (fitToViewport) {
        fit2DGraphToViewport(
            positions,
            width,
            height,
        );
        state.entityGraphViewInitialized = true;
    }

    const edges = Array.isArray(graph.edges)
        ? graph.edges
        : [];

    const edgeGroup = createSVGElement(
        "g",
        {class: "entity-graph-edges"},
    );

    for (const edge of edges) {
        const source = positions.get(edge.source_id);
        const target = positions.get(edge.target_id);

        if (!source || !target) continue;

        const selected =
            entityGraphEdgeKey(state.selectedEntityEdge) ===
            entityGraphEdgeKey(edge);

        const line = createSVGElement("line", {
            class: [
                "entity-graph-edge",
                edge.edge_type === "relationship"
                    ? "relationship-edge"
                    : "mention-edge",
                selected ? "selected" : "",
            ].filter(Boolean).join(" "),
            x1: source.x,
            y1: source.y,
            x2: target.x,
            y2: target.y,
        });

        line.dataset.entityGraphEdgeKey =
            entityGraphEdgeKey(edge);

        if (edge.relationship_id) {
            line.dataset.relationshipId = edge.relationship_id;
        }

        if (
            edge.confidence !== null &&
            edge.confidence !== undefined
        ) {
            line.setAttribute(
                "stroke-width",
                Math.max(1, Number(edge.confidence) * 3),
            );
        }

        line.addEventListener("click", event => {
            event.stopPropagation();
            selectEntityEdge(edge);
        });

        edgeGroup.appendChild(line);
    }

    viewport.appendChild(edgeGroup);

    const nodeGroup = createSVGElement(
        "g",
        {class: "entity-graph-nodes"},
    );

    for (const node of graph.nodes) {
        const position = positions.get(node.node_id);

        if (!position) continue;

        const selected =
            state.selectedEntityNode?.node_id === node.node_id;

        const isEntity = node.node_type === "entity";

        const circle = createSVGElement("circle", {
            class: entityGraphNodeClass(node, selected),
            cx: position.x,
            cy: position.y,
            r: selected
                ? (isEntity ? 11 : 8)
                : (isEntity ? 9 : 6),
            tabindex: "0",
            "aria-label": entityGraphNodeLabel(node),
        });

        circle.dataset.entityNodeId = node.node_id;

        if (isEntity) {
            circle.style.fill = "var(--accent)";
        } else {
            circle.style.fill = colorForProfile(
                profileLabel(node.source_profile || "unknown"),
            );
        }

        circle.addEventListener("click", event => {
            event.stopPropagation();
            selectEntityNode(node);
        });

        circle.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                selectEntityNode(node);
            }
        });

        nodeGroup.appendChild(circle);
    }

    viewport.appendChild(nodeGroup);
    container.appendChild(svg);

    bindGraphInteraction(container);
    applyTransform();
}

function selectEntityNode(node) {
    state.selectedEntityNode = node;
    state.selectedEntityEdge = null;

    renderEntityInspector(node);

    setSelectionStatus(
        `Selected ${entityGraphNodeLabel(node)}`,
    );

    renderEntityGraph(state.entityGraph);
}

function selectEntityEdge(edge) {
    state.selectedEntityEdge = edge;
    state.selectedEntityNode = null;

    const isRelationship =
        edge?.edge_type === "relationship" ||
        Boolean(edge?.relationship_id);

    if (isRelationship) {
        renderRelationshipInspector(edge);

        const relationship =
            edge.relationship_kind ||
            edge.edge_type ||
            "relationship";

        setSelectionStatus(
            `Selected ${relationship}`,
        );
    } else {
        renderMentionInspector(edge);

        setSelectionStatus(
            `Selected mention: ${edge?.mention_text || "reference"}`,
        );
    }

    renderEntityGraph(state.entityGraph);
}

function renderEntityInspector(node) {
    const container = $("inspector-content");

    if (!container) return;

    container.innerHTML = "";

    const title = document.createElement("section");
    title.className = "inspector-section";
    title.innerHTML = "<h3>Entity Graph</h3>";
    container.appendChild(title);

    if (!node) {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent =
            "Select an entity or memory node to inspect it.";
        container.appendChild(empty);
        return;
    }

    const section = inspectorSection(
        node.node_type === "entity"
            ? "Entity"
            : "Collective Memory Reference",
    );

    const rows = [
        ["Node ID", node.node_id],
        ["Node type", node.node_type],
        ["Lifecycle", node.lifecycle_state],
    ];

    if (node.node_type === "entity") {
        rows.push(
            ["Canonical name", node.canonical_name],
            ["Entity type", node.entity_type],
            ["Confidence", formatScore(node.confidence)],
            ["Mention count", node.mention_count],
            [
                "Source profiles",
                Array.isArray(node.source_profiles)
                    ? node.source_profiles.join(", ")
                    : "Not recorded",
            ],
            ["Entity ID", node.entity_id],
        );
    } else {
        rows.push(
            ["Source profile", node.source_profile],
            ["Origin memory", node.origin_memory_id],
        );
    }

    section.innerHTML += `
        <dl class="inspector-grid">
            ${rows.map(([label, value]) => `
                <dt>${escapeHTML(label)}</dt>
                <dd>${escapeHTML(value ?? "Not recorded")}</dd>
            `).join("")}
        </dl>
    `;

    const note = document.createElement("div");
    note.className =
        "empty-state entity-graph-governance-note";

    note.textContent =
        node.node_type === "entity"
            ? "Canonical entity metadata only. Source memory content is not exposed by the entity graph."
            : "Collective memory reference only. Source memory content is not loaded from the entity graph.";

    section.appendChild(note);
    container.appendChild(section);
}

function renderMentionInspector(edge) {
    const container = $("inspector-content");

    if (!container) return;

    container.innerHTML = "";

    const title = document.createElement("section");
    title.className = "inspector-section";
    title.innerHTML = "<h3>Entity Graph</h3>";
    container.appendChild(title);

    if (!edge) {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent =
            "Select a mention edge to inspect it.";
        container.appendChild(empty);
        return;
    }

    const section = inspectorSection("Entity Mention");

    section.innerHTML += `
        <dl class="inspector-grid">
            <dt>Mention</dt>
            <dd>${escapeHTML(edge.mention_text ?? "Not recorded")}</dd>
            <dt>Confidence</dt>
            <dd>${formatScore(edge.confidence)}</dd>
            <dt>Source profile</dt>
            <dd>${escapeHTML(edge.source_profile ?? "Not recorded")}</dd>
            <dt>Source memory</dt>
            <dd>${escapeHTML(edge.source_memory_id ?? "Not recorded")}</dd>
            <dt>Collective entry</dt>
            <dd>${escapeHTML(edge.collective_entry_id ?? "Not recorded")}</dd>
            <dt>Source node</dt>
            <dd>${escapeHTML(edge.source_id ?? "Not recorded")}</dd>
            <dt>Target entity</dt>
            <dd>${escapeHTML(edge.target_id ?? "Not recorded")}</dd>
        </dl>
    `;

    const note = document.createElement("div");
    note.className =
        "empty-state entity-graph-governance-note";

    note.textContent =
        "Read-only entity mention evidence. Source memory content is not loaded or exposed by the entity graph.";

    section.appendChild(note);
    container.appendChild(section);
}

function renderRelationshipInspector(edge) {
    const container = $("inspector-content");

    if (!container) return;

    container.innerHTML = "";

    const title = document.createElement("section");
    title.className = "inspector-section";
    title.innerHTML = "<h3>Relationship</h3>";
    container.appendChild(title);

    if (!edge) {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent =
            "Select a relationship to inspect it.";
        container.appendChild(empty);
        return;
    }

    const section = inspectorSection("Relationship Evidence");

    section.innerHTML += `
        <dl class="inspector-grid">
            <dt>Relationship ID</dt>
            <dd>${escapeHTML(edge.relationship_id ?? "Not recorded")}</dd>
            <dt>Relationship kind</dt>
            <dd>${escapeHTML(edge.relationship_kind ?? "Not recorded")}</dd>
            <dt>Confidence</dt>
            <dd>${formatScore(edge.confidence)}</dd>
            <dt>Source entity</dt>
            <dd>${escapeHTML(edge.source_id)}</dd>
            <dt>Target entity</dt>
            <dd>${escapeHTML(edge.target_id)}</dd>
            <dt>Collective entry</dt>
            <dd>${escapeHTML(edge.collective_entry_id ?? "Not recorded")}</dd>
        </dl>
    `;

    const note = document.createElement("div");
    note.className =
        "empty-state entity-graph-governance-note";

    note.textContent =
        "Read-only relationship projection. No relationship editing is available from the Browser.";

    section.appendChild(note);
    container.appendChild(section);
}

function selectNode(node, graph = state.graph) {
    state.selectedNode = node;

    renderInspector(node, graph);

    setSelectionStatus(
        `Selected ${node.source_profile}:${node.origin_memory_id}`
    );

    document.querySelectorAll(".graph-node").forEach(element =>
        element.classList.toggle(
            "selected",
            element.dataset.graphId === node.graph_id
        )
    );

    document.querySelectorAll(".data-table tbody tr").forEach(element =>
        element.classList.toggle(
            "selected",
            element.dataset.graphId === node.graph_id
        )
    );
}

async function renderTable(graph){
    const container = $("table-view");
    container.innerHTML = "";

    if (!graph.nodes.length) {
        container.innerHTML =
            '<div class="loading-state">No graph data available.</div>';
        return;
    }

    let events = [];

    try {
        events = await fetchGlobalEvents();
    } catch (error) {
        console.warn(
            "Unable to load event metadata for Data Table:",
            error
        );
    }

    const eventMap = new Map();

    for (const event of events) {
        const source = String(
            event?.source_profile || ""
        ).trim();

        const memoryId = String(
            event?.origin_memory_id || ""
        ).trim();

        if (!source || !memoryId) {
            continue;
        }

        eventMap.set(
            `${source}::${memoryId}`,
            event
        );
    }

    const table = document.createElement("table");
    table.className = "data-table";
    table.innerHTML = `<thead><tr>
        <th>Memory Content</th>
        <th>Agent / Profile</th>
        <th>Date / Time</th>
        <th>Lifecycle</th>
        <th>Memory ID</th>
    </tr></thead><tbody></tbody>`;

    const body = table.querySelector("tbody");

    for (const node of graph.nodes) {
        const row = document.createElement("tr");
        row.dataset.graphId = node.graph_id;

        const contentCell = document.createElement("td");
        contentCell.className = "memory-preview";
        contentCell.textContent = "Loading…";

        const profileCell = document.createElement("td");
        profileCell.textContent =
            profileLabel(node.source_profile);

        const source = String(
            node?.source_profile || ""
        ).trim();

        const memoryId = String(
            node?.origin_memory_id || ""
        ).trim();

        const event = eventMap.get(
            `${source}::${memoryId}`
        );

        const dateCell = document.createElement("td");
        dateCell.className = "memory-date";
        dateCell.textContent = event
            ? formatMemoryDate(event)
            : "Date not recorded";

        const lifecycleCell = document.createElement("td");
        lifecycleCell.textContent =
            node.lifecycle_state || "—";

        const idCell = document.createElement("td");
        idCell.className = "memory-id";
        idCell.textContent =
            node.origin_memory_id;

        row.appendChild(contentCell);
        row.appendChild(profileCell);
        row.appendChild(dateCell);
        row.appendChild(lifecycleCell);
        row.appendChild(idCell);

        row.addEventListener(
            "click",
            () => selectNode(node, graph)
        );

        body.appendChild(row);

        loadTableMemoryPreview(
            node,
            contentCell
        );
    }

    container.appendChild(table);
}

async function loadTableMemoryPreview(node, target){
    try{
        const source=String(node.source_profile || "");
        let data;

        if(source.includes(":")){
            const separator=source.indexOf(":");
            const agentId=source.slice(0,separator);
            const profile=source.slice(separator+1);

            if(agentId === state.localAgentId){
                data=await fetchJSON(
                    `/api/memories/${encodeURIComponent(profile)}/${encodeURIComponent(node.origin_memory_id)}`
                );
            }else{
                const agent=state.agentMap.get(agentId);

                if(!agent?.base_url){
                    throw new Error(`Source agent ${agentId} is not available through LAN discovery.`);
                }

                data=await fetchJSON(
                    `${agent.base_url}/api/memories/${encodeURIComponent(profile)}/${encodeURIComponent(node.origin_memory_id)}`
                );
            }
        }else{
            data=await fetchJSON(
                `/api/memories/${encodeURIComponent(source)}/${encodeURIComponent(node.origin_memory_id)}`
            );
        }

        const content=String(data.content || "").trim();

        if(!content){
            target.textContent="(No memory content)";
            return;
        }

        const maxLength=220;
        target.textContent=content.length > maxLength
            ? `${content.slice(0,maxLength)}…`
            : content;
        target.title=content;
    }catch(error){
        target.textContent="Unable to load memory";
        target.title=error.message;
    }
}


function renderHybridSearch(results = state.hybridResults, metadata = null) {
    const container = $("hybrid-search-view");
    if (!container) return;

    container.innerHTML = "";

    const header = document.createElement("div");
    header.className = "hybrid-search-header";
    header.innerHTML = `
        <div>
            <h3>Hybrid Retrieval</h3>
            <p>${escapeHTML(metadata?.query || state.globalFilter.search || "")}</p>
        </div>
        <span class="hybrid-search-count">${results.length.toLocaleString()} result${results.length === 1 ? "" : "s"}</span>
    `;
    container.appendChild(header);

    const diagnostics = metadata?.diagnostics;
    if (diagnostics) {
        const section = document.createElement("section");
        section.className = "inspector-section hybrid-diagnostics";

        const evaluation =
            diagnostics.evaluation === null ||
            diagnostics.evaluation === undefined
                ? "Not evaluated"
                : "Evaluated";

        section.innerHTML = `
            <h3>Retrieval Diagnostics</h3>
            <div class="tile-stat-grid">
                <div>
                    <strong>${Number(diagnostics.result_count ?? results.length).toLocaleString()}</strong>
                    <span>Returned</span>
                </div>
                <div>
                    <strong>${Number(diagnostics.requested_top_k ?? 0).toLocaleString()}</strong>
                    <span>Requested top K</span>
                </div>
                <div>
                    <strong>${Number(diagnostics.candidate_limit ?? 0).toLocaleString()}</strong>
                    <span>Candidate limit</span>
                </div>
                <div>
                    <strong>${diagnostics.reranking_enabled ? "Yes" : "No"}</strong>
                    <span>Reranking</span>
                </div>
            </div>
            <dl class="inspector-grid">
                <dt>Evaluation</dt>
                <dd>${escapeHTML(evaluation)}</dd>
            </dl>
        `;

        container.appendChild(section);
    }

    if (metadata?.reranker_available === false) {
        const notice = document.createElement("div");
        notice.className = "hybrid-search-notice";
        notice.textContent = "Local CrossEncoder unavailable; showing governed RRF results.";
        container.appendChild(notice);
    }

    if (!results.length) {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent = "No governed memories matched this query.";
        container.appendChild(empty);
        return;
    }

    const list = document.createElement("div");
    list.className = "hybrid-result-list";

    for (const result of results) {
        const card = document.createElement("article");
        card.className = "hybrid-result-card";

        const title = document.createElement("div");
        title.className = "hybrid-result-title";
        title.innerHTML = `
            <strong>#${escapeHTML(result.fused_rank)}</strong>
            <span>${escapeHTML(profileLabel(result.source_profile))}</span>
            <span class="hybrid-score">Fused ${formatScore(result.fused_score)}</span>
        `;

        const identity = document.createElement("div");
        identity.className = "hybrid-result-identity";
        identity.textContent = `Memory ${result.origin_memory_id}`;

        const signals = document.createElement("div");
        signals.className = "hybrid-signals";
        const addSignal = (label, rank, contribution) => {
            if (rank === null || rank === undefined) return;
            const chip = document.createElement("span");
            chip.className = "hybrid-signal";
            chip.textContent = `${label} #${rank} · ${formatScore(contribution)}`;
            signals.appendChild(chip);
        };
        addSignal("BM25", result.keyword_rank, result.keyword_contribution);
        addSignal("Semantic", result.semantic_rank, result.semantic_contribution);
        addSignal("Graph", result.graph_rank, result.graph_contribution);
        addSignal("Temporal", result.temporal_rank, result.temporal_contribution);

        if (result.reranker_rank !== null && result.reranker_rank !== undefined) {
            const rerank = document.createElement("span");
            rerank.className = "hybrid-signal hybrid-reranker";
            const movement = result.rank_change > 0 ? `↑${result.rank_change}` : result.rank_change < 0 ? `↓${Math.abs(result.rank_change)}` : "=";
            rerank.textContent = `CrossEncoder #${result.reranker_rank} · ${formatScore(result.reranker_score)} · ${movement}`;
            signals.appendChild(rerank);
        }

        const provenance = document.createElement("div");
        provenance.className = "hybrid-provenance";
        const provenanceCount = Array.isArray(result.provenance) ? result.provenance.length : 0;
        provenance.textContent = `${provenanceCount} provenance record${provenanceCount === 1 ? "" : "s"}`;

        const inspect = document.createElement("button");
        inspect.type = "button";
        inspect.className = "hybrid-inspect-button";
        inspect.textContent = "Inspect memory";
        inspect.addEventListener("click", async () => {
            await inspectHybridResult(result);
        });

        card.append(title, identity, signals, provenance, inspect);
        list.appendChild(card);
    }

    container.appendChild(list);
}

async function inspectHybridResult(result) {
    let node = state.graph.nodes.find(candidate =>
        String(candidate.source_profile) === String(result.source_profile) &&
        String(candidate.origin_memory_id) === String(result.origin_memory_id)
    );

    if (!node) {
        try {
            const graph = await fetchGraph(result.source_profile);
            node = graph.nodes.find(candidate =>
                String(candidate.source_profile) === String(result.source_profile) &&
                String(candidate.origin_memory_id) === String(result.origin_memory_id)
            );
            if (node) state.graph = graph;
        } catch (error) {
            setStatus(`Unable to load result graph node: ${error.message}`, true);
            return;
        }
    }

    if (!node) {
        setStatus("Hybrid result is no longer present in the collective graph.", true);
        return;
    }

    selectNode(node, state.graph);
    setStatus(`Inspecting hybrid result #${result.fused_rank}.`);
}

async function runHybridSearch() {
    const container = $("hybrid-search-view");
    if (container) {
        container.classList.remove("hidden");
        container.innerHTML = '<div class="loading-state">Running hybrid retrieval…</div>';
    }

    try {
        state.hybridSearchLoading = true;
        setStatus("Running governed hybrid retrieval…");
        setViewMode("hybrid-search");
        const response = await fetchHybridSearch();
        state.hybridResults = Array.isArray(response.results) ? response.results : [];
        renderHybridSearch(state.hybridResults, response);
        setStatus(`Hybrid retrieval complete — ${state.hybridResults.length.toLocaleString()} results.`);
    } catch (error) {
        if (container) {
            container.innerHTML = `<div class="error-state">Hybrid retrieval failed.<br>${escapeHTML(error.message)}</div>`;
        }
        setStatus(`Hybrid retrieval failed: ${error.message}`, true);
    } finally {
        state.hybridSearchLoading = false;
    }
}

function setInformationView(view) {
    if (!INFORMATION_VIEW_TYPES.some(type => type.id === view)) {
        view = "profile-views";
    }

    state.informationView = view;

    localStorage.setItem(
        "mnemosyne-information-view",
        view
    );

    const select = $("information-view");
    if (select) {
        select.value = view;
    }

    if (state.viewMode === "tiles") {
        renderTileView();
        return;
    }

    if (state.viewMode === "table") {
        renderTable(state.graph);
    }

    if (state.selectedNode) {
        renderInspector(state.selectedNode, state.graph);
    }
}


function normalizedSearchText(value) {
    return String(value || "")
        .toLocaleLowerCase()
        .trim();
}

function timelineMemoryContent(event) {
    return (
        event?.memory_content ||
        event?.content ||
        event?.text ||
        ""
    );
}

function eventMatchesGlobalFilters(event) {
    const profileFilter =
        String(state.globalFilter.profileScope || "all").trim();

    if (profileFilter && profileFilter !== "all") {
        const eventProfile = profileLabel(
            event?.source_profile
        ).trim();

        if (
            eventProfile !== profileFilter
        ) {
            return false;
        }
    }

    const search = normalizedSearchText(state.globalFilter.search);

    if (search) {
        const content = normalizedSearchText(
            timelineMemoryContent(event)
        );

        if (!content.includes(search)) {
            return false;
        }
    }

    const eventDate = timelineEventDate(event);

    if (state.globalFilter.dateFrom) {
        if (!eventDate) return false;

        const eventTime = new Date(eventDate).getTime();
        const fromTime = new Date(
            `${state.globalFilter.dateFrom}T00:00:00`
        ).getTime();

        if (
            !Number.isFinite(eventTime) ||
            !Number.isFinite(fromTime) ||
            eventTime < fromTime
        ) {
            return false;
        }
    }

    if (state.globalFilter.dateTo) {
        if (!eventDate) return false;

        const eventTime = new Date(eventDate).getTime();
        const toTime = new Date(
            `${state.globalFilter.dateTo}T23:59:59.999`
        ).getTime();

        if (
            !Number.isFinite(eventTime) ||
            !Number.isFinite(toTime) ||
            eventTime > toTime
        ) {
            return false;
        }
    }

    return true;
}

function filterTimelineEvents(events) {
    return (Array.isArray(events) ? events : [])
        .filter(eventMatchesGlobalFilters);
}

function timelineEventDate(event) {
    return (
        event?.memory_date ||
        event?.event_date ||
        event?.timestamp ||
        event?.created_at ||
        event?.proposed_at ||
        event?.validated_at ||
        null
    );
}

function formatMemoryDate(event) {
    const value = timelineEventDate(event);

    if (!value) {
        return "Date not recorded";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    });
}

async function fetchGlobalEvents() {
    /*
     * The left profile selector controls the base graph scope.
     * The header Profiles selector is an independent filter applied
     * by filterTimelineEvents() after the events are loaded.
     */
    const profile = state.selectedProfile || null;

    const query = profile
        ? `/api/events?profile=${encodeURIComponent(profile)}`
        : "/api/events";

    const response = await fetch(query);

    if (!response.ok) {
        throw new Error(`Events request failed: ${response.status}`);
    }

    const data = await response.json();

    return Array.isArray(data?.events)
        ? data.events
        : [];
}

async function getFilteredEvents() {
    const events = await fetchGlobalEvents();
    state.globalEvents = events;
    return filterTimelineEvents(events);
}


async function getGloballyFilteredGraph(graph) {
    if (!graph || !Array.isArray(graph.nodes)) {
        return graph;
    }

    const hasFilters =
        Boolean(state.globalFilter.search?.trim()) ||
        Boolean(state.globalFilter.dateFrom) ||
        Boolean(state.globalFilter.dateTo) ||
        (
            state.globalFilter.profileScope !== "all" &&
            Boolean(state.globalFilter.profileScope)
        );

    if (!hasFilters) {
        return graph;
    }

    const events = await getFilteredEvents();

    const matchingKeys = new Set(
        events.map(event => {
            const source = String(
                event?.source_profile || ""
            ).trim();

            const memoryId = String(
                event?.origin_memory_id || ""
            ).trim();

            return `${source}::${memoryId}`;
        })
    );

    const nodes = graph.nodes.filter(node => {
        const source = String(
            node?.source_profile || ""
        ).trim();

        const memoryId = String(
            node?.origin_memory_id || ""
        ).trim();

        return matchingKeys.has(`${source}::${memoryId}`);
    });

    const allowedGraphIds = new Set(
        nodes.map(node => node.graph_id)
    );

    const edges = {};

    for (const [sourceId, values] of Object.entries(
        graph.edges || {}
    )) {
        if (!allowedGraphIds.has(sourceId)) {
            continue;
        }

        const filteredEdges = Array.isArray(values)
            ? values.filter(edge =>
                allowedGraphIds.has(edge.target_id)
            )
            : [];

        if (filteredEdges.length) {
            edges[sourceId] = filteredEdges;
        }
    }

    return {
        ...graph,
        nodes,
        edges,
    };
}

function applyGlobalFilters() {
    setViewMode(state.viewMode);
}

function bindGlobalFilters() {
    const search = $("global-search");
    const from = $("global-date-from");
    const to = $("global-date-to");
    const profileScope = $("global-profile-scope");
    const clear = $("clear-filters-button");

    if (search) {
        search.value = state.globalFilter.search;

        search.addEventListener("input", event => {
            state.globalFilter.search = event.target.value;
            localStorage.setItem(
                "mnemosyne-global-search",
                state.globalFilter.search
            );
            applyGlobalFilters();
        });
    }

    if (from) {
        from.value = state.globalFilter.dateFrom;

        from.addEventListener("change", event => {
            state.globalFilter.dateFrom = event.target.value;
            localStorage.setItem(
                "mnemosyne-global-date-from",
                state.globalFilter.dateFrom
            );
            applyGlobalFilters();
        });
    }

    if (to) {
        to.value = state.globalFilter.dateTo;

        to.addEventListener("change", event => {
            state.globalFilter.dateTo = event.target.value;
            localStorage.setItem(
                "mnemosyne-global-date-to",
                state.globalFilter.dateTo
            );
            applyGlobalFilters();
        });
    }

    if (profileScope) {
        renderGlobalProfileFilter();

        profileScope.addEventListener("change", event => {
            const value = String(
                event.target.value || "all"
            ).trim();

            state.globalFilter.profileScope =
                value || "all";

            localStorage.setItem(
                "mnemosyne-global-profile-scope",
                state.globalFilter.profileScope
            );

            applyGlobalFilters();
        });
    }

    if (clear) {
        clear.addEventListener("click", () => {
            state.globalFilter.search = "";
            state.globalFilter.dateFrom = "";
            state.globalFilter.dateTo = "";
            state.globalFilter.profileScope = "all";

            localStorage.removeItem("mnemosyne-global-search");
            localStorage.removeItem("mnemosyne-global-date-from");
            localStorage.removeItem("mnemosyne-global-date-to");
            localStorage.removeItem("mnemosyne-global-profile-scope");

            if (search) search.value = "";
            if (from) from.value = "";
            if (to) to.value = "";
            if (profileScope) profileScope.value = "all";

            state.hybridResults = [];
            state.hybridSearchLoading = false;

            setViewMode(
                state.viewMode === "hybrid-search"
                    ? "2d"
                    : state.viewMode
            );
        });
    }
}


async function renderMainInformationView(mode, graph) {
    const container = $("graph-view");

    if (!container) {
        return;
    }

    if (!graph?.nodes?.length) {
        container.innerHTML =
            '<div class="loading-state">No graph data available.</div>';
        return;
    }

    const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];

    const promoted = nodes.filter(
        node => node.is_promoted || node.lifecycle_state === "promoted"
    ).length;

    const revoked = nodes.filter(
        node => node.is_revoked || node.lifecycle_state === "revoked"
    ).length;

    const validated = nodes.filter(
        node => node.validated_at
    ).length;

    const scored = nodes.filter(
        node =>
            node.validation_score !== null &&
            node.validation_score !== undefined
    );

    const averageScore = scored.length
        ? scored.reduce(
            (sum, node) => sum + Number(node.validation_score || 0),
            0,
        ) / scored.length
        : null;

    const profileCounts = new Map();

    for (const node of nodes) {
        const profile = String(
            node.source_profile || "Unknown"
        ).split(":").pop();

        profileCounts.set(
            profile,
            (profileCounts.get(profile) || 0) + 1,
        );
    }

    const profileRows = [...profileCounts.entries()]
        .sort((a, b) => b[1] - a[1])
        .map(
            ([profile, count]) => `
                <div class="tile-stat-row">
                    <span>${escapeHTML(profile)}</span>
                    <strong>${count.toLocaleString()}</strong>
                </div>
            `
        )
        .join("");

    if (mode === "profile-views") {
        container.innerHTML = `
            <div class="information-view">
                <h2>Profile Views</h2>
                <p class="control-help">
                    Memory distribution for the current profile selection.
                </p>

                <div class="tile-stat-grid">
                    <div>
                        <strong>${nodes.length.toLocaleString()}</strong>
                        <span>Memories</span>
                    </div>
                    <div>
                        <strong>${profileCounts.size}</strong>
                        <span>Profiles</span>
                    </div>
                </div>

                <section class="inspector-section">
                    <h3>Memory Distribution</h3>
                    ${profileRows || '<div class="empty-state">No profile data.</div>'}
                </section>
            </div>
        `;
        return;
    }

    if (mode === "activity") {
        container.innerHTML = `
            <div class="information-view">
                <h2>Activity</h2>

                <div class="tile-stat-grid">
                    <div>
                        <strong>${nodes.length.toLocaleString()}</strong>
                        <span>Total memories</span>
                    </div>
                    <div>
                        <strong>${validated.toLocaleString()}</strong>
                        <span>Validated</span>
                    </div>
                    <div>
                        <strong>${promoted.toLocaleString()}</strong>
                        <span>Promoted</span>
                    </div>
                    <div>
                        <strong>${revoked.toLocaleString()}</strong>
                        <span>Revoked</span>
                    </div>
                </div>
            </div>
        `;
        return;
    }

    if (mode === "status") {
        const pending = Math.max(
            0,
            nodes.length - promoted - revoked,
        );

        container.innerHTML = `
            <div class="information-view">
                <h2>Collective Status</h2>

                <div class="tile-stat-grid">
                    <div>
                        <strong>${nodes.length.toLocaleString()}</strong>
                        <span>Total memories</span>
                    </div>
                    <div>
                        <strong>${promoted.toLocaleString()}</strong>
                        <span>Promoted</span>
                    </div>
                    <div>
                        <strong>${pending.toLocaleString()}</strong>
                        <span>Pending</span>
                    </div>
                    <div>
                        <strong>${revoked.toLocaleString()}</strong>
                        <span>Revoked</span>
                    </div>
                </div>

                <div class="tile-status-message">
                    ${
                        revoked === 0 && pending === 0
                            ? "All memories in this view are promoted."
                            : "This view contains memories in multiple lifecycle states."
                    }
                </div>
            </div>
        `;
        return;
    }

    if (mode === "validation") {
        container.innerHTML = `
            <div class="information-view">
                <h2>Validation</h2>

                <div class="tile-stat-grid">
                    <div>
                        <strong>
                            ${averageScore === null
                                ? "—"
                                : averageScore.toFixed(2)}
                        </strong>
                        <span>Average score</span>
                    </div>
                    <div>
                        <strong>${validated.toLocaleString()}</strong>
                        <span>Validated</span>
                    </div>
                    <div>
                        <strong>${scored.length.toLocaleString()}</strong>
                        <span>Scored</span>
                    </div>
                </div>
            </div>
        `;
        return;
    }


}


function setViewMode(mode) {
    const validModes = [
        "2d",
        "3d",
        "table",
        "profile-views",
        "activity",
        "status",
        "validation",
        "entity-graph",
        "hybrid-search",
        "tiles",
    ];

    if (!validModes.includes(mode)) {
        mode = "2d";
    }

    const previousMode = state.viewMode;
    state.viewMode = mode;

    localStorage.setItem("mnemosyne-view-mode", mode);

    const selector = $("view-mode");

    if (selector) {
        selector.value = mode;
    }

    const graphModes = ["2d", "3d", "entity-graph"];

    const informationModes = [
        "profile-views",
        "activity",
        "status",
        "validation",
    ];

    $("graph-view").classList.toggle(
        "hidden",
        !graphModes.includes(mode) &&
        !informationModes.includes(mode),
    );

    $("table-view").classList.toggle(
        "hidden",
        mode !== "table",
    );

    $("tile-view").classList.toggle(
        "hidden",
        mode !== "tiles",
    );

    $("hybrid-search-view").classList.toggle(
        "hidden",
        mode !== "hybrid-search",
    );

    if (mode !== "hybrid-search") {
        state.hybridResults = [];
        state.hybridSearchLoading = false;

        const hybridView = $("hybrid-search-view");
        if (hybridView) {
            hybridView.innerHTML = "";
        }
    }

    if (previousMode === "3d" && mode !== "3d") {
        window.Mnemosyne3D?.destroy?.();
    }

    if (mode === "entity-graph") {
        if (state.entityGraphLoaded) {
            renderEntityGraph(
                state.entityGraph,
                !state.entityGraphViewInitialized,
            );
            return;
        }

        if (state.entityGraphLoading) {
            return;
        }

        state.entityGraphLoading = true;

        const container = $("graph-view");

        if (container) {
            container.innerHTML =
                '<div class="loading-state">Loading entity graph…</div>';
        }

        fetchEntityGraph()
            .then(graph => {
                state.entityGraph = {
                    nodes: Array.isArray(graph?.nodes)
                        ? graph.nodes
                        : [],
                    edges: Array.isArray(graph?.edges)
                        ? graph.edges
                        : [],
                };

                state.entityGraphLoaded = true;
                state.entityGraphLoading = false;

                if (state.viewMode === "entity-graph") {
                    renderEntityGraph(
                        state.entityGraph,
                        true,
                    );
                }
            })
            .catch(error => {
                state.entityGraphLoading = false;

                if (state.viewMode === "entity-graph") {
                    const container = $("graph-view");

                    if (container) {
                        container.innerHTML =
                            '<div class="loading-state">Unable to load entity graph.</div>';
                    }

                    setStatus(
                        `Entity graph error: ${error.message}`,
                        true,
                    );
                }
            });

        return;
    }

    if (mode === "hybrid-search") {
        renderHybridSearch();
        return;
    }

    if (mode === "tiles") {
        renderTileView();
        return;
    }

    const hasFilters =
        Boolean(state.globalFilter.search?.trim()) ||
        Boolean(state.globalFilter.dateFrom) ||
        Boolean(state.globalFilter.dateTo) ||
        (
            state.globalFilter.profileScope !== "all" &&
            Boolean(state.globalFilter.profileScope)
        );

    if (!hasFilters) {
        switch (mode) {
            case "2d":
                renderGraph2D(state.graph);
                break;

            case "3d":
                renderGraph3D(state.graph);
                break;

            case "table":
                renderTable(state.graph);
                break;

            case "profile-views":
            case "activity":
            case "status":
            case "validation":
                renderMainInformationView(
                    mode,
                    state.graph
                );
                break;

            default:
                renderGraph2D(state.graph);
                break;
        }

        return;
    }

    setStatus("Applying global filters…");

    getGloballyFilteredGraph(state.graph)
        .then(filteredGraph => {
            switch (mode) {
                case "2d":
                    renderGraph2D(filteredGraph);
                    break;

                case "3d":
                    renderGraph3D(filteredGraph);
                    break;

                case "table":
                    renderTable(filteredGraph);
                    break;

                case "profile-views":
                case "activity":
                case "status":
                case "validation":
                    renderMainInformationView(
                        mode,
                        filteredGraph
                    );
                    break;

                default:
                    renderGraph2D(filteredGraph);
                    break;
            }

            setStatus(
                `Filtered view: ${filteredGraph.nodes.length.toLocaleString()} memories`
            );
        })
        .catch(error => {
            console.error(
                "Global filter rendering error:",
                error
            );

            setStatus(
                `Unable to apply global filters: ${error.message}`
            );
        });
}


function fit2DGraphToViewport(positions, width, height) {
    if (!positions || positions.size === 0) {
        state.zoom = 1;
        state.panX = 0;
        state.panY = 0;
        return;
    }

    const padding = 50;
    const points = Array.from(positions.values());

    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;

    for (const point of points) {
        minX = Math.min(minX, point.x);
        maxX = Math.max(maxX, point.x);
        minY = Math.min(minY, point.y);
        maxY = Math.max(maxY, point.y);
    }

    const graphWidth = Math.max(maxX - minX, 1);
    const graphHeight = Math.max(maxY - minY, 1);

    const availableWidth = Math.max(width - padding * 2, 1);
    const availableHeight = Math.max(height - padding * 2, 1);

    state.zoom = Math.min(
        availableWidth / graphWidth,
        availableHeight / graphHeight,
        1,
    );

    const graphCenterX = (minX + maxX) / 2;
    const graphCenterY = (minY + maxY) / 2;

    state.panX = width / 2 - graphCenterX * state.zoom;
    state.panY = height / 2 - graphCenterY * state.zoom;
}

function applyTransform() {
    const viewport = document.querySelector(".graph-viewport");
    if(viewport) viewport.setAttribute(
        "transform",`translate(${state.panX} ${state.panY}) scale(${state.zoom})`
    );
}

function resetGraphView() {
    state.zoom = 1;
    state.panX = 0;
    state.panY = 0;
    state.dragging = false;

    if (state.viewMode === "2d") {
        renderGraph2D(state.graph);
    } else if (state.viewMode === "3d") {
        window.Mnemosyne3D?.reset?.();
    } else if (state.viewMode === "entity-graph") {
        state.entityGraphViewInitialized = false;
        renderEntityGraph(
            state.entityGraph,
            true,
        );
    }
}

async function selectProfile(profile){
    state.selectedProfile=profile; state.selectedNode=null; resetGraphView();
    renderProfiles(state.profiles);
    $("workspace-subtitle").textContent=profile ? `Profile: ${profile}` : "All profiles";
    setSelectionStatus("");
    try{
        setStatus(profile ? `Loading ${profile} graph…` : "Loading collective graph…");
        state.graph=await fetchGraph(profile); renderStatistics();
        tileEventCache.clear();
        setViewMode(state.viewMode);
        setStatus(`Loaded ${state.graph.nodes.length} nodes and ${countEdges(state.graph.edges)} edges.`);
    }catch(error){showError(error);}
}

function renderAgents(payload){
    state.agents=(payload.agents || []).map(agent => ({
        ...agent,
        base_url: agent.base_url || (
            agent.address
                ? `http://${agent.address}:${agent.api_port || 8000}`
                : ""
        ),
    }));
    state.scanning=Boolean(payload.scanning);
    state.agentMap=new Map(state.agents.map(a=>[a.client_id,a]));

    // Identify the local Hermes agent from the discovery hostname.
    // The browser may use 127.0.0.1 while discovery advertises the LAN address.
    const localHostname=window.location.hostname;
    const matchingHostname=state.agents.find(agent =>
        agent.hostname === localHostname
    );
    const discoveredLocal=matchingHostname || state.agents.find(agent =>
        agent.hostname === "loki-tux"
    );
    state.localAgentId=discoveredLocal?.client_id || null;
    $("discovery-summary").textContent =
        `${state.agents.length} discovered · ${state.agents.filter(a=>a.state==="ADOPTED").length} adopted` +
        (state.scanning ? " · scanning…" : "");
    $("scan-lan-button").disabled=state.scanning;
    $("stop-scan-button").disabled=!state.scanning;

    const list=$("agent-list"); list.innerHTML="";
    if(!state.agents.length){
        list.innerHTML='<div class="empty-state">No discovered agents. Click Scan LAN.</div>'; return;
    }
    for(const agent of state.agents){
        const card=document.createElement("div");
        card.className=`agent-card${agent.state==="ADOPTED"?" adopted":""}`;
        const head=document.createElement("div"); head.className="agent-head";
        const name=document.createElement("span"); name.className="agent-name"; name.textContent=agent.hostname || agent.client_id;
        const stateText=document.createElement("span"); stateText.textContent=agent.state;
        if(agent.state==="ADOPTED") stateText.className="adopted-label";
        head.append(name,stateText);
        const meta=document.createElement("div"); meta.className="agent-meta";
        meta.textContent=`${agent.address || "address unavailable"}:${agent.api_port || 8000} · ${agent.installed_version || "unknown version"}`;
        const actions=document.createElement("div"); actions.className="agent-actions";
        if(agent.state!=="ADOPTED"){
            const adopt=document.createElement("button"); adopt.type="button"; adopt.textContent="Adopt";
            adopt.addEventListener("click",()=>adoptAgent(agent.client_id)); actions.appendChild(adopt);
        }else{
            const label=document.createElement("span"); label.className="adopted-label"; label.textContent="Available for rebuild";
            actions.appendChild(label);
        }
        card.append(head,meta,actions); list.appendChild(card);
    }
}

async function refreshDiscovery(){
    try{renderAgents(await fetchAgents());}
    catch(error){setStatus(`Discovery error: ${error.message}`,true);}
}

async function scanLAN(){
    try{
        setStatus("Starting LAN discovery…");
        const payload=await postJSON("/api/discovery/scan/start");
        renderAgents(payload);
        if(state.scanning){
            let polls=0;
            const timer=setInterval(async()=>{
                polls++;
                await refreshDiscovery();
                if(!state.scanning || polls>=12) clearInterval(timer);
            },1000);
        }
        setStatus("LAN discovery active.");
    }catch(error){showError(error);}
}

async function stopScan(){
    try{
        const payload=await postJSON("/api/discovery/scan/stop");
        renderAgents(payload); setStatus("LAN discovery stopped.");
    }catch(error){showError(error);}
}

async function adoptAgent(clientId){
    try{
        setStatus("Adopting agent…");
        const payload=await postJSON(`/api/discovery/${encodeURIComponent(clientId)}/adopt`);
        const existing=state.agents.find(a=>a.client_id===clientId);
        if(existing) Object.assign(existing,payload.agent);
        state.agentMap.set(clientId,payload.agent);
        renderAgents({agents:state.agents,scanning:state.scanning});
        setStatus(payload.adopted ? `Adopted ${payload.agent.hostname}.` : `${payload.agent.hostname} was already adopted.`);
    }catch(error){showError(error);}
}

async function nukeCollective(){
    if(!window.confirm(
        "NUKE COLLECTIVE\n\n" +
        "This removes the current collective reconstruction and resets LAN adoption state.\n\n" +
        "Source Hermes profiles and memories will NOT be deleted.\n\n" +
        "Continue?"
    )) return;

    try{
        setStatus("Nuking collective…");
        setOperationStatus("Removing collective reconstruction and resetting agent adoption…");

        const result=await postJSON("/api/admin/collective/nuke");

        // Clear all collective-derived browser state.
        // The underlying Hermes source profiles/memories remain untouched.
        state.graph={nodes:[],edges:{}};
        state.profiles=[];
        state.selectedProfile=null;
        state.selectedNode=null;

        renderProfiles([]);
        renderStatistics({
            profiles:0,
            memories:0,
            nodes:0,
            edges:0
        });

        if(state.viewMode==="table"){
            renderTable(state.graph);
        }else{
            tileEventCache.clear();
        setViewMode(state.viewMode);
        }

        $("inspector-content").innerHTML=
            '<div class="empty-state">' +
            '<strong>Collective nuked</strong>' +
            '<p>Source profiles and memories remain intact. Scan LAN and adopt an agent to rebuild.</p>' +
            '</div>';

        if(result.discovery){
            renderAgents(result.discovery);
        }else{
            await refreshDiscovery();
        }

        setOperationStatus(
            `Nuked ${result.entries_removed || 0} collective references. ` +
            `Source profiles and memories remain available for rebuild.`,
            true
        );

        setStatus("Collective nuked. Source data preserved; LAN agents reset to discovered state.");

    }catch(error){
        showOperationError(error);
    }
}

async function scanNewMemories(){
    const adopted=state.agents.filter(a=>a.state==="ADOPTED");

    if(!adopted.length){
        showOperationError(
            new Error(
                "No adopted LAN agents. Scan the LAN and adopt at least one agent first."
            )
        );
        return;
    }

    try{
        setStatus("Scanning adopted agents for new memories…");
        setOperationStatus(
            "Incremental scan: checking adopted agents for new memories…"
        );

        $("scan-memories-button").disabled=true;
        $("rebuild-button").disabled=true;
        $("nuke-button").disabled=true;

        const result=await postJSON("/api/admin/collective/scan");

        const embeddingFailures=Array.isArray(result.embedding_failures)
            ? result.embedding_failures.length
            : Number(result.embedding_failures || 0);

        const collective=result.collective || {};
        const embedded=Number(collective.embedded || 0);
        const totalEntries=Number(collective.total_entries || 0);
        const newMemories=Number(result.memories_new || 0);
        const failures=Array.isArray(result.failures)
            ? result.failures.length
            : 0;

        setOperationStatus(
            `Scan complete: ${result.memories_discovered || 0} memories checked, ` +
            `${newMemories} new memories imported, ` +
            `${embedded}/${totalEntries} embeddings available, ` +
            `${embeddingFailures} embedding failures, ` +
            `${failures} scan failures.`,
            Boolean(result.success) &&
            embeddingFailures === 0 &&
            failures === 0
        );

        if(newMemories > 0){
            state.profiles=await fetchProfiles();
            renderProfiles(state.profiles);

            state.graph=await fetchGraph(state.selectedProfile);

            renderStatistics(await fetchDiagnostics());

            if(state.viewMode==="table"){
                renderTable(state.graph);
            }else{
                tileEventCache.clear();
        setViewMode(state.viewMode);
            }
        }else{
            renderStatistics(await fetchDiagnostics());
        }

        await refreshDiscovery();

        setStatus(
            `Scan complete — ${newMemories} new memories imported, ` +
            `${state.graph.nodes.length} nodes, ` +
            `${countEdges(state.graph.edges)} edges.`
        );

    }catch(error){
        showOperationError(error);
    }finally{
        $("scan-memories-button").disabled=false;
        $("rebuild-button").disabled=false;
        $("nuke-button").disabled=false;
    }
}

async function rebuildCollective(){
    const adopted=state.agents.filter(a=>a.state==="ADOPTED");
    if(!adopted.length){
        showOperationError(
            new Error(
                "No adopted LAN agents. Scan the LAN and adopt at least one agent first."
            )
        );
        return;
    }

    try{
        setStatus("Rebuilding from adopted LAN agents…");
        setOperationStatus(
            "Rebuild: contacting adopted agents and collecting memory references…"
        );

        $("rebuild-button").disabled=true;
        $("nuke-button").disabled=true;

        const result=await postJSON("/api/admin/collective/rebuild");

        const embeddingFailures=Array.isArray(result.embedding_failures)
            ? result.embedding_failures.length
            : Number(result.embedding_failures || 0);

        const collective=result.collective || {};
        const embedded=Number(collective.embedded || 0);
        const totalEntries=Number(collective.total_entries || 0);

        setOperationStatus(
            `Rebuild complete: ${result.memories_discovered || 0} memories discovered, ` +
            `${result.entries_created || 0} references created, ` +
            `${embedded}/${totalEntries} embeddings generated, ` +
            `${embeddingFailures} embedding failures.`,
            Boolean(result.success) && embeddingFailures === 0
        );

        state.profiles=await fetchProfiles();
        renderProfiles(state.profiles);

        await refreshDiscovery();

        state.graph=await fetchGraph(state.selectedProfile);

        renderStatistics(await fetchDiagnostics());

        if(state.viewMode==="table"){
            renderTable(state.graph);
        }else{
            tileEventCache.clear();
        setViewMode(state.viewMode);
        }

        setStatus(
            `Rebuild complete — ${state.graph.nodes.length} nodes, ` +
            `${countEdges(state.graph.edges)} edges.`
        );

    }catch(error){
        showOperationError(error);
    }finally{
        $("rebuild-button").disabled=false;
        $("nuke-button").disabled=false;
    }
}

function setOperationStatus(message,success=false){
    const el=$("operation-status"); el.className=`operation-status${success?" success":""}`; el.textContent=message;
}
function showOperationError(error){
    console.error(error); setOperationStatus(error.message || String(error),false);
    setStatus(`Operation failed: ${error.message || String(error)}`,true);
}

async function refresh(){
    try{
        setStatus("Refreshing…");
        state.profiles=await fetchProfiles(); renderProfiles(state.profiles); initTiles(state.profiles);
        renderColourControls();
        await loadHermesRuntime();
        const diagnostics=await fetchDiagnostics(); renderStatistics(diagnostics);
        state.graph=await fetchGraph(state.selectedProfile);
        tileEventCache.clear();
        setViewMode(state.viewMode);
        await refreshDiscovery();
        setStatus(`Ready — ${state.graph.nodes.length} nodes, ${countEdges(state.graph.edges)} edges.`);
    }catch(error){showError(error);}
}

function showError(error){
    console.error(error); setStatus(`Error: ${error.message || String(error)}`,true);
    const graphView=$("graph-view");
    if(graphView) graphView.innerHTML=`<div class="error-state">Unable to load Browser data.<br>${escapeHTML(error.message || String(error))}</div>`;
}

function renderStatistics(diagnostics = null) {
    const profiles = diagnostics?.profiles;
    const graph = diagnostics?.graph;

    const profileCount = Array.isArray(profiles)
        ? profiles.length
        : Number(
            diagnostics?.profiles ??
            state.profiles.length
        );

    const memoryCount = Array.isArray(profiles)
        ? profiles.reduce(
            (sum, profile) => sum + Number(profile.memory_count || 0),
            0,
        )
        : Number(
            diagnostics?.memories ??
            diagnostics?.memory_count ??
            state.profiles.reduce(
                (sum, profile) => sum + Number(profile.memory_count || 0),
                0,
            )
        );

    const nodeCount = Number(
        graph?.nodes ??
        diagnostics?.nodes ??
        state.graph.nodes.length
    );

    const edgeCount = Number(
        graph?.edges ??
        diagnostics?.edges ??
        countEdges(state.graph.edges)
    );

    const profilesElement = $("stat-profiles");
    const memoriesElement = $("stat-memories");
    const nodesElement = $("stat-nodes");
    const edgesElement = $("stat-edges");

    if (profilesElement) {
        profilesElement.textContent = Number.isFinite(profileCount)
            ? profileCount.toLocaleString()
            : "—";
    }

    if (memoriesElement) {
        memoriesElement.textContent = Number.isFinite(memoryCount)
            ? memoryCount.toLocaleString()
            : "—";
    }

    if (nodesElement) {
        nodesElement.textContent = Number.isFinite(nodeCount)
            ? nodeCount.toLocaleString()
            : "—";
    }

    if (edgesElement) {
        edgesElement.textContent = Number.isFinite(edgeCount)
            ? edgeCount.toLocaleString()
            : "—";
    }
}

function formatScore(value){
    if(value===null || value===undefined) return "—";
    const number=Number(value); return Number.isFinite(number) ? number.toFixed(3) : "—";
}
function escapeHTML(value){
    return String(value ?? "—").replaceAll("&","&amp;").replaceAll("<","&lt;")
        .replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
}

function renderColourControls() {
    const container = $("profile-colour-controls");
    if (!container) return;

    container.innerHTML = "";

    for (const profile of state.profiles) {
        const row = document.createElement("div");
        row.className = "profile-colour-row";

        const label = document.createElement("label");
        label.textContent = profile.name;
        label.htmlFor = `profile-colour-${profile.id}`;

        const input = document.createElement("input");
        input.type = "color";
        input.id = `profile-colour-${profile.id}`;
        input.value = colorForProfile(profile.id);
        input.title = `Colour for ${profile.name}`;

        input.addEventListener("input", () => {
            profileColours[profileLabel(profile.id)] = input.value;
            saveProfileColours();
            renderProfiles(state.profiles);

            if (state.viewMode === "2d") {
                renderGraph2D(state.graph);
            } else if (state.viewMode === "3d") {
                renderGraph3D(state.graph);
            }
        });

        row.append(label, input);
        container.appendChild(row);
    }
}

function resetProfileColours() {
    localStorage.removeItem(COLOR_STORAGE_KEY);

    for (const key of Object.keys(profileColours)) {
        delete profileColours[key];
    }

    renderColourControls();
    renderProfiles(state.profiles);

    if (state.viewMode === "2d") {
        renderGraph2D(state.graph);
    } else if (state.viewMode === "3d") {
        renderGraph3D(state.graph);
    }

    setStatus("Profile colours reset to defaults.");
}

function loadGlobalFilters() {
    state.globalFilter.search =
        localStorage.getItem("mnemosyne-global-search") || "";

    state.globalFilter.dateFrom =
        localStorage.getItem("mnemosyne-global-date-from") || "";

    state.globalFilter.dateTo =
        localStorage.getItem("mnemosyne-global-date-to") || "";

    const storedProfileScope =
        localStorage.getItem("mnemosyne-global-profile-scope");

    state.globalFilter.profileScope =
        storedProfileScope &&
        storedProfileScope !== "selected"
            ? storedProfileScope
            : "all";
}


function bindControls(){
    bindGlobalFilters();

    $("view-mode").addEventListener("change",e=>setViewMode(e.target.value));

    const informationView = $("information-view");
    if (informationView) {
        informationView.addEventListener(
            "change",
            e => setInformationView(e.target.value)
        );
    }
    $("reset-colours-button").addEventListener("click",resetProfileColours);
    $("edge-limit").addEventListener("change",async e=>{
        state.edgeLimit=e.target.value===""?null:Number(e.target.value);
        await selectProfile(state.selectedProfile);
    });
    $("zoom-in").addEventListener("click",()=>{
        if(window.Mnemosyne3D?.zoomIn){
            window.Mnemosyne3D.zoomIn();
            return;
        }
        state.zoom=Math.min(8,state.zoom*1.25);
        applyTransform();
    });
    $("zoom-out").addEventListener("click",()=>{
        if(window.Mnemosyne3D?.zoomOut){
            window.Mnemosyne3D.zoomOut();
            return;
        }
        state.zoom=Math.max(.2,state.zoom*.8);
        applyTransform();
    });
    $("zoom-reset").addEventListener("click",resetGraphView);
    $("scan-lan-button").addEventListener("click",scanLAN);
    $("stop-scan-button").addEventListener("click",stopScan);
    $("scan-memories-button").addEventListener("click",scanNewMemories);
    $("rebuild-button").addEventListener("click",rebuildCollective);
    $("nuke-button").addEventListener("click",nukeCollective);
    $("hybrid-search-button").addEventListener("click",runHybridSearch);
}

async function init(){
    loadGlobalFilters();
    bindControls();

    const savedViewMode = localStorage.getItem("mnemosyne-view-mode");
    if ([
        "2d",
        "3d",
        "table",
        "profile-views",
        "activity",
        "status",
        "validation",
        "hybrid-search",
        "tiles",
    ].includes(savedViewMode)) {
        state.viewMode = savedViewMode;
        $("view-mode").value = savedViewMode;
    }

    const savedInformationView =
        localStorage.getItem("mnemosyne-information-view");

    if (INFORMATION_VIEW_TYPES.some(
        type => type.id === savedInformationView
    )) {
        state.informationView = savedInformationView;
    }

    const informationView = $("information-view");
    if (informationView) {
        informationView.value = state.informationView;
    }

    try{
        setStatus("Loading profiles…");
        state.profiles=await fetchProfiles(); renderProfiles(state.profiles); initTiles(state.profiles);
        renderColourControls();
        await loadHermesRuntime();
        const diagnostics=await fetchDiagnostics(); renderStatistics(diagnostics);
        await refreshDiscovery();
        state.graph=await fetchGraph(state.selectedProfile);
        renderStatistics(diagnostics);
        tileEventCache.clear();
        setViewMode(state.viewMode);
        setStatus(`Ready — ${state.graph.nodes.length} nodes, ${countEdges(state.graph.edges)} edges.`);
    }catch(error){showError(error);}
}

window.addEventListener("DOMContentLoaded",init);
