# AI Freight OS — MVP Strategy & GTM

## Vision (1 sentence)

> **"ระบบจัดการ freight forwarder ที่ใช้ง่ายที่สุดในเอเชีย ให้ทีม operation 5-50 คน ทำงานเสร็จเร็วขึ้น 3 เท่า ด้วย AI ช่วย"**

ไม่ใช่ CargoWise clone ไม่ใช่ ERP ใหญ่ คือ **Operating System** ที่ FF SME ลืม Excel ไปได้

---

## Target Customer (ICP)

### ลูกค้าตัวจริง: Tier 1
- **Freight Forwarder ไทย/SEA** ขนาด 5-30 พนักงาน
- รายได้ 20-200 ล้านบาท/ปี
- ใช้ Excel + Email + LINE เป็นหลัก
- เคยลอง CargoWise แล้ว "แพงเกินไป + ใช้ยาก"
- ต้องการระบบที่ทำงานได้ทันที ไม่ต้องเทรน 3 เดือน

### ลูกค้าที่ "ใช่" แต่ "ไม่ใช่ตอนนี้"
- Enterprise FF (>100 คน) — ใช้ CargoWise อยู่แล้ว เปลี่ยนยาก
- Solo broker (1-3 คน) — Excel ก็พอใช้
- Customs broker pure-play — workflow ต่างเกินไป

---

## Pain Points ที่จะแก้ (อิงจากข้อมูลจริงของคุณ)

| # | Pain | Solution |
|---|------|----------|
| 1 | ลูกค้าโทรถาม "ของถึงไหน" ตลอดวัน | Public tracking page + LINE bot |
| 2 | ทำใบเสนอราคาใน Excel เสียเวลา 30 นาที/ใบ | AI Quote (3 นาที) |
| 3 | ใส่ข้อมูลซ้ำ 5 รอบ (Email → Excel → SAP → CW → Invoice) | Single source + auto-sync |
| 4 | OCR เอกสาร B/L, Invoice ทำมือ | AI Document Parser |
| 5 | ไม่มี dashboard ดู margin จริง | Real-time profit dashboard |
| 6 | ทีม operation ทำงาน weekend เพราะตามงานไม่ทัน | Automation + alerts |


---

## MVP Scope (90 วัน)

### ✅ MUST HAVE (Phase 1 — Day 1-90)

| Module | Features | สำคัญเพราะ |
|--------|----------|-----------|
| **Shipment** | Job creation, milestones, tracking | Core workflow |
| **Quotation** | PDF gen + customer DB + reuse | คุณมีอยู่แล้ว |
| **Public Tracking** | ลูกค้าเช็คสถานะผ่าน Job No. | คุณมีอยู่แล้ว |
| **AI Quote** | สร้างใบเสนอราคาจาก email | Killer feature #1 |
| **LINE Bot** | ลูกค้าถาม "ของถึงไหน" ผ่าน LINE | Killer feature #2 (Asia) |
| **Dashboard** | Job count, revenue, status | คุณมีอยู่แล้ว |

### 🟡 SHOULD HAVE (Phase 2 — Day 91-180)

- Document OCR (B/L, Invoice, Packing List)
- AI Email Parser (auto-create shipment draft)
- Multi-user + roles (Admin / Ops / Sales / Finance)
- Customer Portal (login → ดู shipment ตัวเอง + invoice)
- Basic Invoicing
- Container Tracking via Carrier API

### 🔴 NICE TO HAVE (Phase 3 — 6+ เดือน)

- AI Delay Prediction
- HS Code suggestion
- Multi-company / Multi-tenant SaaS
- Mobile native app
- Advanced accounting integration
- Marketplace (carrier rates)

### ❌ NOT NOW (อย่าทำ)

- Full ERP/Accounting (ใช้ Xero/QuickBooks integration แทน)
- Warehouse Management (เกิน scope SME ส่วนใหญ่)
- Carrier portal (เกิน scope)
- Blockchain (ไม่จำเป็น)

---

## Tech Stack Decision

### Phase 1 (Now → 3 เดือน): **Streamlit + SQLite → Postgres**
**ทำไม:** คุณมี Streamlit ที่ใช้งานได้แล้ว — อย่าทิ้ง  
**Migrate:** SQLite → Postgres (Supabase free tier) เพื่อ multi-user

