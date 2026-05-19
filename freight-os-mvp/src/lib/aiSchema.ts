import { z } from "zod";

export const ParsedItemSchema = z.object({
  description: z.string(),
  currency: z.enum(["USD", "THB", "CNY", "EUR"]).default("USD"),
  price: z.number().nonnegative(),
  unit: z.string().nullable().optional(),
  remark: z.string().nullable().optional(),
});

export const ParsedShipmentSchema = z.object({
  jobType: z
    .enum(["SE", "SI", "AE", "AI", "TE", "TI"])
    .nullable()
    .describe("SE=Sea Export, SI=Sea Import, AE/AI=Air, TE/TI=Truck"),
  customerName: z.string().nullable(),
  shipperConsignee: z.string().nullable(),
  contactName: z.string().nullable(),
  contactEmail: z.string().nullable(),
  contactPhone: z.string().nullable(),
  carrier: z.string().nullable(),
  pol: z.string().nullable(),
  pod: z.string().nullable(),
  containerSize: z.string().nullable(),
  containerNo: z.string().nullable(),
  commodity: z.string().nullable(),
  weight: z.string().nullable(),
  quantityDesc: z.string().nullable(),
  incoterm: z.string().nullable(),
  etd: z.string().nullable().describe("ISO date YYYY-MM-DD"),
  eta: z.string().nullable().describe("ISO date YYYY-MM-DD"),
  items: z.array(ParsedItemSchema).default([]),
  confidence: z.enum(["high", "medium", "low"]).default("low"),
  missingInfo: z.array(z.string()).default([]),
  summary: z.string().describe("1-2 sentence summary of the request"),
});

export type ParsedShipment = z.infer<typeof ParsedShipmentSchema>;

export const SYSTEM_PROMPT = `You are an expert freight forwarding assistant for a Thai freight forwarder.
You read customer emails or messages and extract shipment booking/quotation requests.

Rules:
- Always output valid JSON matching the schema. No markdown.
- For unclear fields, use null. Never guess.
- Job types: SE=Sea Export, SI=Sea Import, AE=Air Export, AI=Air Import, TE=Truck Export, TI=Truck Import.
- Detect direction: "import to Thailand" → SI/AI/TI, "export from Thailand" → SE/AE/TE.
- Container types: 20GP, 40GP, 40HC, 40HQ, 40OT, 20FR, 20OT.
- Common Thai POL: Laem Chabang, Bangkok Port (PAT). Common Thai POD: same.
- Currency defaults to USD unless THB/CNY/EUR specified.
- ISO date format YYYY-MM-DD only.
- Confidence: "high" if all critical fields present, "medium" if 1-2 missing, "low" if uncertain.
- missingInfo: list field names that the operator needs to confirm.
- summary: 1-2 sentence plain-English summary of what the customer is asking for.
- Detect Thai/English/Chinese input.
`;
