/**
 * Freight Forwarding ERP Document Management Engine
 * Operational Validation Guards & Compliance Middleware
 */

import { Request, Response, NextFunction } from 'express';
import { HouseBillOfLading, Invoice, CustomerProfile } from '../types/document.types';

export class DocumentGuardMiddleware {
  /**
   * Helper: Validates Container Number according to ISO 6346 Checksum Algorithm
   */
  public static validateIso6346Checksum(containerNumber: string): boolean {
    if (!containerNumber || typeof containerNumber !== 'string') return false;
    const clean = containerNumber.replace(/[^A-Z0-9]/g, '').toUpperCase();
    if (clean.length !== 11) return false;

    const charMap: Record<string, number> = {
      A: 10, B: 12, C: 13, D: 14, E: 15, F: 16, G: 17, H: 18, I: 19, J: 20,
      K: 21, L: 23, M: 24, N: 25, O: 26, P: 27, Q: 28, R: 29, S: 30, T: 31,
      U: 32, V: 34, W: 35, X: 36, Y: 37, Z: 38
    };

    let sum = 0;
    for (let i = 0; i < 10; i++) {
      const char = clean[i];
      const val = charMap[char] !== undefined ? charMap[char] : parseInt(char, 10);
      sum += val * Math.pow(2, i);
    }

    const checkDigit = (sum % 11) % 10;
    const actualDigit = parseInt(clean[10], 10);

    return checkDigit === actualDigit;
  }

  /**
   * 1. Guard for House Bill of Lading (HBL) Issuance
   * Enforces SOLAS VGM, Container/Seal Number completeness, and Shipped on Board Date logic.
   */
  public static validateHblIssuanceGuard(req: Request, res: Response, next: NextFunction): void {
    const hbl: HouseBillOfLading = req.body;
    const errors: string[] = [];

    if (!hbl.containers || hbl.containers.length === 0) {
      errors.push('SOLAS Guard Violation: HBL must have at least one container assigned.');
    } else {
      hbl.containers.forEach((c, idx) => {
        if (!c.containerNumber || c.containerNumber.trim() === '') {
          errors.push(`Container #${idx + 1}: Container Serial Number is required.`);
        } else if (!DocumentGuardMiddleware.validateIso6346Checksum(c.containerNumber)) {
          errors.push(`Container #${idx + 1} (${c.containerNumber}): Invalid ISO 6346 Check Digit.`);
        }

        if (!c.sealNumber || c.sealNumber.trim() === '') {
          errors.push(`Container #${idx + 1} (${c.containerNumber}): Seal Number is required for B/L issuance.`);
        }

        if (!c.vgmWeightKg || c.vgmWeightKg <= 0) {
          errors.push(`SOLAS Violation: Container #${idx + 1} (${c.containerNumber}): Verified Gross Mass (VGM kg) must be > 0.`);
        }
      });
    }

    // Date Logic Check: issueDate cannot be earlier than shippedOnBoardDate
    if (hbl.issueDate && hbl.shippedOnBoardDate) {
      const issueTime = new Date(hbl.issueDate).getTime();
      const boardTime = new Date(hbl.shippedOnBoardDate).getTime();

      if (issueTime < boardTime) {
        errors.push(`Compliance Violation: HBL Issue Date (${hbl.issueDate}) cannot precede Shipped on Board Date (${hbl.shippedOnBoardDate}).`);
      }
    }

    if (errors.length > 0) {
      res.status(422).json({
        success: false,
        errorCategory: 'HBL_ISSUANCE_COMPLIANCE_ERROR',
        message: 'HBL Issuance Validation Failed',
        validationErrors: errors
      });
      return;
    }

    next();
  }

  /**
   * 2. Guard for Commercial Invoice Issuance
   * Enforces Customer Credit Limit & Overdue Risk Checks unless Supervisor Bypass Flag is set.
   */
  public static createInvoiceCreditGuard(getCustomerProfile: (customerId: string) => Promise<CustomerProfile | null>) {
    return async (req: Request, res: Response, next: NextFunction): Promise<void> => {
      const invoice: Invoice = req.body;
      const errors: string[] = [];

      const customer = await getCustomerProfile(invoice.customerId);

      if (!customer) {
        res.status(404).json({
          success: false,
          errorCategory: 'CUSTOMER_NOT_FOUND',
          message: `Customer Account '${invoice.customerId}' not found in CRM.`
        });
        return;
      }

      // Check Overdue Status
      if (customer.hasOverdueInvoices && !invoice.supervisorBypassFlag) {
        errors.push(`CREDIT HOLD RISK: Customer '${customer.name}' has overdue outstanding invoices. Invoice issuance blocked.`);
      }

      // Check Credit Limit Ceiling
      const projectedOutstanding = customer.currentOutstandingThb + (invoice.totalAmount * (invoice.fxRateToThb || 1.0));
      if (projectedOutstanding > customer.creditLimitThb && !invoice.supervisorBypassFlag) {
        errors.push(`CREDIT LIMIT EXCEEDED: Projected total outstanding (฿${projectedOutstanding.toLocaleString()}) exceeds approved ceiling limit (฿${customer.creditLimitThb.toLocaleString()}).`);
      }

      if (errors.length > 0) {
        res.status(403).json({
          success: false,
          errorCategory: 'CREDIT_RISK_INTERCEPT_ERROR',
          message: 'Invoice Issuance Intercepted by Credit Risk Control',
          validationErrors: errors,
          requiresSupervisorBypass: true
        });
        return;
      }

      next();
    };
  }
}
