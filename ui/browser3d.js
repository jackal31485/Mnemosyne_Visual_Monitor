import * as THREE from "/static/vendor/three/three.module.min.js";
import { OrbitControls } from "/static/vendor/three/OrbitControls.js";

const DEFAULT_PROFILE_COLORS = [
    0x6ea8fe,
    0x7bd88f,
    0xf6c85f,
    0xf08a8a,
    0xb58cff,
    0x5fd3d3,
    0xff9f68,
    0xd0d0d0,
];

let active = null;

function hashString(value) {
    let hash = 0;
    for (let i = 0; i < value.length; i += 1) {
        hash = ((hash << 5) - hash) + value.charCodeAt(i);
        hash |= 0;
    }
    return Math.abs(hash);
}

function profileLabel(profile) {
    const value = String(profile || "");
    const separator = value.indexOf(":");

    return separator >= 0
        ? value.slice(separator + 1)
        : value;
}

function colorForProfile(profile) {
    const label = profileLabel(profile);

    try {
        const stored = JSON.parse(
            localStorage.getItem("mnemosyne-profile-colours") || "{}"
        );

        const configured = stored[label];

        if (
            typeof configured === "string" &&
            /^#[0-9a-fA-F]{6}$/.test(configured)
        ) {
            return Number.parseInt(configured.slice(1), 16);
        }
    } catch (_) {
        // Fall back to the deterministic default palette.
    }

    return DEFAULT_PROFILE_COLORS[
        hashString(label) % DEFAULT_PROFILE_COLORS.length
    ];
}


function createRenderer(container) {
    const renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
    });

    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(container.clientWidth, container.clientHeight, false);
    renderer.setClearColor(0x000000, 0);

    return renderer;
}

