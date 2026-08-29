const API_BASE = "http://127.0.0.1:8000";

let graphInstance = null;
let currentGraphData = {
    nodes: [],
    links: [],
};

let autoRotate = false;

const PROFILE_COLORS = {
    athena: "#4dabf7",
    boss: "#ff922b",
    friday: "#b197fc",
    hawk: "#51cf66",
    jeeves: "#22b8cf",
    pope: "#ff6b6b",
    horus: "#f59f00",
    odin: "#845ef7",
    thoth: "#20c997",
    vulcan: "#fa5252",
};

function updateStatus(message = "", isError = false) {
    const status = document.getElementById("status");

    if (!status) {
        return;
    }

    status.textContent = message;
    status.classList.toggle("error", isError);
}

function nodeColor(node) {
    const profile = String(node.source_profile || "").toLowerCase();

    return PROFILE_COLORS[profile] || "#ced4da";
}

function nodeLabel(node) {
    const profile = node.source_profile || "unknown";
    const memoryId = node.origin_memory_id || node.graph_id || "";

    return `${profile}\n${memoryId}`;
}

function deduplicateEdges(edges) {
    const seen = new Set();
    const result = [];

    for (const edge of edges) {
        const source = edge.source_id;
        const target = edge.target_id;

        if (!source || !target || source === target) {
            continue;
        }

        const key = source < target
            ? `${source}\u0000${target}`
            : `${target}\u0000${source}`;

        if (seen.has(key)) {
            continue;
        }

        seen.add(key);

        result.push({
            source,
            target,
            similarity_score: Number(edge.similarity_score) || 0,
        });
    }

    return result;
}

async function fetchProfiles() {
    try {
        const response = await fetch(`${API_BASE}/api/profiles`);

        if (!response.ok) {
            throw new Error(`Profile API error ${response.status}`);
        }

        const profiles = await response.json();
        const select = document.getElementById("profileSelect");

        select.innerHTML = "";

        const allOption = document.createElement("option");
        allOption.value = "";
        allOption.textContent = "All";
        select.appendChild(allOption);

        for (const profile of profiles) {
            const option = document.createElement("option");

            option.value = profile.id;
            option.textContent = profile.name;

            select.appendChild(option);
        }
    } catch (error) {
        updateStatus(
            `Unable to load profiles: ${error.message}`,
            true
        );
    }
}

async function fetchGraph() {
    try {
        const profile = document.getElementById("profileSelect").value;
        const edgeLimit = document
            .getElementById("edgeLimitInput")
            .value
            .trim();

        const params = new URLSearchParams();

        if (profile) {
            params.set("source_profile", profile);
        }

        if (edgeLimit !== "") {
            const parsedLimit = Number.parseInt(edgeLimit, 10);

            if (!Number.isNaN(parsedLimit) && parsedLimit >= 0) {
                params.set("edge_limit", parsedLimit);
            }
        }

        const query = params.toString();

        const url =
            `${API_BASE}/api/graph` +
            (query ? `?${query}` : "");

        updateStatus("Loading constellation...");

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`Graph API error ${response.status}`);
        }

        const graph = await response.json();

        renderGraph(graph);
    } catch (error) {
        updateStatus(
            `Unable to load graph: ${error.message}`,
            true
        );
    }
}

function renderGraph(graph) {
    const container = document.getElementById("graph");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    const nodes = (graph.nodes || []).map(node => ({
        ...node,
    }));

    const allEdges = Object
        .values(graph.edges || {})
        .flat();

    const nodeIds = new Set(
        nodes.map(node => node.graph_id)
    );

    const links = deduplicateEdges(allEdges)
        .filter(edge =>
            nodeIds.has(edge.source) &&
            nodeIds.has(edge.target)
        );

    currentGraphData = {
        nodes,
        links,
    };

    graphInstance = ForceGraph3D()(container)
        .backgroundColor("#080b12")
        .showNavInfo(false)

        .nodeId("graph_id")

        .nodeVal(() => 4)

        .nodeColor(nodeColor)

        .nodeLabel(nodeLabel)

        .nodeOpacity(0.95)

        .nodeResolution(12)

        .linkSource("source")

        .linkTarget("target")

        .linkColor(() => "#718096")

        .linkOpacity(link =>
            0.25 + Math.max(
                0,
                Number(link.similarity_score) || 0
            ) * 0.65
        )

        .linkWidth(link =>
            0.5 +
            Math.max(
                0,
                Number(link.similarity_score) || 0
            ) * 2.5
        )

        .linkDirectionalParticles(link =>
            Number(link.similarity_score) >= 0.85 ? 2 : 0
        )

        .linkDirectionalParticleWidth(1.5)

        .linkDirectionalParticleSpeed(0.004)

        .graphData(currentGraphData)

        .onNodeClick(node => {
            updateStatus(
                `${node.source_profile || "unknown"} — ` +
                `${node.origin_memory_id || node.graph_id}`
            );

            graphInstance.cameraPosition(
                {
                    x: node.x * 1.6,
                    y: node.y * 1.6,
                    z: node.z * 1.6,
                },
                node,
                800
            );
        })

        .onBackgroundClick(() => {
            updateStatus(
                `${currentGraphData.nodes.length} nodes, ` +
                `${currentGraphData.links.length} unique similarity links`
            );
        });

    /*
     * Keep the force simulation spread out enough for a large graph.
     */
    graphInstance.d3Force(
        "charge"
    ).strength(-80);

    graphInstance.d3Force(
        "link"
    ).distance(45);

    /*
     * Give the renderer a little time to settle before fitting.
     */
    setTimeout(() => {
        fitGraph();
    }, 1200);

    updateStatus(
        `${nodes.length} nodes, ` +
        `${links.length} unique similarity links`
    );
}

