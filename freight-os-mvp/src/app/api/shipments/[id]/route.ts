import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const shipment = await prisma.shipment.findUnique({
    where: { id: params.id },
    include: {
      customer: true,
      milestones: { orderBy: { sortOrder: "asc" } },
      aiLogs: { orderBy: { createdAt: "desc" }, take: 5 },
    },
  });
  if (!shipment) {
    return NextResponse.json({ ok: false, error: "Not found" }, { status: 404 });
  }
  return NextResponse.json({ ok: true, shipment });
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  const allowed = [
    "status", "carrier", "pol", "pod", "containerNo", "containerSize",
    "commodity", "weight", "quantityDesc", "incoterm", "remark",
  ];
  const data: any = {};
  for (const key of allowed) if (key in body) data[key] = body[key];
  if (body.etd !== undefined) data.etd = body.etd ? new Date(body.etd) : null;
  if (body.eta !== undefined) data.eta = body.eta ? new Date(body.eta) : null;

  const shipment = await prisma.shipment.update({
    where: { id: params.id },
    data,
    include: { customer: true, milestones: true },
  });
  return NextResponse.json({ ok: true, shipment });
}
