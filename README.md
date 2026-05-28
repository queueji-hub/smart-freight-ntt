# 🚢 Smart Freight NTT,

ระบบจัดการ Freight Forwarder สำหรับ Nattayaraat Co., Ltd.
ใช้ Python Streamlit + SQLite — ใช้งานง่าย, deploy เร็ว

## ✨ ฟีเจอร์

- **📊 Dashboard** — KPIs + รายการ shipments + กรอง/ค้นหา + สร้าง/แก้ไข ในหน้าเดียว
- **📄 Quotation** — สร้างใบเสนอราคา PDF (A4) + ระบบ Job Number อัตโนมัติ (SE/SI/AE/AI/TE/TI)
  - แก้ไข, copy, ค้นหา quotation เก่า
  - Customer database พร้อม autocomplete
  - แทรก/เลื่อน items ได้
- **📦 Shipments** — ใบคุมงาน + อัปเดตสถานะ + ส่งออก CSV

## 🚀 รันบนเครื่องตัวเอง

ต้องมี Python 3.11+ ติดตั้งแล้ว

```bash
# 1. Clone โปรเจกต์
git clone https://github.com/YOUR_USERNAME/smart-freight-ntt.git
cd smart-freight-ntt

# 2. ติดตั้ง dependencies
pip install -r requirements.txt

# 3. รัน
streamlit run Dashboard.py
```

เปิด http://localhost:8501

## 🔧 ตั้งค่า (Optional)

### OpenAI API (สำหรับ AI Quote Parser)

1. คัดลอก `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml`
2. ใส่ API key:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```

### Logo บริษัท

วาง `logo.png` ที่ `assets/logo.png` — จะแสดงในใบเสนอราคา PDF อัตโนมัติ

## ☁️ Deploy ขึ้น Streamlit Cloud (ฟรี)

1. Push repo นี้ขึ้น GitHub (public)
2. ไปที่ https://share.streamlit.io
3. Sign in with GitHub → New app
4. เลือก repo, branch `main`, main file `Dashboard.py`
5. App settings → Secrets → ใส่ `OPENAI_API_KEY` (ถ้ามี)
6. Deploy

หมายเหตุ: Streamlit Cloud ใช้ ephemeral filesystem — SQLite data จะหายเมื่อ app restart
ถ้าต้องการ data ถาวร ใช้ Supabase/Neon (PostgreSQL ฟรี) แทน

## 📁 โครงสร้างโปรเจกต์

```
smart-freight-ntt/
├── Dashboard.py              # Main entry — CRM + Shipment + Finance
├── pages/
│   ├── 1_Quotation.py        # Quotation generator
│   └── 2_Shipments.py        # Shipment job control
├── managers/                 # Business logic
│   ├── shipment_manager.py
│   ├── quotation_manager.py
│   ├── customer_manager.py
│   ├── milestone_manager.py
│   ├── job_number.py
│   └── ai_quote_parser.py    # OpenAI integration
├── pdf/
│   └── quotation_pdf.py      # ReportLab A4 PDF generator
├── database/
│   └── connection.py         # SQLite + schema
├── utils/
│   └── nav.py                # Sidebar helpers
├── config.py                 # Company info
├── assets/                   # Logo, etc.
└── requirements.txt
```

## 🔢 Job Number Format

```
{TYPE}{YY}{MM}{NNNN}
```

| Code | Type         | Example      |
|------|--------------|--------------|
| SE   | Sea Export   | SE25050001   |
| SI   | Sea Import   | SI25050042   |
| AE   | Air Export   | AE25050001   |
| AI   | Air Import   | AI25050001   |
| TE   | Truck Export | TE25050001   |
| TI   | Truck Import | TI25050001   |

## 📝 License

Proprietary — Nattayaraat Co., Ltd.