### Phase 2 (3-6 เดือน): **Next.js + FastAPI + Postgres**
**ทำไม:** เมื่อมีลูกค้าจริง 3-5 ราย → UI ต้องโปรกว่า Streamlit  
**Migration:** Streamlit คงอยู่เป็น admin panel, Next.js เป็น customer portal

### Phase 3 (6+ เดือน): **Microservices + K8s**
**ทำไม:** เมื่อมี 50+ ลูกค้า — ก่อนหน้านี้อย่าทำ over-engineering

---

## 90-Day Roadmap

### Week 1-2: ทำให้สิ่งที่มี "พร้อมใช้กับลูกค้าจริง"
- [ ] Migrate SQLite → Supabase Postgres (multi-user safe)
- [ ] Add basic auth (username/password)
- [ ] Deploy บน Streamlit Cloud หรือ Railway
- [ ] Custom domain + SSL
- [ ] Onboard **Nattayaraat** เป็นลูกค้าจริงรายแรก (free)

### Week 3-4: AI Quote
- [ ] Email parser (OpenAI GPT-4 + Pydantic schema)
- [ ] รับ email forward → สร้าง quotation draft
- [ ] Manual review → approve → ส่ง PDF
- [ ] Train prompt บน 50 emails จริงของ Nattayaraat

### Week 5-6: LINE Bot
- [ ] LINE OA + Messaging API
- [ ] Customer พิมพ์ Job No. → bot ตอบสถานะ
- [ ] Subscribe milestone updates → push notification
- [ ] Free tier (LINE OA)

### Week 7-8: Document OCR
- [ ] Upload B/L PDF → ดึง: shipper, consignee, container, vessel
- [ ] Auto-fill shipment form
- [ ] ใช้ Google Document AI หรือ Azure Form Recognizer

### Week 9-10: Multi-user + Customer Portal
- [ ] User roles: Admin, Ops, Sales, Finance, Customer
- [ ] Customer login → ดู shipment + download invoice
- [ ] Email notifications (SendGrid)

### Week 11-12: Lead Customer Onboarding
- [ ] Sign 3 paying customers (target: 3,000-5,000 บาท/เดือน/บริษัท)
- [ ] Iterate based on feedback
- [ ] Case study + testimonial


---

## Pricing Strategy

### Tier 1: **Starter** — 2,900 บาท/เดือน (~$80)
- 3 users
- 100 shipments/เดือน
- AI quotes 30 ครั้ง/เดือน
- LINE Bot
- Email support

### Tier 2: **Pro** — 7,900 บาท/เดือน (~$220)
- 10 users
- 500 shipments/เดือน
- AI quotes 200 ครั้ง/เดือน
- Document OCR 100 หน้า/เดือน
- Customer portal
- Phone support

### Tier 3: **Business** — 19,900 บาท/เดือน (~$550)
- 30 users
- Unlimited shipments
- AI quotes unlimited
- Document OCR 1,000 หน้า/เดือน
- Multi-company
- API access
- Dedicated CSM

### Tier 4: **Enterprise** — Custom (50K+ บาท/เดือน)
- Unlimited everything
- White-label
- On-premise option
- Custom integrations
- 24/7 support
- SLA 99.9%

### เปรียบเทียบกับคู่แข่ง (เป้าหมาย)
| | CargoWise | **AI Freight OS** | ประหยัด |
|---|---|---|---|
| Monthly | ~50,000-100,000 บาท | 2,900-19,900 บาท | **80%** |
| Setup | 6-12 เดือน | 1-3 วัน | **95%** |
| Training | 40+ ชั่วโมง | 2 ชั่วโมง | **95%** |

---

## Go-To-Market (Asia SME)

### ทำไม SME ไทยเกลียด CargoWise
1. **แพง** — ค่า license $1500+/เดือน
2. **ใช้ยาก** — UI 2005, ต้อง trained operator
3. **Implementation 6-12 เดือน** — บริษัท SME รอไม่ได้
4. **Support เฉพาะ enterprise** — SME ติดต่อยาก
5. **ภาษาอังกฤษล้วน** — staff ไทยใช้ลำบาก
6. **ไม่มี LINE/WhatsApp integration**

