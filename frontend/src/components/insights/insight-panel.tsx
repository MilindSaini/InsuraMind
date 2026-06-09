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

      {/* Risk Alerts */}
      <RiskAlertCard chunks={insights.riskAlerts} />

      {/* Dynamic Sections */}
      {insights.sections && Object.keys(insights.sections).length > 0 ? (
        Object.entries(insights.sections).map(([sectionKey, chunks]) => {
          let badgeVariant: "success" | "failed" | "info" | "gold" = "success";
          let icon = <BadgeCheck className="h-4 w-4 text-emerald" />;
          
          if (["exclusion", "default", "liability", "risk"].includes(sectionKey)) {
            badgeVariant = "failed";
            icon = <ShieldAlert className="h-4 w-4 text-danger" />;
          } else if (["waiting_period", "prepayment", "validity", "confidential", "redemption", "anti_dilution"].includes(sectionKey)) {
            badgeVariant = "info";
            icon = <Clock className="h-4 w-4 text-accent" />;
          } else if (["claim_rule", "repayment", "obligations", "investment", "definition", "security", "address", "termination", "rating", "rights", "renewal", "fees", "authority", "dispute", "governance", "liquidation", "exit", "vesting", "general"].includes(sectionKey)) {
            badgeVariant = "info";
            icon = <BadgeCheck className="h-4 w-4 text-accent" />;
          }

          return (
            <ChunkCard
              key={sectionKey}
              title={sectionKey.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
              icon={icon}
              chunks={chunks}
              borderClass={`insight-${sectionKey}`}
              badgeVariant={badgeVariant}
            />
          );
        })
      ) : (
        <>
          {/* Legacy Coverage */}
          <ChunkCard
            title="Coverage"
            icon={<BadgeCheck className="h-4 w-4 text-emerald" />}
            chunks={insights.coverage}
            borderClass="insight-coverage"
            badgeVariant="success"
          />

          {/* Legacy Exclusions */}
          <ChunkCard
            title="Exclusions"
            icon={<ShieldAlert className="h-4 w-4 text-danger" />}
            chunks={insights.exclusions}
            borderClass="insight-exclusion"
            badgeVariant="failed"
          />

          {/* Legacy Waiting Periods */}
          <ChunkCard
            title="Waiting Periods"
            icon={<Clock className="h-4 w-4 text-accent" />}
            chunks={insights.waitingPeriods}
            borderClass="insight-waiting"
            badgeVariant="info"
          />
        </>
      )}

      {/* Extracted Facts */}
      <EntityCard entities={insights.entities} />
    </div>
  );
}

function EntityCard({ entities }: { entities: Entity[] }) {
  return (
    <div className="rounded-card border border-line bg-white p-5">
      <h3 className="mb-4 font-heading text-sm font-semibold text-text-primary">Extracted Facts</h3>
      {!entities || entities.length === 0 ? (
        <div className="rounded bg-surface-secondary p-4 text-center border border-dashed border-border-subtle">
          <p className="text-body-sm text-text-muted">No structured facts extracted yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 max-h-[240px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-line scrollbar-track-transparent">
          {entities.map((entity) => (
            <div key={entity.id} className="flex flex-col rounded-input border border-border-subtle bg-surface-secondary p-3">
              <p className="text-caption font-semibold uppercase text-text-muted mb-1 line-clamp-2">{entity.entityType.replaceAll("_", " ")}</p>
              <p className="text-sm font-medium text-text-primary whitespace-normal">{entity.entityValue}</p>
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
          {chunks?.length || 0} {(chunks?.length === 1) ? "Clause" : "Clauses"}
        </Badge>
      </div>
      {!chunks || chunks.length === 0 ? (
        <p className="text-body-sm text-text-muted">No matching clauses found.</p>
      ) : (
        <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2">
          {chunks.map((chunk) => (
            <div key={chunk.id} className="flex flex-col gap-2 rounded-input border border-border-subtle bg-surface-secondary p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="text-body-sm text-text-secondary whitespace-pre-wrap">
                  {chunk.heading && <strong className="block mb-1 text-text-primary">{chunk.heading}</strong>}
                  {chunk.text}
                </div>
                <Badge variant="default" className="shrink-0 text-[11px]">
                  {chunk.citationLabel || `p.${chunk.pageNumber || "?"}`}
                </Badge>
              </div>
              {(chunk.riskLevel === 'high' || chunk.riskLevel === 'medium') && (
                <div className="mt-2 text-xs rounded border border-warning/30 bg-warning/10 p-2 text-warning flex items-start gap-2">
                  <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold uppercase mr-1">{chunk.riskLevel} RISK</span>
                    {chunk.riskScore && <span className="opacity-75 mr-2">(Score: {chunk.riskScore})</span>}
                    {chunk.riskReason && <span className="opacity-90">{chunk.riskReason}</span>}
                  </div>
                </div>
              )}
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
      <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
        {chunks.map((chunk) => (
          <p key={chunk.id} className="text-body-sm text-text-secondary whitespace-pre-wrap">
            {chunk.text}
          </p>
        ))}
      </div>
    </div>
  );
}
