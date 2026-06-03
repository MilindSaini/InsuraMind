"use client";

import { AlertTriangle, BadgeCheck, Clock, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { Chunk, Entity, InsightResponse } from "@/types";

export function InsightPanel({ insights }: { insights?: InsightResponse }) {
  if (!insights) {
    return <Card><CardContent className="text-sm text-muted">Insights will appear after processing.</CardContent></Card>;
  }
  return (
    <div className="space-y-4">
      <EntityCard entities={insights.entities} />
      <ChunkCard title="Coverage" icon={<BadgeCheck className="h-4 w-4 text-ok" />} chunks={insights.coverage} />
      <ChunkCard title="Exclusions" icon={<ShieldAlert className="h-4 w-4 text-risk" />} chunks={insights.exclusions} />
      <ChunkCard title="Waiting Periods" icon={<Clock className="h-4 w-4 text-brand" />} chunks={insights.waitingPeriods} />
      <ChunkCard title="Risk Alerts" icon={<AlertTriangle className="h-4 w-4 text-risk" />} chunks={insights.riskAlerts} />
    </div>
  );
}

function EntityCard({ entities }: { entities: Entity[] }) {
  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold">Extracted Facts</h2>
      </CardHeader>
      <CardContent className="space-y-2">
        {entities.length === 0 ? (
          <p className="text-sm text-muted">No structured facts extracted yet.</p>
        ) : (
          entities.slice(0, 10).map((entity) => (
            <div key={entity.id} className="flex items-start justify-between gap-3 text-sm">
              <span className="capitalize text-muted">{entity.entityType.replaceAll("_", " ")}</span>
              <span className="text-right font-medium">{entity.entityValue}</span>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

function ChunkCard({ title, icon, chunks }: { title: string; icon: React.ReactNode; chunks: Chunk[] }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          {icon}
          <h2 className="text-sm font-semibold">{title}</h2>
        </div>
        <Badge>{chunks.length}</Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        {chunks.length === 0 ? (
          <p className="text-sm text-muted">No matching clauses found.</p>
        ) : (
          chunks.slice(0, 3).map((chunk) => (
            <article key={chunk.id} className="rounded-md border border-line bg-panel p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="truncate text-sm font-medium">{chunk.heading || chunk.sectionType.replaceAll("_", " ")}</p>
                <Badge className={chunk.riskLevel === "high" ? "border-red-200 bg-red-50 text-risk" : ""}>
                  {chunk.citationLabel || `p.${chunk.pageNumber || "?"}`}
                </Badge>
              </div>
              <p className="line-clamp-4 text-sm text-muted">{chunk.text}</p>
            </article>
          ))
        )}
      </CardContent>
    </Card>
  );
}