function fitGraph() {
    if (!graphInstance || !currentGraphData.nodes.length) {
        return;
    }

    graphInstance.zoomToFit(
        1000,
        80
    );
}

function resetView() {
    if (!graphInstance) {
        return;
    }

    graphInstance.cameraPosition(
        {
            x: 0,
            y: 0,
            z: 1000,
        },
        {
            x: 0,
            y: 0,
            z: 0,
        },
        1000
    );

    setTimeout(() => {
        fitGraph();
    }, 1100);
}

function toggleAutoRotate() {
    if (!graphInstance) {
        return;
    }

    autoRotate = !autoRotate;

    graphInstance.controls().autoRotate = autoRotate;
    graphInstance.controls().autoRotateSpeed = 0.5;

    const button = document.getElementById("rotateButton");

    if (button) {
        button.textContent =
            autoRotate
                ? "Stop Rotation"
                : "Auto Rotate";
    }
}

window.addEventListener("resize", () => {
    if (!graphInstance) {
        return;
    }

    const container = document.getElementById("graph");

    if (!container) {
        return;
    }

    graphInstance
        .width(container.clientWidth)
        .height(container.clientHeight);
});

document.addEventListener(
    "DOMContentLoaded",
    async () => {
        document
            .getElementById("profileSelect")
            .addEventListener(
                "change",
                fetchGraph
            );

        document
            .getElementById("edgeLimitInput")
            .addEventListener(
                "change",
                fetchGraph
            );

        document
            .getElementById("fitButton")
            .addEventListener(
                "click",
                fitGraph
            );

        document
            .getElementById("resetButton")
            .addEventListener(
                "click",
                resetView
            );

        document
            .getElementById("rotateButton")
            .addEventListener(
                "click",
                toggleAutoRotate
            );

        await fetchProfiles();
        await fetchGraph();
    }
);

/* --------------------------------------------------------------------- */
/*  LAN Discovery UI – uses the new /api/discovery endpoints  */
/* --------------------------------------------------------------------- */

async function fetchDiscovery() {
    try {
        const response = await fetch(`${API_BASE}/api/discovery`);
        if (!response.ok) throw new Error(`Network error ${response.status}`);
        const data = await response.json();
        renderDiscoveryList(data.agents || []);
    } catch (e) {
        updateStatus(`Failed to load discovery: ${e.message}`, true);
    }
}

async function scanDiscovery() {
    updateStatus("Scanning local network…");
    try {
        const response = await fetch(`${API_BASE}/api/discovery/scan`, {
            method: "POST",
        });
        if (!response.ok) throw new Error(`Scan failed ${response.status}`);
        const data = await response.json();
        renderDiscoveryList(data.agents || []);
    } catch (e) {
        updateStatus(`Scan error: ${e.message}`, true);
    }
}

function renderDiscoveryList(agents) {
    const container = document.getElementById("discoveryList");
    if (!container) return;
    let html = `<h3>REMOTE AGENTS</h3>`;
    if (agents.length === 0) {
        html += `<p>No agents found.</p>`;
    } else {
        html += `<p>Scan complete — ${agents.length} agent${agents.length > 1 ? "s" : ""} found</p>`;
        for (const a of agents) {
            const dt = new Date();
            html += `\n<div class="agent-item">`;
            html += `<strong>${a.hostname}</strong><br/>`;
            html += `Host: ${a.hostname}<br/>`; // duplicate but fine
            html += `Version: ${a.installed_version || "N/A"}<br/>`;
            html += `Client ID: ${a.client_id}\n`;
            html += `Last seen: ${new Date(a.last_seen).toLocaleString()}<br/>
        </div>`;
        }
    }
    container.innerHTML = html;
}

document.getElementById("scanButton").addEventListener("click", scanDiscovery);