### Competitive Advantages

| Feature | CargoWise | **AI Freight OS** |
|---------|-----------|-----|
| ราคา | $1,500-5,000/mo | $80-550/mo |
| Onboarding | 6-12 เดือน | 1-3 วัน |
| Mobile | ❌ | ✅ |
| LINE Bot | ❌ | ✅ |
| Thai/EN UI | ❌ | ✅ |
| AI Quote | ❌ | ✅ |
| AI Email Parser | ❌ | ✅ |
| Public Tracking | ❌ | ✅ |
| Public API | $$$$$ | ✅ included |
| OCR เอกสารไทย | ❌ | ✅ |

### Acquisition Channels (Phase 1)

1. **Direct outreach** — LinkedIn / Facebook Group "FF Thailand"
2. **Existing network** — Nattayaraat introduce ลูกค้าใหม่
3. **Content marketing** — บทความ "ทำใบเสนอราคาเร็วขึ้น 10x ด้วย AI"
4. **Partnership** — TIFFA (Thai International Freight Forwarders Association)
5. **Customer referral program** — ฟรี 1 เดือน/referral

### Acquisition Channels (Phase 2)

1. **Google Ads** — keyword "ระบบ freight forwarder"
2. **YouTube tutorials** — "How to manage shipment in 5 min"
3. **TIFFA conferences** — booth + demo
4. **API marketplace** — Zapier, Make integrations

---

## Investor Narrative (Pitch ใน 30 วินาที)

> **"CargoWise คือ SAP ของ freight forwarding — แพง, ช้า, สำหรับ enterprise เท่านั้น"**
> 
> **"AI Freight OS คือ Stripe ของ freight forwarding — สำหรับ SME เอเชีย 95% ที่ CargoWise เข้าไม่ถึง"**
>
> ตลาด Asian FF SME มี 50,000+ บริษัท × $200/mo = **$120M ARR opportunity**
>
> เริ่มจากไทย (1,500 FF), ขยายเวียดนาม, อินโดนีเซีย, สิงคโปร์, มาเลเซีย, ฟิลิปปินส์


---

## TAM / SAM / SOM (Asia Pacific)

| | จำนวนบริษัท | ARPU/เดือน | TAM |
|---|---|---|---|
| **TAM** Asia FF SME | 100,000+ | $200 | $240M ARR |
| **SAM** SEA FF SME | 30,000 | $200 | $72M ARR |
| **SOM 3yr** | 1,500 (5%) | $200 | **$3.6M ARR** |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| AI hallucination ใน quote | Human approval ก่อนส่ง (Phase 1) |
| ลูกค้าไม่ยอมย้ายจาก Excel | เริ่มจาก feature เสริม (tracking) ก่อน, ค่อย expand |
| CargoWise ลดราคามาแข่ง | Niche down: Asia SME, AI-first, ไม่ใช่ enterprise |
| Carrier API costs | เริ่มด้วย manual milestone update, ค่อยเชื่อม API ทีหลัง |
| Founder bandwidth | เริ่ม solo, hire dev คนแรกหลัง $5K MRR |

---

## Success Metrics (Year 1)

- **Q1**: 1 paying customer (Nattayaraat)
- **Q2**: 5 paying customers, $1.5K MRR
- **Q3**: 15 paying customers, $5K MRR
- **Q4**: 40 paying customers, $15K MRR

หลัง $15K MRR → Series A pitch ได้

---

## เริ่มต้นทำตอนนี้ (Track B)

Track A (เอกสารนี้) เสร็จแล้ว → ขั้นต่อไปคือ **Track B: ใส่ AI ใน Streamlit**

ลำดับงานที่ผมจะทำให้คุณ:
1. ✅ MVP Strategy (เอกสารนี้)
2. → **AI Quote Generator** (สัปดาห์นี้)
3. → **LINE Bot integration** (สัปดาห์หน้า)
4. → **Document OCR** (สัปดาห์ถัดไป)
5. → Multi-user auth + deploy (เดือนหน้า)

แต่ละขั้นทำเสร็จ → ทดสอบกับงานจริง Nattayaraat → เก็บ feedback → ปรับ
