import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function PATCH(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  const data: any = {};
  if ("occurredAt" in body) {
    data.occurredAt = body.occurredAt ? new Date(body.occurredAt) : null;
  }
  if ("note" in body) data.note = body.note;

  const milestone = await prisma.milestone.update({
    where: { id: params.id },
    data,
  });
  return NextResponse.json({ ok: true, milestone });
}
