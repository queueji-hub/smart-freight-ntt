import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/db";
import { parseEmailToShipment } from "@/lib/aiParser";
import { generateJobNo, isValidJobType, JobType } from "@/lib/jobNumber";

const RequestSchema = z.object({
  text: z.string().min(10, "Text too short"),
  autoSave: z.boolean().default(true),
});

const STANDARD_MILESTONES_SE = [
  ["BKD", "Booking Confirmed"],
  ["PUC", "Pick-up Container"],
  ["STF", "Stuffed at Origin"],
  ["RTN", "Container Returned"],
  ["CCL", "Customs Cleared"],
  ["ETD", "Vessel Departed"],
  ["ITT", "In Transit"],
  ["ETA", "Vessel Arrived"],
  ["DLV", "Delivered"],
];

const STANDARD_MILESTONES_SI = [
  ["BKD", "Booking Confirmed"],
  ["ETD", "Vessel Departed Origin"],
  ["ITT", "In Transit"],
  ["ETA", "Vessel Arrived Thailand"],
  ["DSC", "Container Discharged"],
  ["CCL", "Customs Cleared"],
  ["PUC", "Container Pick-up"],
  ["DLV", "Delivered to Consignee"],
];

function getMilestonesFor(jobType: string) {
  return jobType === "SI" ? STANDARD_MILESTONES_SI : STANDARD_MILESTONES_SE;
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { text, autoSave } = RequestSchema.parse(body);

    // Step 1: Parse with AI
    const result = await parseEmailToShipment(text);
    const parsed = result.data;

    // Step 2: Log AI call
    const aiLog = await prisma.aiLog.create({
      data: {
        agent: "EMAIL_PARSER",
        inputText: text,
        outputJson: JSON.stringify(parsed),
        model: result.model,
        confidence: parsed.confidence,
        status: result.error ? "FAILED" : "SUCCESS",
        errorMessage: result.error,
      },
    });

    // Step 3: If autoSave, create shipment + customer + milestones
    let shipment = null;
    if (autoSave && parsed.jobType && isValidJobType(parsed.jobType)) {
      // Upsert customer
      let customerId: string | undefined;
      if (parsed.customerName?.trim()) {
        const customer = await prisma.customer.upsert({
          where: { id: "non-existent" }, // force create-or-find by name lookup below
          create: {
            companyName: parsed.customerName,
            contactName: parsed.contactName,
            email: parsed.contactEmail,
            phone: parsed.contactPhone,
          },
          update: {},
        }).catch(async () => {
          const existing = await prisma.customer.findFirst({
            where: { companyName: parsed.customerName! },
          });
          if (existing) return existing;
          return prisma.customer.create({
            data: {
              companyName: parsed.customerName!,
              contactName: parsed.contactName,
              email: parsed.contactEmail,
              phone: parsed.contactPhone,
            },
          });
        });
        customerId = customer.id;
      }

      const jobNo = await generateJobNo(parsed.jobType as JobType);

      shipment = await prisma.shipment.create({
        data: {
          jobNo,
          jobType: parsed.jobType,
          status: "DRAFT",
          customerId,
          shipperConsignee: parsed.shipperConsignee,
          carrier: parsed.carrier,
          pol: parsed.pol,
          pod: parsed.pod,
          containerNo: parsed.containerNo,
          containerSize: parsed.containerSize,
          commodity: parsed.commodity,
          weight: parsed.weight,
          quantityDesc: parsed.quantityDesc,
          incoterm: parsed.incoterm,
          etd: parsed.etd ? new Date(parsed.etd) : null,
          eta: parsed.eta ? new Date(parsed.eta) : null,
          remark: parsed.summary,
          source: "AI_EMAIL",
          milestones: {
            create: getMilestonesFor(parsed.jobType).map(([code, name], i) => ({
              code,
              name,
              sortOrder: i,
            })),
          },
        },
        include: { milestones: true, customer: true },
      });

      // Update aiLog with shipment ref
      await prisma.aiLog.update({
        where: { id: aiLog.id },
        data: { shipmentId: shipment.id },
      });
    }

    return NextResponse.json({
      ok: true,
      method: result.method,
      parsed,
      shipment,
      aiLogId: aiLog.id,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ ok: false, error: message }, { status: 400 });
  }
}
