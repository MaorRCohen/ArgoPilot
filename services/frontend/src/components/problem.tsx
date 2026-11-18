import Link from "next/link";
import { CircleAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import type { ServiceError } from "@/lib/http";
import { cn } from "@/lib/utils";

function headline(e: ServiceError, what: string): string {
  switch (e.code) {
    case "NOT_FOUND":
      return "We can't find this plot";
    case "CONFLICT":
      return "This plot's crop has no irrigation profile yet";
    case "VALIDATION":
      return "The request was not accepted";
    case "UPSTREAM_UNAVAILABLE":
      return `The ${what} can't be built right now`;
    default:
      return e.status === 0 || e.status >= 500 ? `The ${what} is not available` : `The ${what} could not be loaded`;
  }
}

/**
 * Shows what failed and where, never a stack trace. `retryHref` reloads the same page.
 * `glass` (default) sits on the photo of a scene page; `paper` sits on the paper (the home page).
 */
export function Problem({
  error,
  what,
  retryHref,
  tone = "glass",
}: {
  error: ServiceError;
  what: string;
  retryHref: string;
  tone?: "glass" | "paper";
}) {
  const canRetry = error.status === 0 || error.status >= 500;
  return (
    <Alert
      className={cn(
        "max-w-3xl gap-y-1.5 rounded-2xl border-2 border-destructive/50 px-5 py-5 text-destructive sm:px-8 sm:py-7",
        tone === "glass" ? "on-dark panel shadow-float" : "bg-danger-tint shadow-hero",
      )}
    >
      <CircleAlert className="size-7" aria-hidden />
      <AlertTitle className="font-heading text-2xl leading-tight font-bold text-destructive sm:text-3xl">
        {headline(error, what)}
      </AlertTitle>
      <AlertDescription className="text-base text-foreground sm:text-lg">
        <p>{error.detail}</p>
        {error.retryAfterS ? <p className="mt-1">Try again in about {error.retryAfterS} seconds.</p> : null}
      </AlertDescription>
      <div className="col-span-2 mt-4 flex flex-wrap gap-3 sm:col-span-1 sm:col-start-2">
        {canRetry ? (
          <Link
            href={retryHref}
            className={buttonVariants({ size: "lg", className: "h-12 px-6 text-base font-semibold" })}
          >
            Try again
          </Link>
        ) : null}
        <Link
          href="/"
          className={buttonVariants({
            variant: "outline",
            size: "lg",
            className: cn("h-12 px-6 text-base font-semibold", tone === "paper" && "border-input bg-card"),
          })}
        >
          Back to farms
        </Link>
      </div>
    </Alert>
  );
}
