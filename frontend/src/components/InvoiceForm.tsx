import React, { useState, useEffect } from 'react';

export interface InvoiceLineItem {
  id: string;
  description: string;
  quantity: number;
  unitPrice: number;
  taxType: 'VAT_7' | 'NON_VAT' | 'ADVANCE';
  whtType: 'NONE' | 'WHT_1' | 'WHT_3';
  amount: number;
}

export interface CustomerCreditInfo {
  id: string;
  name: string;
  taxId: string;
  paymentTermDays: number;
  creditLimitThb: number;
  currentOutstandingThb: number;
  hasOverdueInvoices: boolean;
}

export const InvoiceForm: React.FC = () => {
  const [docNo, setDocNo] = useState('INV-2026-0001');
  const [jobNo, setJobNo] = useState('SE26080001');
  const [issueDate, setIssueDate] = useState(new Date().toISOString().slice(0, 10));
  const [dueDate, setDueDate] = useState('');
  const [currency, setCurrency] = useState<'THB' | 'USD'>('THB');
  const [fxRate, setFxRate] = useState(35.5);
  const [supervisorBypass, setSupervisorBypass] = useState(false);

  const [customer, setCustomer] = useState<CustomerCreditInfo>({
    id: 'CUST-001',
    name: 'Nattayaraat Logistics Trading Ltd',
    taxId: '0735568004823',
    paymentTermDays: 30,
    creditLimitThb: 1000000,
    currentOutstandingThb: 750000,
    hasOverdueInvoices: true, // Mocking credit hold warning
  });

  const [items, setItems] = useState<InvoiceLineItem[]>([
    {
      id: 'inv-1',
      description: 'Ocean Freight Charges (Laem Chabang to Los Angeles)',
      quantity: 1,
      unitPrice: 1500,
      taxType: 'NON_VAT',
      whtType: 'NONE',
      amount: 1500,
    },
    {
      id: 'inv-2',
      description: 'Terminal Handling Charge (THC)',
      quantity: 1,
      unitPrice: 4500,
      taxType: 'VAT_7',
      whtType: 'WHT_3',
      amount: 4500,
    },
  ]);

  // Calculate Due Date based on Issue Date + Customer Payment Terms
  useEffect(() => {
    if (issueDate && customer.paymentTermDays) {
      const d = new Date(issueDate);
      d.setDate(d.getDate() + customer.paymentTermDays);
      setDueDate(d.toISOString().slice(0, 10));
    }
  }, [issueDate, customer.paymentTermDays]);

  // Keyboard Shortcuts (Alt + N for Add Line Item)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && e.key.toLowerCase() === 'n') {
        e.preventDefault();
        handleAddItem();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [items]);

  const handleAddItem = () => {
    setItems((prev) => [
      ...prev,
      {
        id: `inv-${Date.now()}`,
        description: '',
        quantity: 1,
        unitPrice: 0,
        taxType: 'VAT_7',
        whtType: 'NONE',
        amount: 0,
      },
    ]);
  };

  const handleItemChange = (id: string, field: keyof InvoiceLineItem, val: any) => {
    setItems((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item;
        const updated = { ...item, [field]: val };

        if (field === 'quantity' || field === 'unitPrice') {
          const qty = field === 'quantity' ? Number(val) : updated.quantity;
          const price = field === 'unitPrice' ? Number(val) : updated.unitPrice;
          updated.amount = qty * price;
        }
        return updated;
      })
    );
  };

  const handleRemoveItem = (id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  // Calculations
  const subtotal = items.reduce((sum, item) => sum + item.amount, 0);
  const vatAmount = items
    .filter((i) => i.taxType === 'VAT_7')
    .reduce((sum, i) => sum + i.amount * 0.07, 0);

  const wht1 = items.filter((i) => i.whtType === 'WHT_1').reduce((sum, i) => sum + i.amount * 0.01, 0);
  const wht3 = items.filter((i) => i.whtType === 'WHT_3').reduce((sum, i) => sum + i.amount * 0.03, 0);
  const whtTotal = wht1 + wht3;

  const grandTotal = subtotal + vatAmount - whtTotal;
  const grandTotalThb = grandTotal * (currency === 'THB' ? 1 : fxRate);

  const isCreditLimitExceeded = customer.currentOutstandingThb + grandTotalThb > customer.creditLimitThb;
  const isBlocked = (customer.hasOverdueInvoices || isCreditLimitExceeded) && !supervisorBypass;

  return (
    <div className="max-w-6xl mx-auto p-6 bg-slate-900 text-slate-100 rounded-xl border border-slate-800 shadow-2xl space-y-6 font-sans">
      {/* HEADER BAR */}
      <div className="flex justify-between items-center pb-4 border-b border-slate-800">
        <div>
          <span className="text-xs uppercase font-bold tracking-widest text-sky-400">Financial Ledger Engine</span>
          <h2 className="text-2xl font-black text-slate-50 flex items-center gap-2">
            💳 Commercial Invoice & Tax Receipt
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`px-3 py-1 text-xs font-bold rounded-full border ${
              !isBlocked ? 'bg-emerald-950 text-emerald-400 border-emerald-800' : 'bg-rose-950 text-rose-400 border-rose-800'
            }`}
          >
            {!isBlocked ? '✓ Credit Approved' : '⚠️ CREDIT HOLD INTERCEPT'}
          </span>
        </div>
      </div>

      {/* CREDIT WARNING BANNER */}
      {(customer.hasOverdueInvoices || isCreditLimitExceeded) && (
        <div className="p-4 bg-rose-950/70 border border-rose-800 rounded-lg text-rose-200 text-xs flex justify-between items-center">
          <div className="space-y-1">
            <p className="font-bold text-rose-300">🚨 Credit Risk Intercept Triggered:</p>
            {customer.hasOverdueInvoices && <p>• Customer has overdue unpaid invoices exceeding aging threshold.</p>}
            {isCreditLimitExceeded && (
              <p>
                • Total outstanding (฿{(customer.currentOutstandingThb + grandTotalThb).toLocaleString()}) will exceed
                credit ceiling (฿{customer.creditLimitThb.toLocaleString()}).
              </p>
            )}
          </div>
          <label className="flex items-center gap-2 bg-slate-900 px-3 py-2 border border-rose-700 rounded cursor-pointer">
            <input
              type="checkbox"
              checked={supervisorBypass}
              onChange={(e) => setSupervisorBypass(e.target.checked)}
              className="rounded text-sky-500 focus:ring-0"
            />
            <span className="font-bold text-rose-300">Supervisor Bypass Flag</span>
          </label>
        </div>
      )}

      {/* SECTION 1: INVOICE HEADER & CUSTOMER DETAILS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 bg-slate-950/60 border border-slate-800/80 rounded-lg">
        <div>
          <label className="block text-xs font-bold text-slate-400 mb-1">Document No</label>
          <input
            type="text"
            value={docNo}
            onChange={(e) => setDocNo(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm font-semibold text-slate-100 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-bold text-slate-400 mb-1">Linked Job Reference</label>
          <input
            type="text"
            value={jobNo}
            onChange={(e) => setJobNo(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm text-slate-100 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-bold text-slate-400 mb-1">Issue Date</label>
          <input
            type="date"
            value={issueDate}
            onChange={(e) => setIssueDate(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm text-slate-100 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-bold text-slate-400 mb-1">Due Date (Auto +{customer.paymentTermDays}D)</label>
          <input
            type="date"
            readOnly
            value={dueDate}
            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm text-sky-400 font-mono font-bold cursor-not-allowed"
          />
        </div>
      </div>

      {/* SECTION 2: LINE ITEMS TABLE */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <h3 className="text-sm font-bold text-slate-200">📊 Billing Line Items & Charge Specifications</h3>
          <button
            type="button"
            onClick={handleAddItem}
            className="px-3 py-1 bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold rounded transition flex items-center gap-1"
          >
            <span>+ Add Charge Line</span>
            <span className="text-[10px] text-sky-200">(Alt+N)</span>
          </button>
        </div>

        <div className="overflow-x-auto border border-slate-800 rounded-lg">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-bold uppercase border-b border-slate-800">
              <tr>
                <th className="p-2.5">Description Specification</th>
                <th className="p-2.5 w-20 text-center">Qty</th>
                <th className="p-2.5 w-28 text-right">Unit Price</th>
                <th className="p-2.5 w-28">Tax Rate</th>
                <th className="p-2.5 w-28">WHT Rate</th>
                <th className="p-2.5 w-32 text-right">Amount ({currency})</th>
                <th className="p-2.5 text-center w-12">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 bg-slate-900/50">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-slate-800/40">
                  <td className="p-2">
                    <input
                      type="text"
                      value={item.description}
                      onChange={(e) => handleItemChange(item.id, 'description', e.target.value)}
                      placeholder="Charge description..."
                      className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1 text-slate-100"
                    />
                  </td>
                  <td className="p-2">
                    <input
                      type="number"
                      value={item.quantity}
                      onChange={(e) => handleItemChange(item.id, 'quantity', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-center font-mono"
                    />
                  </td>
                  <td className="p-2">
                    <input
                      type="number"
                      step="50"
                      value={item.unitPrice}
                      onChange={(e) => handleItemChange(item.id, 'unitPrice', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-right font-mono font-bold"
                    />
                  </td>
                  <td className="p-2">
                    <select
                      value={item.taxType}
                      onChange={(e) => handleItemChange(item.id, 'taxType', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1"
                    >
                      <option value="VAT_7">VAT 7%</option>
                      <option value="NON_VAT">Non-VAT</option>
                      <option value="ADVANCE">Advance</option>
                    </select>
                  </td>
                  <td className="p-2">
                    <select
                      value={item.whtType}
                      onChange={(e) => handleItemChange(item.id, 'whtType', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1"
                    >
                      <option value="NONE">None (0%)</option>
                      <option value="WHT_1">WHT 1%</option>
                      <option value="WHT_3">WHT 3%</option>
                    </select>
                  </td>
                  <td className="p-2 text-right font-mono font-bold text-slate-100">
                    {item.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td className="p-2 text-center">
                    <button
                      type="button"
                      onClick={() => handleRemoveItem(item.id)}
                      className="text-slate-500 hover:text-rose-400 p-1 font-bold"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION 3: READ-ONLY HIGHLIGHTED TOTALS & FINANCIAL RECONCILIATION */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-4 bg-slate-950 border border-slate-800 rounded-lg">
        <div className="space-y-2 text-xs">
          <span className="font-bold text-slate-400 uppercase tracking-wider">Currency & Exchange Setup</span>
          <div className="flex gap-4">
            <div>
              <label className="block text-slate-500 mb-1">Billing Currency</label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value as any)}
                className="bg-slate-900 border border-slate-700 rounded px-3 py-1 text-slate-100"
              >
                <option value="THB">THB (฿)</option>
                <option value="USD">USD ($)</option>
              </select>
            </div>
            {currency === 'USD' && (
              <div>
                <label className="block text-slate-500 mb-1">FX Exchange Rate (THB/USD)</label>
                <input
                  type="number"
                  step="0.01"
                  value={fxRate}
                  onChange={(e) => setFxRate(Number(e.target.value))}
                  className="bg-slate-900 border border-slate-700 rounded px-3 py-1 text-right font-mono"
                />
              </div>
            )}
          </div>
        </div>

        <div className="space-y-1.5 text-xs text-right font-mono">
          <div className="flex justify-between">
            <span className="text-slate-400">Subtotal Before Tax:</span>
            <span className="font-bold">{currency === 'THB' ? '฿' : '$'}{subtotal.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">VAT 7%:</span>
            <span className="font-bold text-slate-200">+{currency === 'THB' ? '฿' : '$'}{vatAmount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
          </div>
          {whtTotal > 0 && (
            <div className="flex justify-between text-rose-400">
              <span>Withholding Tax Deduction:</span>
              <span>-{currency === 'THB' ? '฿' : '$'}{whtTotal.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            </div>
          )}
          <div className="flex justify-between pt-2 border-t border-slate-800 text-base font-black text-emerald-400">
            <span>GRAND TOTAL NET:</span>
            <span>{currency === 'THB' ? '฿' : '$'}{grandTotal.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
          </div>
        </div>
      </div>

      {/* FOOTER ACTIONS */}
      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs rounded transition"
        >
          Save Draft
        </button>
        <button
          type="button"
          disabled={isBlocked}
          className={`px-6 py-2 text-xs font-bold rounded transition shadow-lg ${
            !isBlocked
              ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-900/40 cursor-pointer'
              : 'bg-slate-800 text-slate-600 cursor-not-allowed border border-slate-800'
          }`}
        >
          💳 Issue Invoice Document
        </button>
      </div>
    </div>
  );
};
