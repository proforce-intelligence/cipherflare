import logging
from typing import List, Dict, Any
import uuid

logger = logging.getLogger(__name__)

class GraphService:
    @staticmethod
    def build_network_graph(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Builds a high-fidelity node-link graph from findings.
        Nodes: 
          - Findings (Onion Sites)
          - Entities (BTC, Emails, PGP, etc.)
        Edges:
          - Relational labels (e.g., "MINTED_BY", "STATED_IN")
        """
        nodes = []
        links = []
        seen_nodes = {} # node_id -> node_obj
        
        # Node styling config
        TYPE_COLORS = {
            "finding": "#F97316", # Orange
            "emails": "#3B82F6",  # Blue
            "btc_addresses": "#F59E0B", # Yellow/Gold
            "eth_addresses": "#8B5CF6", # Purple
            "pgp_keys": "#10B981", # Green
            "xmr_addresses": "#EF4444" # Red
        }

        for finding in findings:
            fid = finding.get("id") or str(uuid.uuid4())
            url = finding.get("url", "Unknown")
            
            # 1. Add/Update Finding Node
            if fid not in seen_nodes:
                node = {
                    "id": fid,
                    "label": url.split("//")[-1].split("/")[0], # Clean host
                    "type": "finding",
                    "full_url": url,
                    "risk_level": finding.get("risk_level", "low"),
                    "color": TYPE_COLORS["finding"],
                    "size": 15 + (finding.get("risk_score", 0) / 5) # Larger if higher risk
                }
                seen_nodes[fid] = node
                nodes.append(node)
            
            # 2. Extract and link entities
            entities = finding.get("entities", {})
            for etype, evalues in entities.items():
                if not evalues: continue
                
                for val in evalues:
                    eid = f"entity_{etype}_{val}"
                    
                    # Add/Update Entity Node
                    if eid not in seen_nodes:
                        enode = {
                            "id": eid,
                            "label": val[:20] + "..." if len(val) > 20 else val,
                            "type": etype,
                            "full_value": val,
                            "color": TYPE_COLORS.get(etype, "#94A3B8"),
                            "size": 10
                        }
                        seen_nodes[eid] = enode
                        nodes.append(enode)
                    else:
                        # Increase size if entity is found in multiple places
                        seen_nodes[eid]["size"] += 2

                    # Add Rich Edge
                    links.append({
                        "source": fid,
                        "target": eid,
                        "label": etype.replace("_", " ").upper(),
                        "type": etype,
                        "value": 2
                    })

        # Calculate connectivity score for sorting/layout
        for link in links:
            source = seen_nodes.get(link["source"])
            target = seen_nodes.get(link["target"])
            if source and target:
                source.setdefault("weight", 0)
                target.setdefault("weight", 0)
                source["weight"] += 1
                target["weight"] += 1

        return {
            "nodes": nodes,
            "links": links,
            "summary": {
                "total_findings": len(findings),
                "total_nodes": len(nodes),
                "total_links": len(links)
            }
        }

graph_service = GraphService()
