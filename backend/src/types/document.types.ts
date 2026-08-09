/**
 * Freight Forwarding ERP Document Management Engine
 * TypeScript Type Definitions & Interfaces
 * CargoWise & SOLAS Standard Compliant
 */

export type JobType = 'SE' | 'SI' | 'AE' | 'AI' | 'TE' | 'TI';
export type DocumentStatus = 'DRAFT' | 'PENDING_APPROVAL' | 'ISSUED' | 'VOIDED' | 'CANCELLED';
export type ContainerSizeType = '20GP' | '40GP' | '40HC' | '45HC' | '20RF' | '40RF' | '20OT' | '40OT' | '20FR' | '40FR';
export type CurrencyCode = 'THB' | 'USD' | 'EUR' | 'CNY' | 'JPY';

export interface ContainerSpec {
  sizeType: ContainerSizeType;
  tareWeightKg: number;
  maxPayloadKg: number;
  maxCbm: number;
}

export interface ContainerDetail {
  id?: string;
  containerNumber: string;
  sizeType: ContainerSizeType;
  sealNumber: string;
  grossWeightKg: number;
  netWeightKg: number;
  tareWeightKg: number;
  vgmWeightKg: number;
  vgmMethod: 'Method 1' | 'Method 2';
  volumeCbm: number;
  socCoc: 'SOC' | 'COC';
  tempSettingC?: number;
  ventSettingPercent?: number;
}

export interface CustomerProfile {
  id: string;
  code: string;
  name: string;
  taxId: string;
  paymentTermDays: number;
  creditLimitThb: number;
  currentOutstandingThb: number;
  hasOverdueInvoices: boolean;
}

export interface QuotationItem {
  id?: string;
  description: string;
  currency: CurrencyCode;
  unitPrice: number;
  billingUnit: string;
  remark?: string;
}

export interface Quotation {
  id?: string;
  quotationNo: string;
  jobType: JobType;
  customerId: string;
  customerName: string;
  pol: string;
  pod: string;
  quotationDate: Date;
  validityDate: Date;
  paymentTermDays: number;
  items: QuotationItem[];
  status: DocumentStatus;
  totalAmountUsd: number;
  totalAmountThb: number;
}

export interface HouseBillOfLading {
  id?: string;
  hblNo: string;
  jobNo: string;
  shipper: string;
  consignee: string;
  notifyParty: string;
  vesselName: string;
  voyageNo: string;
  pol: string;
  pod: string;
  shippedOnBoardDate: Date;
  issueDate: Date;
  placeOfIssue: string;
  freightTerm: 'PREPAID' | 'COLLECT';
  containers: ContainerDetail[];
  cargoSummary: string;
  totalGrossWeightKg: number;
  totalVolumeCbm: number;
  status: DocumentStatus;
}

export interface InvoiceItem {
  id?: string;
  description: string;
  quantity: number;
  unitPrice: number;
  amount: number;
  taxType: 'VAT_7' | 'NON_VAT' | 'ADVANCE';
  whtType: 'NONE' | 'WHT_1' | 'WHT_3';
}

export interface Invoice {
  id?: string;
  docNo: string;
  jobNo: string;
  customerId: string;
  customerName: string;
  customerTaxId: string;
  issueDate: Date;
  dueDate: Date;
  currency: CurrencyCode;
  fxRateToThb: number;
  items: InvoiceItem[];
  subtotal: number;
  vatAmount: number;
  whtAmount: number;
  totalAmount: number;
  amountInWordsThb: string;
  amountInWordsUsd: string;
  supervisorBypassFlag?: boolean;
  status: DocumentStatus;
}
