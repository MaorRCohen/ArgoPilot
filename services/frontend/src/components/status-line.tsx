import { getServiceStatuses } from "@/lib/health";

export async function StatusLine() {
  const statuses = await getServiceStatuses();
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground" aria-label="Service status">
      {statuses.map(({ service, up }) => (
        <li key={service} className="flex items-center gap-1.5">
          <span
            aria-hidden
            className={`size-2 rounded-full ${up ? "bg-up" : "bg-destructive"}`}
          />
          <span className={up ? undefined : "font-bold text-destructive"}>
            {service.replace("-service", "")} {up ? "up" : "down"}
          </span>
        </li>
      ))}
    </ul>
  );
}
