import Link from "next/link";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { ServiceError } from "@/lib/http";

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

/** Shows what failed and where, never a stack trace. `retryHref` reloads the same page. */
export function Problem({ error, what, retryHref }: { error: ServiceError; what: string; retryHref: string }) {
  const canRetry = error.status === 0 || error.status >= 500;
  return (
    <Alert className="border-destructive/40 bg-danger-tint text-foreground">
      <AlertTitle className="font-heading text-base font-bold text-destructive">{headline(error, what)}</AlertTitle>
      <AlertDescription className="text-sm text-foreground">
        <p>{error.detail}</p>
        {error.retryAfterS ? <p className="mt-1">Try again in about {error.retryAfterS} seconds.</p> : null}
        <p className="mt-3 flex gap-4 font-bold">
          {canRetry ? (
            <Link href={retryHref} className="underline underline-offset-4">
              Try again
            </Link>
          ) : null}
          <Link href="/" className="underline underline-offset-4">
            Back to farms
          </Link>
        </p>
      </AlertDescription>
    </Alert>
  );
}
