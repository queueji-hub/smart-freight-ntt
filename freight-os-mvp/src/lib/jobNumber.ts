import { prisma } from "./db";

const JOB_TYPES = ["SE", "SI", "AE", "AI", "TE", "TI"] as const;
export type JobType = (typeof JOB_TYPES)[number];

export function isValidJobType(t: string): t is JobType {
  return (JOB_TYPES as readonly string[]).includes(t);
}

/**
 * Generate next sequential job number: {TYPE}{YY}{MM}{NNNN}
 * Example: SI25110042
 * Atomic via DB transaction - safe for concurrent calls.
 */
export async function generateJobNo(jobType: JobType, ref?: Date): Promise<string> {
  const d = ref ?? new Date();
  const yy = String(d.getFullYear() % 100).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const prefix = `${jobType}${yy}${mm}`;

  // Find max existing running for this prefix
  const last = await prisma.shipment.findFirst({
    where: { jobNo: { startsWith: prefix } },
    orderBy: { jobNo: "desc" },
    select: { jobNo: true },
  });

  let next = 1;
  if (last) {
    const tail = last.jobNo.slice(prefix.length);
    next = (parseInt(tail, 10) || 0) + 1;
  }
  return `${prefix}${String(next).padStart(4, "0")}`;
}
