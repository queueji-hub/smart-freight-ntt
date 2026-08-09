/**
 * Freight Forwarding ERP Document Management Engine
 * Express REST Controller Endpoints
 */

import { Request, Response } from 'express';
import { DocumentService } from '../services/document.service';
import { AutofillService } from '../services/autofill.service';
import { CustomerProfile, ContainerSizeType, CurrencyCode } from '../types/document.types';

export class DocumentController {
  private documentService: DocumentService;

  constructor() {
    this.documentService = new DocumentService();
  }

  /**
   * Mock CRM Database Lookup for Demonstration Architecture
   */
  public static async mockGetCustomerProfile(customerId: string): Promise<CustomerProfile | null> {
    const mockCustomers: Record<string, CustomerProfile> = {
      'CUST-001': {
        id: 'CUST-001',
        code: 'NATT-001',
        name: 'Nattayaraat Logistics Trading Ltd',
        taxId: '0735568004823',
        paymentTermDays: 30,
        creditLimitThb: 1000000.0,
        currentOutstandingThb: 250000.0,
        hasOverdueInvoices: false
      },
      'CUST-OVERDUE': {
        id: 'CUST-OVERDUE',
        code: 'RISK-999',
        name: 'High Risk Trade Corp',
        taxId: '0105559998881',
        paymentTermDays: 15,
        creditLimitThb: 300000.0,
        currentOutstandingThb: 350000.0,
        hasOverdueInvoices: true
      }
    };

    return mockCustomers[customerId] || mockCustomers['CUST-001'];
  }

  /**
   * Endpoint: Create Quotation Document
   * POST /api/v1/documents/quotations
   */
  public createQuotation = async (req: Request, res: Response): Promise<void> => {
    try {
      const quotation = await this.documentService.createQuotation(req.body);
      res.status(201).json({
        success: true,
        message: 'Quotation Document Draft Created Successfully',
        data: quotation
      });
    } catch (error: any) {
      res.status(500).json({ success: false, message: error.message });
    }
  };

  /**
   * Endpoint: Create HBL Draft Document
   * POST /api/v1/documents/hbl
   */
  public createHbl = async (req: Request, res: Response): Promise<void> => {
    try {
      const hbl = await this.documentService.createHbl(req.body);
      res.status(201).json({
        success: true,
        message: 'HBL Document Created Successfully',
        data: hbl
      });
    } catch (error: any) {
      res.status(500).json({ success: false, message: error.message });
    }
  };

  /**
   * Endpoint: Issue HBL Document (Guard Middleware Active)
   * POST /api/v1/documents/hbl/issue
   */
  public issueHbl = async (req: Request, res: Response): Promise<void> => {
    try {
      const hbl = await this.documentService.createHbl(req.body);
      hbl.status = 'ISSUED';
      res.status(200).json({
        success: true,
        message: 'HBL Document Officially Issued & Locked',
        data: hbl
      });
    } catch (error: any) {
      res.status(500).json({ success: false, message: error.message });
    }
  };

  /**
   * Endpoint: Create Commercial Invoice Document
   * POST /api/v1/documents/invoices
   */
  public createInvoice = async (req: Request, res: Response): Promise<void> => {
    try {
      const customerId = req.body.customerId || 'CUST-001';
      const customer = await DocumentController.mockGetCustomerProfile(customerId);

      if (!customer) {
        res.status(404).json({ success: false, message: 'Customer account not found' });
        return;
      }

      const invoice = await this.documentService.createInvoice(req.body, customer);
      res.status(201).json({
        success: true,
        message: 'Commercial Invoice Document Created Successfully',
        data: invoice
      });
    } catch (error: any) {
      res.status(500).json({ success: false, message: error.message });
    }
  };

  /**
   * Endpoint: Issue Commercial Invoice Document (Credit Guard Active)
   * POST /api/v1/documents/invoices/issue
   */
  public issueInvoice = async (req: Request, res: Response): Promise<void> => {
    try {
      const customerId = req.body.customerId || 'CUST-001';
      const customer = await DocumentController.mockGetCustomerProfile(customerId);

      if (!customer) {
        res.status(404).json({ success: false, message: 'Customer account not found' });
        return;
      }

      const invoice = await this.documentService.createInvoice(req.body, customer);
      invoice.status = 'ISSUED';
      res.status(200).json({
        success: true,
        message: 'Commercial Invoice Issued & Finalized in Financial Ledger',
        data: invoice
      });
    } catch (error: any) {
      res.status(500).json({ success: false, message: error.message });
    }
  };

  /**
   * Utility Endpoint: Auto-fill Container Tare Specs
   * GET /api/v1/documents/autofill/container-spec/:sizeType
   */
  public getContainerSpec = async (req: Request, res: Response): Promise<void> => {
    const sizeType = (req.params.sizeType || '40HC').toUpperCase() as ContainerSizeType;
    const spec = AutofillService.getContainerSpec(sizeType);
    res.status(200).json({ success: true, data: spec });
  };

  /**
   * Utility Endpoint: Convert Amount into Words (THB & USD)
   * POST /api/v1/documents/autofill/amount-in-words
   */
  public getAmountInWords = async (req: Request, res: Response): Promise<void> => {
    const { amount, currency } = req.body;
    const numericAmount = parseFloat(amount || 0);
    const curr = (currency || 'USD') as CurrencyCode;

    const thaiText = AutofillService.convertAmountToThaiBahtText(numericAmount);
    const englishWords = AutofillService.convertAmountToEnglishWords(numericAmount, curr);

    res.status(200).json({
      success: true,
      data: {
        numericAmount,
        currency: curr,
        thaiBahtText: thaiText,
        englishWords
      }
    });
  };
}
