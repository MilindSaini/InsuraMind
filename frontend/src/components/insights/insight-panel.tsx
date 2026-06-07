"use client";

import { AlertTriangle, BadgeCheck, Clock, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { Chunk, Entity, InsightResponse } from "@/types";

export function InsightPanel({ insights }: { insights?: InsightResponse }) {
  if (!insights) {
    return (
      <div className="rounded-card border border-line bg-white p-8 text-center">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-gold-surface">
          <BadgeCheck className="h-6 w-6 text-gold" />
        </div>
        <p className="text-body-sm text-text-muted">Insights will appear after processing.</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="font-heading text-lg font-semibold text-text-primary">Document Insights</h2>
        <Badge variant="gold">AI GENERATED</Badge>
      </div>

      {/* Extracted Facts */}
      <EntityCard entities={insights.entities} />

      {/* Coverage */}
      <ChunkCard
        title="Coverage"
        icon={<BadgeCheck className="h-4 w-4 text-emerald" />}
        chunks={insights.coverage}
        borderClass="insight-coverage"
        badgeVariant="success"
      />

      {/* Exclusions */}
      <ChunkCard
        title="Exclusions"
        icon={<ShieldAlert className="h-4 w-4 text-danger" />}
        chunks={insights.exclusions}
        borderClass="insight-exclusion"
        badgeVariant="failed"
      />

      {/* Waiting Periods */}
      <ChunkCard
        title="Waiting Periods"
        icon={<Clock className="h-4 w-4 text-accent" />}
        chunks={insights.waitingPeriods}
        borderClass="insight-waiting"
        badgeVariant="info"
      />

      {/* Risk Alerts */}
      <RiskAlertCard chunks={insights.riskAlerts} />
    </div>
  );
}

function EntityCard({ entities }: { entities: Entity[] }) {
  const displayEntities = entities.slice(0, 8);
  return (
    <div className="rounded-card border border-line bg-white p-5">
      <h3 className="mb-4 font-heading text-sm font-semibold text-text-primary">Extracted Facts</h3>
      {displayEntities.length === 0 ? (
        <p className="text-body-sm text-text-muted">No structured facts extracted yet.</p>
      ) : (
        <div className="grid grid-cols-2 gap-x-6 gap-y-3">
          {displayEntities.map((entity) => (
            <div key={entity.id}>
              <p className="text-caption uppercase text-text-muted">{entity.entityType.replaceAll("_", " ")}</p>
              <p className="text-sm font-semibold text-text-primary">{entity.entityValue}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ChunkCard({
  title,
  icon,
  chunks,
  borderClass,
  badgeVariant,
}: {
  title: string;
  icon: React.ReactNode;
  chunks: Chunk[];
  borderClass: string;
  badgeVariant: "success" | "failed" | "info" | "gold";
}) {
  return (
    <div className={`rounded-card border border-line bg-white p-5 ${borderClass}`}>
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {icon}
          <h3 className="font-heading text-sm font-semibold text-text-primary">{title}</h3>
        </div>
        <Badge variant={badgeVariant}>
          {chunks.length} {chunks.length === 1 ? "Clause" : "Clauses"}
        </Badge>
      </div>
      {chunks.length === 0 ? (
        <p className="text-body-sm text-text-muted">No matching clauses found.</p>
      ) : (
        <div className="space-y-2">
          {chunks.slice(0, 3).map((chunk) => (
            <div key={chunk.id} className="flex items-start justify-between gap-3 rounded-input border border-border-subtle bg-surface-secondary p-3">
              <p className="text-body-sm text-text-secondary line-clamp-2">
                {chunk.heading || chunk.text.slice(0, 100)}
              </p>
              <Badge variant="default" className="shrink-0 text-[11px]">
                {chunk.citationLabel || `p.${chunk.pageNumber || "?"}`}
              </Badge>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RiskAlertCard({ chunks }: { chunks: Chunk[] }) {
  if (chunks.length === 0) return null;

  const highRiskChunks = chunks.filter((c) => c.riskLevel === "high");
  return (
    <div className="rounded-card border border-line bg-warning-surface p-5 insight-risk">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-warning" />
          <h3 className="font-heading text-sm font-semibold text-text-primary">Risk Alerts</h3>
        </div>
        {highRiskChunks.length > 0 && (
          <Badge variant="failed" className="!bg-danger !text-white !border-danger">HIGH RISK</Badge>
        )}
      </div>
      <div className="space-y-2">
        {chunks.slice(0, 3).map((chunk) => (
          <p key={chunk.id} className="text-body-sm text-text-secondary">
            {chunk.text.slice(0, 200)}
          </p>
        ))}
      </div>
    </div>
  );
}
