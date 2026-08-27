from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient
import uvicorn

from app.main import app as api_app

app = FastAPI(title="Mnemosyne Visual Monitor – Constellation View")

@app.get("/api/graph")
def graph():
    client = TestClient(api_app)
    response = client.get("/api/graph")
    response.raise_for_status()
    return response.json()

@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mnemosyne Constellation</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<style>
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#080b12;color:#e8edf7;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
#app{width:100%;height:100%;position:relative}
svg{width:100%;height:100%;display:block}
.link{stroke:#78839a;stroke-opacity:.28}
.link-label{fill:#aeb8ca;font-size:10px;pointer-events:none}
.node{stroke:#fff;stroke-width:1.2px;cursor:grab}
.node:active{cursor:grabbing}
.panel{position:absolute;top:14px;left:14px;right:14px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;pointer-events:none}
.card{background:rgba(15,20,31,.92);border:1px solid #293245;border-radius:10px;padding:9px 12px;box-shadow:0 5px 25px rgba(0,0,0,.35);pointer-events:auto}
.title{font-weight:700}
.stats{font-size:12px;color:#aeb8ca}
.controls{display:flex;gap:6px;flex-wrap:wrap}
button{border:1px solid #344056;background:#151c29;color:#e8edf7;border-radius:7px;padding:6px 9px;cursor:pointer}
button.active{background:#263a58;border-color:#668ac4}
.tooltip{position:fixed;display:none;max-width:330px;background:#111722;border:1px solid #354057;border-radius:9px;padding:10px 12px;font-size:12px;line-height:1.45;pointer-events:none;box-shadow:0 8px 30px rgba(0,0,0,.45)}
.legend{display:flex;gap:7px;flex-wrap:wrap;font-size:11px}
.legend span{display:inline-flex;align-items:center;gap:4px}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block}
</style>
</head>
<body>
<div id="app">
<svg></svg>
<div class="panel">
  <div class="card">
    <div class="title">Mnemosyne Constellation</div>
    <div id="stats" class="stats">Loading…</div>
  </div>
  <div class="card controls" id="profiles"></div>
  <div class="card legend" id="legend"></div>
</div>
<div class="tooltip" id="tooltip"></div>
</div>

<script>
const svg=d3.select("svg");
const tooltip=d3.select("#tooltip");
const stats=d3.select("#stats");
const profileControls=d3.select("#profiles");
const legend=d3.select("#legend");

const palette=[
 "#4dabf7","#ff6b6b","#51cf66","#fcc419","#cc5de8",
 "#20c997","#ff922b","#845ef7","#f06595","#94d82d"
];

function escapeHtml(value){
  return String(value ?? "")
    .replaceAll("&","&amp;").replaceAll("<","&lt;")
    .replaceAll(">","&gt;").replaceAll('"',"&quot;");
}

async function load(){
  const response=await fetch("/api/graph");
  if(!response.ok) throw new Error("Graph API returned "+response.status);
  const data=await response.json();

  const rawNodes=Array.isArray(data.nodes)?data.nodes:[];
  let rawEdges=[];

  if(Array.isArray(data.edges)){
    rawEdges=data.edges;
  }else if(data.edges && typeof data.edges==="object"){
    Object.values(data.edges).forEach(list=>{
      if(Array.isArray(list)) rawEdges.push(...list);
    });
  }

  const profiles=[...new Set(rawNodes.map(n=>n.source_profile).filter(Boolean))].sort();
  const color=d3.scaleOrdinal().domain(profiles).range(palette);

  let selected=new Set(profiles);

  function renderLegend(){
    legend.html("");
    profiles.forEach(p=>{
      legend.append("span").html(
        `<i class="dot" style="background:${color(p)}"></i>${escapeHtml(p)}`
      );
    });
  }

  function renderControls(){
    profileControls.html("");
    const all=profileControls.append("button")
      .text("All")
      .classed("active",selected.size===profiles.length)
      .on("click",()=>{
        selected=new Set(profiles);
        renderControls();
        draw();
      });

    profiles.forEach(p=>{
      profileControls.append("button")
        .text(p)
        .classed("active",selected.has(p))
        .on("click",()=>{
          if(selected.has(p)) selected.delete(p);
          else selected.add(p);
          renderControls();
          draw();
        });
    });
  }

  renderLegend();
  renderControls();

  function draw(){
    svg.selectAll("*").remove();

    const nodes=rawNodes
      .filter(n=>selected.has(n.source_profile))
      .map((n,i)=>({...n,index:i}));

    const nodeIds=new Set(nodes.map(n=>n.graph_id ?? n.id));

    const edges=rawEdges.filter(e=>{
      const s=e.source_id ?? e.source;
      const t=e.target_id ?? e.target;
      return nodeIds.has(s)&&nodeIds.has(t);
    }).map(e=>({
      source:e.source_id ?? e.source,
      target:e.target_id ?? e.target,
      similarity_score:e.similarity_score ?? e.similarity ?? 0
    }));

    const width=window.innerWidth;
    const height=window.innerHeight;

    stats.text(`${nodes.length} nodes · ${edges.length} similarity links · ${selected.size}/${profiles.length} profiles`);

    const root=svg.append("g");

    const zoom=d3.zoom()
      .scaleExtent([.15,5])
      .on("zoom",event=>root.attr("transform",event.transform));

    svg.call(zoom);

    const defs=svg.append("defs");
    profiles.forEach(p=>{
      defs.append("filter")
        .attr("id","glow-"+CSS.escape(p))
        .append("feGaussianBlur")
        .attr("stdDeviation","2");
    });

    const link=root.append("g")
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("class","link")
      .attr("stroke-width",d=>Math.max(1,Math.min(5,d.similarity_score*5)))
      .attr("stroke-opacity",d=>Math.max(.12,Math.min(.8,d.similarity_score)));

    const linkLabel=root.append("g")
      .selectAll("text")
      .data(edges)
      .join("text")
      .attr("class","link-label")
      .text(d=>d.similarity_score.toFixed(3))
      .style("display","none");

    /*
     * Profile clustering:
     * each profile receives a deterministic centre around the viewport.
     * The force simulation then keeps related nodes together while allowing
     * individual nodes to remain draggable.
     */
    const centres=new Map();
    profiles.forEach((p,i)=>{
      const angle=(i/Math.max(1,profiles.length))*Math.PI*2;
      centres.set(p,{
        x:width/2+Math.cos(angle)*Math.min(width,height)*.30,
        y:height/2+Math.sin(angle)*Math.min(width,height)*.30
      });
    });

    const node=root.append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("class","node")
      .attr("r",d=>d.has_embedding===false?5:7)
      .attr("fill",d=>color(d.source_profile))
      .on("mouseenter",(event,d)=>{
        const id=d.graph_id ?? d.id ?? "";
        const memory=d.origin_memory_id ?? d.memory_id ?? "";
        const similarityLinks=edges.filter(e=>e.source===id||e.target===id);

        tooltip
          .style("display","block")
          .html(
            `<strong>${escapeHtml(d.source_profile)}</strong><br>`+
            `ID: ${escapeHtml(id)}<br>`+
            `Memory: ${escapeHtml(memory)}<br>`+
            `State: ${escapeHtml(d.lifecycle_state ?? d.kind ?? "")}<br>`+
            `Links: ${similarityLinks.length}`
          );
      })
      .on("mousemove",event=>{
        tooltip.style("left",(event.clientX+14)+"px")
               .style("top",(event.clientY+14)+"px");
      })
      .on("mouseleave",()=>tooltip.style("display","none"))
      .call(d3.drag()
        .on("start",(event,d)=>{
          if(!event.active) simulation.alphaTarget(.2).restart();
          d.fx=d.x; d.fy=d.y;
        })
        .on("drag",(event,d)=>{
          d.fx=event.x; d.fy=event.y;
        })
        .on("end",(event,d)=>{
          if(!event.active) simulation.alphaTarget(0);
          d.fx=null; d.fy=null;
        })
      );

    const simulation=d3.forceSimulation(nodes)
      .force("link",d3.forceLink(edges).id(d=>d.graph_id ?? d.id)
        .distance(d=>100+(1-d.similarity_score)*180)
        .strength(d=>Math.max(.05,d.similarity_score*.35)))
      .force("charge",d3.forceManyBody().strength(-35))
      .force("collision",d3.forceCollide().radius(9))
      .force("center",d3.forceCenter(width/2,height/2))
      .force("cluster",d3.forceX(d=>centres.get(d.source_profile)?.x ?? width/2).strength(.055))
      .force("clusterY",d3.forceY(d=>centres.get(d.source_profile)?.y ?? height/2).strength(.055))
      .on("tick",()=>{
        link
          .attr("x1",d=>d.source.x).attr("y1",d=>d.source.y)
          .attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);

        node.attr("cx",d=>d.x).attr("cy",d=>d.y);

        linkLabel
          .attr("x",d=>(d.source.x+d.target.x)/2)
          .attr("y",d=>(d.source.y+d.target.y)/2);
      });

    window.addEventListener("resize",()=>{
      simulation.force("center",d3.forceCenter(window.innerWidth/2,window.innerHeight/2));
      simulation.alpha(.2).restart();
    },{once:true});
  }

  draw();
}

load().catch(error=>{
  console.error(error);
  stats.text("Failed to load constellation: "+error.message);
});
</script>
</body>
</html>
""")

if __name__ == "__main__":
    uvicorn.run("src.web.main:app",host="127.0.0.1",port=12345,reload=False)
