/**
 * Freight Forwarding ERP Document Management Engine
 * Express Router API Route Bindings
 */

import { Router } from 'express';
import { DocumentController } from '../controllers/document.controller';
import { DocumentGuardMiddleware } from '../middlewares/document-guard.middleware';

const router = Router();
const controller = new DocumentController();

// --- 1. QUOTATION ENDPOINTS ---
router.post('/quotations', controller.createQuotation);

// --- 2. HOUSE BILL OF LADING (HBL) ENDPOINTS ---
router.post('/hbl', controller.createHbl);
router.post('/hbl/issue', DocumentGuardMiddleware.validateHblIssuanceGuard, controller.issueHbl);

// --- 3. COMMERCIAL INVOICE ENDPOINTS ---
router.post('/invoices', controller.createInvoice);
router.post(
  '/invoices/issue',
  DocumentGuardMiddleware.createInvoiceCreditGuard(DocumentController.mockGetCustomerProfile),
  controller.issueInvoice
);

// --- 4. AUTO-FILL & UTILITY ENDPOINTS ---
router.get('/autofill/container-spec/:sizeType', controller.getContainerSpec);
router.post('/autofill/amount-in-words', controller.getAmountInWords);

export default router;
