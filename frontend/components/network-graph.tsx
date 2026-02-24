"use client"

import { useEffect, useState, useRef } from "react"
import dynamic from "next/dynamic"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { RefreshCw, Maximize2, Zap, Target, Mail, Wallet, ShieldCheck, Fingerprint } from "lucide-react"

// Dynamically import the force graph with SSR disabled
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { 
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-neutral-950">
      <RefreshCw className="h-8 w-8 animate-spin text-orange-500" />
      <p className="ml-2 text-sm text-neutral-400 font-mono">INITIALIZING ANALYTIC ENGINE...</p>
    </div>
  )
})

interface NetworkGraphProps {
  jobId: string
  onClose?: () => void
}

export function NetworkGraph({ jobId, onClose }: NetworkGraphProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const fgRef = useRef<any>()

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/network/${jobId}`)
        const result = await response.json()
        if (result.success) {
          setData(result.graph)
        }
      } catch (error) {
        console.error("Failed to fetch graph:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchGraph()
  }, [jobId])

  if (loading) {
    return (
      <div className="w-full h-[600px] flex flex-col items-center justify-center space-y-4 bg-neutral-900 border border-orange-900/30 rounded-lg">
        <RefreshCw className="h-10 w-10 animate-spin text-orange-500" />
        <p className="text-sm text-orange-500 font-mono tracking-widest">MAPPING RELATIONSHIPS...</p>
      </div>
    )
  }

  return (
    <div className="w-full h-full min-h-[700px] flex flex-col bg-neutral-950 border border-orange-900/30 rounded-xl overflow-hidden shadow-2xl">
      <div className="p-4 bg-neutral-900/80 border-b border-orange-900/30 flex items-center justify-between backdrop-blur-md">
        <div>
          <h3 className="text-orange-500 font-bold flex items-center gap-2 tracking-tighter">
            <Fingerprint className="h-5 w-5" />
            ENTITY RELATIONSHIP ANALYZER
          </h3>
          <p className="text-[10px] text-neutral-500 font-mono">CRYPTO-FORENSIC & OSINT CROSS-REFERENCE MAP</p>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => fgRef.current?.zoomToFit(400)}
            className="border-orange-900/50 text-orange-500 hover:bg-orange-500/10"
          >
            <Maximize2 className="h-4 w-4 mr-2" />
            FIT VIEW
          </Button>
          {onClose && (
            <Button variant="ghost" size="sm" onClick={onClose} className="text-neutral-500">CLOSE</Button>
          )}
        </div>
      </div>

      <div className="flex-1 relative bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-neutral-900 via-black to-black">
        {data ? (
          <ForceGraph2D
            ref={fgRef}
            graphData={data}
            backgroundColor="rgba(0,0,0,0)"
            nodeLabel={(node: any) => `
              <div class="bg-neutral-900 border border-orange-500 p-2 rounded text-[10px] font-mono shadow-xl">
                <span class="text-orange-500 font-bold">${node.type.toUpperCase()}</span><br/>
                <span class="text-white">${node.label}</span>
                ${node.risk_level ? `<br/><span class="text-red-500">RISK: ${node.risk_level.toUpperCase()}</span>` : ''}
              </div>
            `}
            nodeAutoColorBy="type"
            linkDirectionalArrowLength={6}
            linkDirectionalArrowRelPos={1}
            linkCurvature={0.15}
            linkWidth={1.5}
            linkColor={() => 'rgba(255, 255, 255, 0.15)'}
            // Draw relationship labels ON the links
            linkCanvasObjectMode={() => 'after'}
            linkCanvasObject={(link: any, ctx, globalScale) => {
              const MAX_FONT_SIZE = 10;
              // Use constant for node size instead of calling instance method to prevent crash
              const nodeRelSize = 4; 
              const LABEL_NODE_MARGIN = nodeRelSize * 1.5;

              const start = link.source;
              const end = link.target;

              // ignore unbound links
              if (typeof start !== 'object' || typeof end !== 'object') return;

              // calculate label positioning
              const textPos = {
                x: start.x + (end.x - start.x) / 2,
                y: start.y + (end.y - start.y) / 2
              };

              const relAngle = Math.atan2(end.y - start.y, end.x - start.x);

              const label = link.label;

              // draw text label
              const fontSize = Math.min(MAX_FONT_SIZE, 12 / globalScale);
              ctx.font = `${fontSize}px "Geist Mono"`;
              const textWidth = ctx.measureText(label).width;
              const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2); // some padding

              ctx.save();
              ctx.translate(textPos.x, textPos.y);
              ctx.rotate(relAngle);

              ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
              ctx.fillRect(-bckgDimensions[0] / 2, -bckgDimensions[1] / 2, ...bckgDimensions as [number, number]);

              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = 'rgba(255, 165, 0, 0.8)'; // Orange relationship text
              ctx.fillText(label, 0, 0);
              ctx.restore();
            }}
            nodeCanvasObject={(node: any, ctx, globalScale) => {
              // Safety check for finite coordinates to prevent Canvas errors
              if (!isFinite(node.x) || !isFinite(node.y)) return;

              const label = node.label;
              const fontSize = 14 / globalScale;
              ctx.font = `${fontSize}px "Geist Mono", monospace`;
              
              const nodeSize = node.size / 2;
              
              // Draw Glow
              const gradient = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, nodeSize * 2.5);
              gradient.addColorStop(0, `${node.color}55`);
              gradient.addColorStop(1, 'transparent');
              ctx.fillStyle = gradient;
              ctx.beginPath();
              ctx.arc(node.x, node.y, nodeSize * 2.5, 0, 2 * Math.PI, false);
              ctx.fill();

              // Draw Main Node Circle
              ctx.beginPath();
              ctx.arc(node.x, node.y, nodeSize, 0, 2 * Math.PI, false);
              ctx.fillStyle = node.color;
              ctx.fill();
              
              // White rim for clarity
              ctx.strokeStyle = '#fff';
              ctx.lineWidth = 1.5 / globalScale;
              ctx.stroke();

              // Draw Label Text (only if zoomed in enough)
              if (globalScale > 0.5) {
                const textWidth = ctx.measureText(label).width;
                const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.4);
                
                ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y + nodeSize + 2, bckgDimensions[0], bckgDimensions[1]);
                
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';
                ctx.fillStyle = '#fff';
                ctx.fillText(label, node.x, node.y + nodeSize + 3);
              }

              node.__bckgDimensions = [nodeSize, nodeSize];
            }}
            cooldownTicks={100}
            onEngineStop={() => fgRef.current?.zoomToFit(400, 100)}
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-neutral-500 font-mono">NO ARCHIVED CONNECTIONS FOUND</p>
          </div>
        )}
        
        {/* Legend Overlay */}
        <div className="absolute bottom-4 left-4 p-3 bg-neutral-900/80 border border-orange-900/30 rounded-lg backdrop-blur-md hidden md:block shadow-2xl">
          <p className="text-[10px] font-bold text-orange-500 mb-2 font-mono border-b border-orange-900/30 pb-1 uppercase tracking-widest">Analytic Legend</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#F97316] shadow-[0_0_5px_#F97316]"></div>
              <span className="text-[10px] text-neutral-400 font-mono">HIDDEN SITE</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#3B82F6] shadow-[0_0_5px_#3B82F6]"></div>
              <span className="text-[10px] text-neutral-400 font-mono">EMAIL ADDR</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#F59E0B] shadow-[0_0_5px_#F59E0B]"></div>
              <span className="text-[10px] text-neutral-400 font-mono">BTC WALLET</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#10B981] shadow-[0_0_5px_#10B981]"></div>
              <span className="text-[10px] text-neutral-400 font-mono">PGP PUBLIC</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#EF4444] shadow-[0_0_5px_#EF4444]"></div>
              <span className="text-[10px] text-neutral-400 font-mono">XMR WALLET</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#8B5CF6] shadow-[0_0_5px_#8B5CF6]"></div>
              <span className="text-[10px] text-neutral-400 font-mono">ETH WALLET</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
