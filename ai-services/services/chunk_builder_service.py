from models.schemas import Chunk

class ChunkBuilderService:
    """Builds Chunk models from the extracted clauses."""
    def build_chunks(self, clauses: list[dict]) -> list[Chunk]:
        chunks = []
        for i, item in enumerate(clauses):
            sec = item.get("source_section", {})
            text = item.get("value", "")
            
            chunk = Chunk(
                chunkIndex=i,
                sectionType=sec.get("section_type", "general"),
                heading=item.get("title", sec.get("heading")),
                parentHeading=sec.get("heading"),
                text=text,
                pageNumber=sec.get("page_number"),
                riskLevel=item.get("risk_level", "low"),
                riskScore=item.get("risk_score", 0.0),
                riskReason=item.get("risk_reason", ""),
                importance="critical" if item.get("risk_level") == "high" else "normal",
                citationLabel=f"p.{sec.get('page_number', 1)} c.{i + 1}"
            )
            chunks.append(chunk)
        return chunks
