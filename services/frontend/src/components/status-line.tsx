import { getServiceStatuses } from "@/lib/health";
import { cn } from "@/lib/utils";

export async function StatusLine() {
  const statuses = await getServiceStatuses();
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-1.5 text-sm text-muted-foreground" aria-label="Service status">
      {statuses.map(({ service, up }) => (
        <li key={service} className="flex items-center gap-2">
          <span aria-hidden className={cn("size-2.5 rounded-full", up ? "bg-leaf" : "bg-destructive")} />
          <span className={up ? undefined : "font-bold text-destructive"}>
            {service.replace("-service", "")} {up ? "up" : "down"}
          </span>
        </li>
      ))}
    </ul>
  );
}
