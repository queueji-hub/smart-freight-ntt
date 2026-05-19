import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const status = searchParams.get("status");
  const q = searchParams.get("q");

  const where: any = {};
  if (status) where.status = status;
  if (q) {
    where.OR = [
      { jobNo: { contains: q } },
      { containerNo: { contains: q } },
      { pol: { contains: q } },
      { pod: { contains: q } },
      { customer: { companyName: { contains: q } } },
    ];
  }

  const shipments = await prisma.shipment.findMany({
    where,
    include: { customer: true, milestones: { orderBy: { sortOrder: "asc" } } },
    orderBy: { createdAt: "desc" },
    take: 100,
  });

  return NextResponse.json({ ok: true, shipments });
}
