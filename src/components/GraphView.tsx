import { useEffect, useRef } from "react";
import Graph from "graphology";
import forceAtlas2 from "graphology-layout-forceatlas2";

export type GraphNode = { id: string; label: string; group?: string };
export type GraphEdge = { source: string; target: string; label?: string };

// Predefined colors
const GROUP_COLORS: Record<string, string> = {
  symptom: "#f59e0b",
  disease: "#ef4444",
  crop: "#22c55e",
  treatment: "#3b82f6",
  agent: "#a855f7",
  default: "#64748b",
};

// HSL to Hex converter
function hslToHex(h: number, s: number, l: number) {
  l /= 100;
  const a = s * Math.min(l, 1 - l) / 100;
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color).toString(16).padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

// Generate a color from a string (hash)
function getColorForGroup(group: string) {
  if (GROUP_COLORS[group]) return GROUP_COLORS[group];
  
  // Hash function for stable colors
  let hash = 0;
  for (let i = 0; i < group.length; i++) {
    hash = group.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  // Generate Hex color
  const h = Math.abs(hash) % 360;
  return hslToHex(h, 70, 55);
}

export function GraphView({ nodes, edges, height = 520 }: { nodes: GraphNode[]; edges: GraphEdge[]; height?: number }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    
    let renderer: any = null;
    let isMounted = true;

    async function initGraph() {
      const { default: Sigma } = await import("sigma");
      if (!isMounted || !containerRef.current) return;

      const graph = new Graph();
      
      // Add nodes with random initial positions
      nodes.forEach((n) => {
        const group = n.group || "default";
        if (!graph.hasNode(n.id)) {
          graph.addNode(n.id, {
            label: n.label,
            x: Math.random() * 100,
            y: Math.random() * 100,
            size: group === "disease" ? 14 : group === "agent" ? 12 : Math.random() * 3 + 5,
            color: getColorForGroup(group),
          });
        }
      });
      
      // Add edges
      edges.forEach((e, i) => {
        if (graph.hasNode(e.source) && graph.hasNode(e.target)) {
          // Avoid duplicate edges throwing errors
          if (!graph.hasEdge(e.source, e.target) && !graph.hasEdge(e.target, e.source)) {
            try {
              graph.addEdgeWithKey(`e${i}`, e.source, e.target, {
                label: e.label, size: 1.5, color: "rgba(150,150,150,0.3)", type: "arrow",
              });
            } catch (err) {
              // Ignore edge creation errors
            }
          }
        }
      });

      // Apply ForceAtlas2 layout to cluster related nodes
      if (graph.order > 0) {
        forceAtlas2.assign(graph, {
          iterations: 150,
          settings: {
            gravity: 1,
            scalingRatio: 2,
            strongGravityMode: false,
          }
        });
      }

      renderer = new Sigma(graph, containerRef.current, {
        renderEdgeLabels: true,
        defaultEdgeType: "arrow",
        labelColor: { color: getComputedStyle(document.documentElement).getPropertyValue("--foreground") || "#222" },
        labelSize: 13,
        labelWeight: "600",
      });
      sigmaRef.current = renderer;
    }

    initGraph();

    return () => { 
      isMounted = false;
      if (renderer) renderer.kill(); 
      sigmaRef.current = null; 
    };
  }, [nodes, edges]);

  // Extract unique groups from nodes for the legend, up to 10 to avoid clutter
  const uniqueGroups = Array.from(new Set(nodes.map(n => n.group || "default")))
    .filter(g => g !== "default")
    .slice(0, 10);

  return (
    <div className="relative rounded-3xl overflow-hidden border border-border/50 bg-secondary/30 backdrop-blur-md shadow-soft" style={{ height }}>
      <div ref={containerRef} className="absolute inset-0 bg-transparent" />
      <div className="absolute top-4 left-4 bg-background/80 backdrop-blur-md border rounded-xl px-4 py-2.5 text-xs flex flex-wrap gap-3 max-w-[90%] overflow-hidden max-h-32 shadow-lg">
        {uniqueGroups.map(group => (
          <span key={group} className="flex items-center gap-1.5 capitalize text-foreground font-medium">
            <span className="size-2.5 rounded-full shadow-sm" style={{ background: getColorForGroup(group) }} /> {group.replace('community-', 'Comm ')}
          </span>
        ))}
      </div>
    </div>
  );
}
