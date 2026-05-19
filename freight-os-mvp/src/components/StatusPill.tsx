import clsx from "clsx";

const STATUS_STYLES: Record<string, string> = {
  DRAFT: "bg-text-tertiary/15 text-text-secondary",
  BOOKED: "bg-accent/15 text-accent",
  IN_TRANSIT: "bg-warning/15 text-warning",
  ARRIVED: "bg-success/15 text-success",
  DELIVERED: "bg-success/15 text-success",
  CANCELLED: "bg-danger/15 text-danger",
};

const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Draft",
  BOOKED: "Booked",
  IN_TRANSIT: "In Transit",
  ARRIVED: "Arrived",
  DELIVERED: "Delivered",
  CANCELLED: "Cancelled",
};

export function StatusPill({ status }: { status: string }) {
  return (
    <span className={clsx("pill", STATUS_STYLES[status] || STATUS_STYLES.DRAFT)}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {STATUS_LABEL[status] || status}
    </span>
  );
}