function calculatePositions(nodes, edges) {
    const positions = new Map();
    const velocities = new Map();
    const nodeById = new Map(nodes.map(node => [node.graph_id, node]));
    const neighbors = new Map(nodes.map(node => [node.graph_id, []]));

    for (const edge of edges) {
        const source = nodeById.get(edge.source_id);
        const target = nodeById.get(edge.target_id);
        if (!source || !target) continue;

        const score = Math.max(0, Math.min(1, Number(edge.similarity_score ?? 0)));

        neighbors.get(source.graph_id).push({
            id: target.graph_id,
            weight: score,
        });

        neighbors.get(target.graph_id).push({
            id: source.graph_id,
            weight: score,
        });
    }

    /*
     * Start from a deterministic 3D distribution, then let the graph
     * topology pull related memories together.
     */
    const count = Math.max(nodes.length, 1);
    const radius = Math.max(180, Math.min(520, Math.sqrt(count) * 22));

    nodes.forEach((node, index) => {
        const seed = hashString(String(node.graph_id));
        const theta = (index / count) * Math.PI * 2;
        const phi = Math.acos(
            1 - 2 * ((index + 0.5) / count)
        );

        const variation = 0.75 + ((seed % 1000) / 1000) * 0.5;

        const position = new THREE.Vector3(
            radius * variation * Math.sin(phi) * Math.cos(theta),
            radius * variation * Math.cos(phi),
            radius * variation * Math.sin(phi) * Math.sin(theta),
        );

        positions.set(node.graph_id, position);
        velocities.set(node.graph_id, new THREE.Vector3());
    });

    /*
     * Force-directed relaxation.
     *
     * Attractive force:
     *   stronger semantic similarity => stronger pull
     *
     * Repulsive force:
     *   keeps unrelated memories separated
     *
     * The simulation runs only during layout creation, not every frame.
     */
    const iterations = count > 700 ? 55 : 85;
    const idealDistance = 58;
    const repulsion = count > 700 ? 1450 : 1900;

    for (let iteration = 0; iteration < iterations; iteration += 1) {
        const alpha = 1 - (iteration / iterations);
        const damping = 0.72;

        /*
         * Global repulsion.
         *
         * 526 nodes means ~276k pairs per iteration, which is entirely
         * reasonable for a one-time layout calculation and avoids adding
         * another dependency such as a Barnes-Hut implementation.
         */
        for (let i = 0; i < nodes.length; i += 1) {
            const a = nodes[i];
            const pa = positions.get(a.graph_id);
            const va = velocities.get(a.graph_id);

            for (let j = i + 1; j < nodes.length; j += 1) {
                const b = nodes[j];
                const pb = positions.get(b.graph_id);
                const vb = velocities.get(b.graph_id);

                const dx = pa.x - pb.x;
                const dy = pa.y - pb.y;
                const dz = pa.z - pb.z;

                const distanceSquared =
                    dx * dx + dy * dy + dz * dz + 18;

                const distance = Math.sqrt(distanceSquared);
                const force =
                    (repulsion * alpha) / distanceSquared;

                const fx = (dx / distance) * force;
                const fy = (dy / distance) * force;
                const fz = (dz / distance) * force;

                va.x += fx;
                va.y += fy;
                va.z += fz;

                vb.x -= fx;
                vb.y -= fy;
                vb.z -= fz;
            }
        }

        /*
         * Similarity attraction.
         *
         * Ignore very weak edges when positioning. The graph may retain
         * them visually, but they should not prevent strong communities
         * from forming compact clusters.
         */
        for (const edge of edges) {
            const score = Math.max(
                0,
                Math.min(1, Number(edge.similarity_score ?? 0))
            );

            if (score < 0.75) continue;

            const pa = positions.get(edge.source_id);
            const pb = positions.get(edge.target_id);
            const va = velocities.get(edge.source_id);
            const vb = velocities.get(edge.target_id);

            if (!pa || !pb || !va || !vb) continue;

            const dx = pb.x - pa.x;
            const dy = pb.y - pa.y;
            const dz = pb.z - pa.z;

            const distance = Math.sqrt(
                dx * dx + dy * dy + dz * dz
            ) || 0.001;

            /*
             * Higher similarity means a shorter desired distance and a
             * stronger spring.
             */
            const normalizedStrength =
                (score - 0.75) / 0.25;

            const targetDistance =
                idealDistance * (1.15 - normalizedStrength * 0.55);

            const spring =
                0.018 +
                normalizedStrength * 0.055;

            const force =
                (distance - targetDistance) *
                spring *
                alpha;

            const fx = (dx / distance) * force;
            const fy = (dy / distance) * force;
            const fz = (dz / distance) * force;

            va.x += fx;
            va.y += fy;
            va.z += fz;

            vb.x -= fx;
            vb.y -= fy;
            vb.z -= fz;
        }

        /*
         * Keep the graph centered and prevent runaway positions.
         */
        for (const node of nodes) {
            const position = positions.get(node.graph_id);
            const velocity = velocities.get(node.graph_id);

            velocity.x *= damping;
            velocity.y *= damping;
            velocity.z *= damping;

            position.add(velocity);

            const maxRadius = radius * 1.45;
            const length = position.length();

            if (length > maxRadius) {
                position.multiplyScalar(maxRadius / length);
                velocity.multiplyScalar(0.25);
            }
        }
    }

    /*
     * Center the final constellation.
     */
    const center = new THREE.Vector3();

    for (const position of positions.values()) {
        center.add(position);
    }

    center.multiplyScalar(1 / count);

    for (const position of positions.values()) {
        position.sub(center);
    }

    return positions;
}
function createNodeMesh(node, position, selected) {
    const radius = selected ? 5.5 : 3.5;

    const geometry = new THREE.SphereGeometry(radius, 12, 8);
    const material = new THREE.MeshBasicMaterial({
        color: colorForProfile(node.source_profile),
    });

    const mesh = new THREE.Mesh(geometry, material);

    mesh.position.copy(position);
    mesh.userData.node = node;

    if (selected) {
        const outlineGeometry = new THREE.SphereGeometry(radius * 1.45, 12, 8);
        const outlineMaterial = new THREE.MeshBasicMaterial({
            color: 0xffffff,
            wireframe: true,
        });

        const outline = new THREE.Mesh(outlineGeometry, outlineMaterial);
        mesh.add(outline);
    }

    return mesh;
}

function createEdges(graph, positions) {
    const group = new THREE.Group();

    for (const edge of getGraphEdges(graph.edges)) {
        const source = positions.get(edge.source_id);
        const target = positions.get(edge.target_id);

        if (!source || !target) {
            continue;
        }

        const score = Number(edge.similarity_score ?? 0);

        const geometry = new THREE.BufferGeometry().setFromPoints([
            source,
            target,
        ]);

        const material = new THREE.LineBasicMaterial({
            color: score >= 0.85 ? 0x9fc8ff : 0x687789,
            transparent: true,
            opacity: score >= 0.85 ? 0.72 : 0.42,
        });

        group.add(new THREE.Line(geometry, material));
    }

    return group;
}

function getGraphEdges(edges) {
    if (Array.isArray(edges)) {
        return edges;
    }

    if (typeof window.flattenEdges === "function") {
        return window.flattenEdges(edges);
    }

    return [];
}

