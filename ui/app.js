const API_BASE = "http://127.0.0.1:8000";

function updateStatus(message = "", isError = false) {
    const status = document.getElementById("status");
    status.textContent = message;
    status.classList.toggle("error", isError);
}

async function fetchProfiles() {
    try {
        const resp = await fetch(`${API_BASE}/api/profiles`);

        if (!resp.ok) {
            throw new Error(`Profile API error ${resp.status}`);
        }

        const data = await resp.json();
        const sel = document.getElementById("profileSelect");

        sel.innerHTML = "";

        const allOpt = document.createElement("option");
        allOpt.textContent = "All";
        allOpt.value = "";
        sel.appendChild(allOpt);

        for (const profile of data) {
            const opt = document.createElement("option");
            opt.value = profile.id;
            opt.textContent = profile.name;
            sel.appendChild(opt);
        }
    } catch (err) {
        updateStatus(`Unable to load profiles: ${err.message}`, true);
    }
}

async function fetchGraph() {
    try {
        const profile = document.getElementById("profileSelect").value;
        const edgeLimit = document.getElementById("edgeLimitInput").value;

        const params = new URLSearchParams();

        if (profile) {
            params.set("source_profile", profile);
        }

        if (edgeLimit !== "") {
            params.set("edge_limit", edgeLimit);
        }

        const query = params.toString();
        const url = `${API_BASE}/api/graph${query ? `?${query}` : ""}`;

        const resp = await fetch(url);

        if (!resp.ok) {
            throw new Error(`Graph API error ${resp.status}`);
        }

        const graph = await resp.json();
        renderGraph(graph);
        updateStatus(
            `${graph.nodes.length} nodes, ${Object.values(graph.edges).flat().length} edges`
        );
    } catch (err) {
        updateStatus(`Unable to load graph: ${err.message}`, true);
    }
}

function renderGraph(graph) {
    const svg = d3.select("#graph");
    svg.selectAll("*").remove();

    const width = svg.node().clientWidth;
    const height = svg.node().clientHeight;

    const nodes = graph.nodes || [];
    const edges = Object.values(graph.edges || {}).flat();

    const nodeById = new Map(nodes.map(node => [node.graph_id, node]));

    const links = edges
        .filter(edge =>
            nodeById.has(edge.source_id) &&
            nodeById.has(edge.target_id)
        )
        .map(edge => ({
            source: edge.source_id,
            target: edge.target_id,
            similarity_score: edge.similarity_score
        }));

    const profileColors = {
        athena: "#4dabf7",
        boss: "#ff922b",
        friday: "#b197fc",
        hawk: "#51cf66",
        jeeves: "#22b8cf",
        pope: "#ff6b6b"
    };

    function nodeColor(node) {
        return profileColors[node.source_profile.toLowerCase()] || "#ced4da";
    }

    const simulation = d3.forceSimulation(nodes)
        .force(
            "link",
            d3.forceLink(links)
                .id(node => node.graph_id)
                .distance(140)
                .strength(0.7)
        )
        .force("charge", d3.forceManyBody().strength(-350))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(32));

    const link = svg.append("g")
        .attr("class", "links")
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke-width", edge => 1 + edge.similarity_score * 3)
        .attr("stroke-opacity", edge => 0.25 + edge.similarity_score * 0.65);

    const node = svg.append("g")
        .attr("class", "nodes")
        .selectAll("circle")
        .data(nodes)
        .join("circle")
        .attr("r", 14)
        .attr("fill", nodeColor)
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
        .style("filter", item =>
            `drop-shadow(0 0 6px ${nodeColor(item)})`
        )
        .call(
            d3.drag()
                .on("start", dragStarted)
                .on("drag", dragged)
                .on("end", dragEnded)
        );

    node.append("title")
        .text(item =>
            `${item.source_profile}: ${item.origin_memory_id}`
        );

    const labels = svg.append("g")
        .attr("class", "labels")
        .selectAll("text")
        .data(nodes)
        .join("text")
        .attr("class", "node-label")
        .text(item => item.source_profile);

    simulation.on("tick", () => {
        link
            .attr("x1", linkDatum => linkDatum.source.x)
            .attr("y1", linkDatum => linkDatum.source.y)
            .attr("x2", linkDatum => linkDatum.target.x)
            .attr("y2", linkDatum => linkDatum.target.y);

        node
            .attr("cx", nodeDatum => nodeDatum.x)
            .attr("cy", nodeDatum => nodeDatum.y);

        labels
            .attr("x", nodeDatum => nodeDatum.x)
            .attr("y", nodeDatum => nodeDatum.y - 24);
    });

    function dragStarted(event, d) {
        if (!event.active) {
            simulation.alphaTarget(0.3).restart();
        }

        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragEnded(event, d) {
        if (!event.active) {
            simulation.alphaTarget(0);
        }

        d.fx = null;
        d.fy = null;
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    await fetchProfiles();
    await fetchGraph();

    document
        .getElementById("profileSelect")
        .addEventListener("change", fetchGraph);

    document
        .getElementById("edgeLimitInput")
        .addEventListener("change", fetchGraph);
});
