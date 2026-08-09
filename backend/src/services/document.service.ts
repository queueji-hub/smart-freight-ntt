/**
 * Freight Forwarding ERP Document Management Engine
 * Core Service Layer Implementation
 */

import { Quotation, HouseBillOfLading, Invoice, CustomerProfile, ContainerDetail } from '../types/document.types';
import { AutofillService } from './autofill.service';
import { DocumentGuardMiddleware } from '../middlewares/document-guard.middleware';

export class DocumentService {
  /**
   * 1. Process & Instantiate Quotation Document with Auto-calculations
   */
  public async createQuotation(payload: Partial<Quotation>): Promise<Quotation> {
    const quotationDate = payload.quotationDate ? new Date(payload.quotationDate) : new Date();
    const validityDate = payload.validityDate ? new Date(payload.validityDate) : AutofillService.calculateDueDate(quotationDate, 30);

    const items = payload.items || [];
    const totalUsd = items
      .filter((i) => i.currency === 'USD')
      .reduce((sum, i) => sum + (i.unitPrice || 0), 0);

    const totalThb = items
      .filter((i) => i.currency === 'THB')
      .reduce((sum, i) => sum + (i.unitPrice || 0), 0);

    const quotation: Quotation = {
      quotationNo: payload.quotationNo || `QT-${new Date().getFullYear().toString().slice(2)}${(new Date().getMonth() + 1).toString().padStart(2, '0')}-0001`,
      jobType: payload.jobType || 'SE',
      customerId: payload.customerId || 'CUST-DEFAULT',
      customerName: payload.customerName || 'Valued Client',
      pol: payload.pol || '',
      pod: payload.pod || '',
      quotationDate,
      validityDate,
      paymentTermDays: payload.paymentTermDays || 30,
      items,
      status: 'DRAFT',
      totalAmountUsd: totalUsd,
      totalAmountThb: totalThb
    };

    return quotation;
  }

  /**
   * 2. Process & Instantiate House Bill of Lading (HBL) with Container Auto-fill
   */
  public async createHbl(payload: Partial<HouseBillOfLading>): Promise<HouseBillOfLading> {
    const containers: ContainerDetail[] = (payload.containers || []).map((c) => {
      const spec = AutofillService.getContainerSpec(c.sizeType);
      const tareKg = c.tareWeightKg || spec.tareWeightKg;
      const grossKg = c.grossWeightKg || 0;
      const vgmKg = c.vgmWeightKg || (grossKg > 0 ? grossKg + tareKg : 0);

      return {
        ...c,
        containerNumber: (c.containerNumber || '').toUpperCase().trim(),
        sealNumber: c.sealNumber || '',
        tareWeightKg: tareKg,
        vgmWeightKg: vgmKg,
        vgmMethod: c.vgmMethod || 'Method 2',
        socCoc: c.socCoc || 'COC'
      };
    });

    const totalGross = containers.reduce((sum, c) => sum + c.grossWeightKg, 0);
    const totalCbm = containers.reduce((sum, c) => sum + c.volumeCbm, 0);
    const cargoSummary = AutofillService.generateCargoSummary(containers);

    const hbl: HouseBillOfLading = {
      hblNo: payload.hblNo || `HBL-${new Date().getFullYear()}-0001`,
      jobNo: payload.jobNo || 'JOB-2026-0001',
      shipper: payload.shipper || '',
      consignee: payload.consignee || '',
      notifyParty: payload.notifyParty || 'SAME AS CONSIGNEE',
      vesselName: payload.vesselName || '',
      voyageNo: payload.voyageNo || '',
      pol: payload.pol || '',
      pod: payload.pod || '',
      shippedOnBoardDate: payload.shippedOnBoardDate ? new Date(payload.shippedOnBoardDate) : new Date(),
      issueDate: payload.issueDate ? new Date(payload.issueDate) : new Date(),
      placeOfIssue: payload.placeOfIssue || 'BANGKOK, THAILAND',
      freightTerm: payload.freightTerm || 'PREPAID',
      containers,
      cargoSummary,
      totalGrossWeightKg: totalGross,
      totalVolumeCbm: totalCbm,
      status: 'DRAFT'
    };

    return hbl;
  }

  /**
   * 3. Process & Instantiate Invoice with Amount in Words Auto-conversion
   */
  public async createInvoice(payload: Partial<Invoice>, customer: CustomerProfile): Promise<Invoice> {
    const issueDate = payload.issueDate ? new Date(payload.issueDate) : new Date();
    const dueDate = payload.dueDate ? new Date(payload.dueDate) : AutofillService.calculateDueDate(issueDate, customer.paymentTermDays);

    const currency = payload.currency || 'THB';
    const fxRate = payload.fxRateToThb || 1.0;
    const items = payload.items || [];

    let subtotal = 0;
    let vatAmount = 0;
    let whtAmount = 0;

    items.forEach((item) => {
      const lineAmount = item.quantity * item.unitPrice;
      subtotal += lineAmount;

      if (item.taxType === 'VAT_7') {
        vatAmount += lineAmount * 0.07;
      }

      if (item.whtType === 'WHT_1') {
        whtAmount += lineAmount * 0.01;
      } else if (item.whtType === 'WHT_3') {
        whtAmount += lineAmount * 0.03;
      }
    });

    const totalAmount = subtotal + vatAmount - whtAmount;
    const amountInWordsThb = AutofillService.convertAmountToThaiBahtText(totalAmount * (currency === 'THB' ? 1.0 : fxRate));
    const amountInWordsUsd = AutofillService.convertAmountToEnglishWords(totalAmount, currency);

    const invoice: Invoice = {
      docNo: payload.docNo || `INV-${new Date().getFullYear()}-0001`,
      jobNo: payload.jobNo || 'JOB-2026-0001',
      customerId: customer.id,
      customerName: customer.name,
      customerTaxId: customer.taxId,
      issueDate,
      dueDate,
      currency,
      fxRateToThb: fxRate,
      items,
      subtotal: Math.round(subtotal * 100) / 100,
      vatAmount: Math.round(vatAmount * 100) / 100,
      whtAmount: Math.round(whtAmount * 100) / 100,
      totalAmount: Math.round(totalAmount * 100) / 100,
      amountInWordsThb,
      amountInWordsUsd,
      supervisorBypassFlag: payload.supervisorBypassFlag || false,
      status: 'DRAFT'
    };

    return invoice;
  }
}