function disposeObject(object) {
    object.traverse(child => {
        if (child.geometry) {
            child.geometry.dispose();
        }

        if (child.material) {
            if (Array.isArray(child.material)) {
                child.material.forEach(material => material.dispose());
            } else {
                child.material.dispose();
            }
        }
    });
}

export function destroy3D() {
    if (!active) {
        return;
    }

    cancelAnimationFrame(active.animationFrame);

    if (active.resizeObserver) {
        active.resizeObserver.disconnect();
    }

    active.controls.dispose();

    disposeObject(active.scene);

    active.renderer.dispose();

    active.container.innerHTML = "";

    active = null;
}

export function render3D(container, graph, state, onSelect) {
    destroy3D();

    if (!graph?.nodes?.length) {
        container.innerHTML =
            '<div class="loading-state">No graph data available.</div>';
        return;
    }

    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(
        55,
        Math.max(container.clientWidth, 1) /
            Math.max(container.clientHeight, 1),
        0.1,
        5000,
    );

    camera.position.set(0, 0, 700);

    const renderer = createRenderer(container);
    container.appendChild(renderer.domElement);

    renderer.domElement.className = "graph-3d-canvas";
    renderer.domElement.setAttribute(
        "aria-label",
        "Mnemosyne 3D constellation graph",
    );

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 120;
    controls.maxDistance = 2500;
    controls.rotateSpeed = 0.55;
    controls.zoomSpeed = 0.8;
    controls.panSpeed = 0.6;

    const graphEdges = getGraphEdges(graph.edges);
    const positions = calculatePositions(graph.nodes, graphEdges);

    const edgeGroup = createEdges({ ...graph, edges: graphEdges }, positions);
    scene.add(edgeGroup);

    const nodeGroup = new THREE.Group();

    for (const node of graph.nodes) {
        const position = positions.get(node.graph_id);

        if (!position) {
            continue;
        }

        const selected =
            state.selectedNode?.graph_id === node.graph_id;

        nodeGroup.add(
            createNodeMesh(node, position, selected),
        );
    }

    scene.add(nodeGroup);

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();

    function handlePointer(event) {
        const rect = renderer.domElement.getBoundingClientRect();

        pointer.x =
            ((event.clientX - rect.left) / rect.width) * 2 - 1;

        pointer.y =
            -((event.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(pointer, camera);

        const hits = raycaster.intersectObjects(
            nodeGroup.children,
            false,
        );

        if (!hits.length) {
            return;
        }

        const node = hits[0].object.userData.node;

        if (node) {
            onSelect(node, graph);
        }
    }

    renderer.domElement.addEventListener(
        "pointerup",
        handlePointer,
    );

    const resizeObserver = new ResizeObserver(() => {
        const width = Math.max(container.clientWidth, 1);
        const height = Math.max(container.clientHeight, 1);

        camera.aspect = width / height;
        camera.updateProjectionMatrix();

        renderer.setSize(width, height, false);
    });

    resizeObserver.observe(container);

    function animate() {
        if (active?.renderer !== renderer) {
            return;
        }

        controls.update();
        renderer.render(scene, camera);

        active.animationFrame = requestAnimationFrame(animate);
    }

    active = {
        container,
        scene,
        camera,
        renderer,
        controls,
        resizeObserver,
        animationFrame: requestAnimationFrame(animate),
    };
}

export function zoomIn() {
    if (!active) {
        return;
    }

    const offset = active.camera.position.clone().sub(active.controls.target);
    const distance = offset.length();

    if (distance <= active.controls.minDistance) {
        return;
    }

    const nextDistance = Math.max(
        active.controls.minDistance,
        distance * 0.8,
    );

    offset.setLength(nextDistance);
    active.camera.position.copy(active.controls.target).add(offset);
    active.controls.update();
}

export function zoomOut() {
    if (!active) {
        return;
    }

    const offset = active.camera.position.clone().sub(active.controls.target);
    const distance = offset.length();

    if (distance >= active.controls.maxDistance) {
        return;
    }

    const nextDistance = Math.min(
        active.controls.maxDistance,
        distance * 1.25,
    );

    offset.setLength(nextDistance);
    active.camera.position.copy(active.controls.target).add(offset);
    active.controls.update();
}

export function reset3D() {
    if (!active) {
        return;
    }

    active.camera.position.set(0, 0, 700);
    active.controls.target.set(0, 0, 0);
    active.controls.update();
}

window.Mnemosyne3D = {
    render: render3D,
    destroy: destroy3D,
    zoomIn,
    zoomOut,
    reset: reset3D,
};
