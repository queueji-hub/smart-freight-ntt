import OpenAI from "openai";
import { ParsedShipment, ParsedShipmentSchema, SYSTEM_PROMPT } from "./aiSchema";

const HEURISTIC_FALLBACK: ParsedShipment = {
  jobType: null,
  customerName: null,
  shipperConsignee: null,
  contactName: null,
  contactEmail: null,
  contactPhone: null,
  carrier: null,
  pol: null,
  pod: null,
  containerSize: null,
  containerNo: null,
  commodity: null,
  weight: null,
  quantityDesc: null,
  incoterm: null,
  etd: null,
  eta: null,
  items: [],
  confidence: "low",
  missingInfo: [],
  summary: "",
};

/**
 * Parse customer email/text into structured shipment data.
 * Uses OpenAI structured outputs + Zod validation.
 * Falls back to heuristic regex parsing when no API key.
 */
export async function parseEmailToShipment(text: string): Promise<{
  data: ParsedShipment;
  method: "ai" | "heuristic";
  model?: string;
  error?: string;
}> {
  if (!text || !text.trim()) {
    return { data: HEURISTIC_FALLBACK, method: "heuristic", error: "Empty input" };
  }

  const apiKey = process.env.OPENAI_API_KEY;

  if (!apiKey) {
    return { data: heuristicParse(text), method: "heuristic" };
  }

  try {
    const client = new OpenAI({ apiKey });
    const completion = await client.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: text },
      ],
      response_format: { type: "json_object" },
      temperature: 0.1,
    });

    const content = completion.choices[0]?.message?.content ?? "{}";
    const raw = JSON.parse(content);
    const parsed = ParsedShipmentSchema.parse(raw);

    return { data: parsed, method: "ai", model: "gpt-4o-mini" };
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    return {
      data: heuristicParse(text),
      method: "heuristic",
      error: msg,
    };
  }
}

function heuristicParse(text: string): ParsedShipment {
  const t = text.toLowerCase();
  const out: ParsedShipment = { ...HEURISTIC_FALLBACK };

  // Job type
  if (/sea\s*export/.test(t)) out.jobType = "SE";
  else if (/sea\s*import/.test(t)) out.jobType = "SI";
  else if (/air\s*export/.test(t)) out.jobType = "AE";
  else if (/air\s*import/.test(t)) out.jobType = "AI";
  else if (/truck\s*export/.test(t)) out.jobType = "TE";
  else if (/truck\s*import/.test(t)) out.jobType = "TI";

  // Phone (Thai or international)
  const phone = text.match(/(?:\+?\d{1,3}[\s-]?)?\(?\d{2,3}\)?[\s-]?\d{3,4}[\s-]?\d{4}/);
  if (phone) out.contactPhone = phone[0].trim();

  // Email
  const email = text.match(/[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}/i);
  if (email) out.contactEmail = email[0];

  // Carriers
  const carriers = ["MAERSK", "MSC", "CMA", "ONE", "EVERGREEN", "COSCO", "OOCL",
    "HAPAG", "ZIM", "SITC", "PIL", "WAN HAI", "YANG MING", "HMM", "KMTC"];
  for (const c of carriers) if (t.includes(c.toLowerCase())) { out.carrier = c; break; }

  // Incoterm
  for (const i of ["FOB", "CIF", "DAP", "DDP", "DDU", "EXW", "C&F"])
    if (t.includes(i.toLowerCase())) { out.incoterm = i; break; }

  // Container size
  const cs = text.match(/(20|40)\s*(GP|HC|HQ|OT|FR)/i);
  if (cs) out.containerSize = `${cs[1]}${cs[2].toUpperCase()}`;

  out.summary = text.slice(0, 120) + (text.length > 120 ? "..." : "");
  return out;
}
