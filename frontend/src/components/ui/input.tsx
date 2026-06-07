import { InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-12 w-full rounded-input border border-line bg-surface-secondary px-4 text-body-md text-text-primary outline-none",
        "transition-all duration-200",
        "placeholder:text-text-muted",
        "focus:border-gold focus:shadow-gold-glow",
        className
      )}
      {...props}
    />
  );
}
