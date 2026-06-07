import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "success" | "processing" | "failed" | "warning" | "info" | "gold";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: "border-line bg-panel text-text-secondary",
  success: "border-emerald/20 bg-emerald-surface text-emerald",
  processing: "border-accent/20 bg-accent-surface text-accent",
  failed: "border-danger/20 bg-danger-surface text-danger",
  warning: "border-warning/20 bg-warning-surface text-warning",
  info: "border-accent/20 bg-accent-surface text-accent",
  gold: "border-gold/20 bg-gold-surface text-gold",
};

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-badge border px-2.5 py-0.5 text-caption font-semibold",
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}
