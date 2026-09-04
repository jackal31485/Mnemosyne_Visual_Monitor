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
    selectedNode: null,
    viewMode: "graph",
    edgeLimit: 5,
    zoom: 1, panX: 0, panY: 0,
    dragging: false,
    dragStartX: 0, dragStartY: 0, panStartX: 0, panStartY: 0,
    agents: [],
    scanning: false,
    agentMap: new Map(),
    localAgentId: null,
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
    return data.map((entry) => Array.isArray(entry)
        ? {id: entry[0], name: entry[1], memory_count: entry[2]}
        : {id: entry.id, name: entry.name, memory_count: entry.memory_count});
}

async function fetchProfiles() {
    return normalizeProfiles(await fetchJSON("/profiles/"));
}

async function fetchGraph(profile = null) {
    const params = new URLSearchParams();
    if (profile) params.set("source_profile", profile);
    if (state.edgeLimit !== null) params.set("edge_limit", String(state.edgeLimit));
    const query = params.toString();
    return fetchJSON(query ? `/api/graph?${query}` : "/api/graph");
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

function profileLabel(sourceProfile) {
    const value = String(sourceProfile || "unknown");
    const colon = value.indexOf(":");
    return colon >= 0 ? value.slice(colon + 1) : value;
}

const PROFILE_COLORS = [
    "#6ea8fe",
    "#7bd88f",
    "#f6c85f",
    "#f08a8a",
    "#b58cff",
    "#5fd3d3",
    "#ff9f68",
    "#d0d0d0",
];

function colorForProfile(profile) {
    const value = profileLabel(profile);
    let hash = 0;

    for (let i = 0; i < value.length; i += 1) {
        hash = ((hash << 5) - hash) + value.charCodeAt(i);
        hash |= 0;
    }

    return PROFILE_COLORS[Math.abs(hash) % PROFILE_COLORS.length];
}

function renderProfiles(profiles) {
    const list = $("profile-list");
    list.innerHTML = "";

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

function renderStatistics(diagnostics = null) {
    $("stat-profiles").textContent =
        diagnostics?.profiles?.total_profiles ?? state.profiles.length ?? "—";

    const fallbackMemoryCount = state.profiles.reduce(
        (sum, profile) => sum + Number(profile.memory_count || 0), 0
    );
    $("stat-memories").textContent =
        diagnostics?.profiles?.total_memories ?? fallbackMemoryCount;

    $("stat-nodes").textContent = state.graph.nodes.length;
    $("stat-edges").textContent = countEdges(state.graph.edges);
}

function countEdges(edges) {
    if (!edges || typeof edges !== "object") return 0;
    return Object.values(edges).reduce(
        (total, outgoing) => total + (Array.isArray(outgoing) ? outgoing.length : 0), 0
    );
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
    for (const [key,value] of Object.entries(attributes)) element.setAttribute(key,value);
    return element;
}

function renderGraph(graph) {
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

    /*
     * The Three.js module is loaded separately from browser.js.
     * If renderGraph runs before it becomes available, wait for the
     * module-ready event and render the current graph once.
     */
    container.innerHTML =
        '<div class="loading-state">Loading 3D constellation…</div>';

    if (!window.__mnemosyne3d_waiting) {
        window.__mnemosyne3d_waiting = true;

        window.addEventListener(
            "mnemosyne-3d-ready",
            () => {
                window.__mnemosyne3d_waiting = false;
                renderGraph(state.graph);
            },
            { once: true },
        );
    }
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

function bindGraphInteraction(container) {
    container.onwheel = e => {
        e.preventDefault();
        state.zoom = Math.max(.2,Math.min(8,state.zoom*(e.deltaY < 0 ? 1.15 : .87)));
        applyTransform();
    };
    container.onmousedown = e => {
        if(e.target.closest(".graph-node")) return;
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

function applyTransform() {
    const viewport = document.querySelector(".graph-viewport");
    if(viewport) viewport.setAttribute(
        "transform",`translate(${state.panX} ${state.panY}) scale(${state.zoom})`
    );
}
function resetGraphView(){
    state.zoom=1;
    state.panX=0;
    state.panY=0;

    if(window.Mnemosyne3D?.reset){
        window.Mnemosyne3D.reset();
        return;
    }

    applyTransform();
}

function renderInspector(node, graph) {
    const container = $("inspector-content");
    if(!node){
        container.innerHTML='<div class="empty-state"><strong>No selection</strong><p>Select a node to inspect its memory.</p></div>';
        return;
    }
    const outgoing = Array.isArray(graph.edges?.[node.graph_id]) ? graph.edges[node.graph_id] : [];
    const incoming = flattenEdges(graph.edges).filter(e=>e.target_id===node.graph_id);

    container.innerHTML="";
    const memorySection=document.createElement("section");
    memorySection.className="inspector-section";
    memorySection.innerHTML=`
        <h3>Memory Content</h3>
        <div id="memory-content" class="memory-loading">Loading source memory…</div>`;
    container.appendChild(memorySection);

    const identity=document.createElement("section");
    identity.className="inspector-section";
    identity.innerHTML=`
        <h3>Identity</h3><dl class="inspector-grid">
        <dt>Graph ID</dt><dd>${escapeHTML(node.graph_id)}</dd>
        <dt>Profile</dt><dd>${escapeHTML(node.source_profile)}</dd>
        <dt>Memory ID</dt><dd>${escapeHTML(node.origin_memory_id)}</dd>
        </dl>`;
    container.appendChild(identity);

    const lifecycle=document.createElement("section");
    lifecycle.className="inspector-section";
    lifecycle.innerHTML=`
        <h3>Lifecycle</h3><dl class="inspector-grid">
        <dt>State</dt><dd>${escapeHTML(node.lifecycle_state)}</dd>
        <dt>Proposed</dt><dd>${escapeHTML(node.proposed_at)}</dd>
        <dt>Validated</dt><dd>${escapeHTML(node.validated_at)}</dd>
        <dt>Validator</dt><dd>${escapeHTML(node.validator_profile)}</dd>
        <dt>Validation score</dt><dd>${formatScore(node.validation_score)}</dd>
        </dl>`;
    container.appendChild(lifecycle);

    const relationships=document.createElement("section");
    relationships.className="inspector-section";
    relationships.innerHTML=`<h3>Relationships</h3><div class="relationship-count">${outgoing.length} outgoing · ${incoming.length} incoming</div>`;
    for(const edge of outgoing){
        const item=document.createElement("div");
        item.className="relationship";
        item.innerHTML=`<div><span class="relationship-type">${escapeHTML(edge.relationship_type)}</span></div>
            <div>→ ${escapeHTML(edge.target_id)}</div>
            <div>similarity: ${formatScore(edge.similarity_score)}</div>`;
        relationships.appendChild(item);
    }
    if(!outgoing.length){
        const empty=document.createElement("div");
        empty.className="empty-state"; empty.textContent="No outgoing relationships in this view.";
        relationships.appendChild(empty);
    }
    container.appendChild(relationships);

    loadMemoryContent(node);
}

async function loadMemoryContent(node) {
    const target=$("memory-content");
    if(!target) return;
    try {
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

                if(!agent?.base_url) throw new Error(
                    `Source agent ${agentId} is not available through LAN discovery.`
                );

                data=await fetchJSON(
                    `${agent.base_url}/api/memories/${encodeURIComponent(profile)}/${encodeURIComponent(node.origin_memory_id)}`
                );
            }
        }else{
            data=await fetchJSON(
                `/api/memories/${encodeURIComponent(source)}/${encodeURIComponent(node.origin_memory_id)}`
            );
        }
        target.className="memory-content";
        target.textContent=data.content;
    }catch(error){
        target.className="error-state";
        target.textContent=`Unable to retrieve source memory: ${error.message}`;
    }
}

function selectNode(node,graph=state.graph){
    state.selectedNode=node;
    renderInspector(node,graph);
    setSelectionStatus(`Selected ${node.source_profile}:${node.origin_memory_id}`);
    document.querySelectorAll(".graph-node").forEach(e =>
        e.classList.toggle("selected",e.dataset.graphId===node.graph_id));
    document.querySelectorAll(".data-table tbody tr").forEach(e =>
        e.classList.toggle("selected",e.dataset.graphId===node.graph_id));
}

function renderTable(graph){
    const container=$("table-view"); container.innerHTML="";
    if(!graph.nodes.length){
        container.innerHTML='<div class="loading-state">No graph data available.</div>';
        return;
    }

    const table=document.createElement("table");
    table.className="data-table";
    table.innerHTML=`<thead><tr>
        <th>Memory Content</th>
        <th>Agent / Profile</th>
        <th>Lifecycle</th>
        <th>Memory ID</th>
    </tr></thead><tbody></tbody>`;

    const body=table.querySelector("tbody");

    for(const node of graph.nodes){
        const row=document.createElement("tr");
        row.dataset.graphId=node.graph_id;

        const contentCell=document.createElement("td");
        contentCell.className="memory-preview";
        contentCell.textContent="Loading…";

        const profileCell=document.createElement("td");
        profileCell.textContent=profileLabel(node.source_profile);

        const lifecycleCell=document.createElement("td");
        lifecycleCell.textContent=node.lifecycle_state || "—";

        const idCell=document.createElement("td");
        idCell.className="memory-id";
        idCell.textContent=node.origin_memory_id;

        row.appendChild(contentCell);
        row.appendChild(profileCell);
        row.appendChild(lifecycleCell);
        row.appendChild(idCell);

        row.addEventListener("click",()=>selectNode(node,graph));
        body.appendChild(row);

        loadTableMemoryPreview(node, contentCell);
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

function setViewMode(mode){
    state.viewMode=mode;
    $("graph-view").classList.toggle("hidden",mode==="table");
    $("table-view").classList.toggle("hidden",mode!=="table");
    if(mode==="table") renderTable(state.graph); else renderGraph(state.graph);
}

async function selectProfile(profile){
    state.selectedProfile=profile; state.selectedNode=null; resetGraphView();
    renderProfiles(state.profiles);
    $("workspace-subtitle").textContent=profile ? `Profile: ${profile}` : "All profiles";
    setSelectionStatus("");
    try{
        setStatus(profile ? `Loading ${profile} graph…` : "Loading collective graph…");
        state.graph=await fetchGraph(profile); renderStatistics();
        state.viewMode==="table" ? renderTable(state.graph) : renderGraph(state.graph);
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
            renderGraph(state.graph);
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
            renderGraph(state.graph);
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
        state.profiles=await fetchProfiles(); renderProfiles(state.profiles);
        const diagnostics=await fetchDiagnostics(); renderStatistics(diagnostics);
        state.graph=await fetchGraph(state.selectedProfile);
        state.viewMode==="table" ? renderTable(state.graph) : renderGraph(state.graph);
        await refreshDiscovery();
        setStatus(`Ready — ${state.graph.nodes.length} nodes, ${countEdges(state.graph.edges)} edges.`);
    }catch(error){showError(error);}
}

function showError(error){
    console.error(error); setStatus(`Error: ${error.message || String(error)}`,true);
    const graphView=$("graph-view");
    if(graphView) graphView.innerHTML=`<div class="error-state">Unable to load Browser data.<br>${escapeHTML(error.message || String(error))}</div>`;
}

function formatScore(value){
    if(value===null || value===undefined) return "—";
    const number=Number(value); return Number.isFinite(number) ? number.toFixed(3) : "—";
}
function escapeHTML(value){
    return String(value ?? "—").replaceAll("&","&amp;").replaceAll("<","&lt;")
        .replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
}

function bindControls(){
    $("refresh-button").addEventListener("click",refresh);
    $("clear-profile-button").addEventListener("click",()=>selectProfile(null));
    $("view-mode").addEventListener("change",e=>setViewMode(e.target.value));
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
    $("rebuild-button").addEventListener("click",rebuildCollective);
    $("nuke-button").addEventListener("click",nukeCollective);
}

async function init(){
    bindControls();
    try{
        setStatus("Loading profiles…");
        state.profiles=await fetchProfiles(); renderProfiles(state.profiles);
        const diagnostics=await fetchDiagnostics(); renderStatistics(diagnostics);
        await refreshDiscovery();
        state.graph=await fetchGraph(state.selectedProfile);
        renderStatistics(diagnostics);
        state.viewMode==="table" ? renderTable(state.graph) : renderGraph(state.graph);
        setStatus(`Ready — ${state.graph.nodes.length} nodes, ${countEdges(state.graph.edges)} edges.`);
    }catch(error){showError(error);}
}

window.addEventListener("DOMContentLoaded",init);
