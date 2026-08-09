import React, { useState, useEffect, useRef } from 'react';

export interface ContainerRow {
  id: string;
  containerNumber: string;
  sizeType: '20GP' | '40GP' | '40HC' | '45HC' | '20RF' | '40RF';
  sealNumber: string;
  grossWeightKg: number;
  tareWeightKg: number;
  vgmWeightKg: number;
  volumeCbm: number;
}

export interface HblFormData {
  hblNo: string;
  jobNo: string;
  shipper: string;
  consignee: string;
  notifyParty: string;
  vesselName: string;
  voyageNo: string;
  pol: string;
  pod: string;
  shippedOnBoardDate: string;
  issueDate: string;
  freightTerm: 'PREPAID' | 'COLLECT';
  containers: ContainerRow[];
}

const TARE_MATRIX: Record<string, number> = {
  '20GP': 2200,
  '40GP': 3750,
  '40HC': 3900,
  '45HC': 4800,
  '20RF': 3080,
  '40RF': 4500,
};

export const HblForm: React.FC = () => {
  const [formData, setFormData] = useState<HblFormData>({
    hblNo: 'HBL-2026-0001',
    jobNo: '',
    shipper: '',
    consignee: '',
    notifyParty: 'SAME AS CONSIGNEE',
    vesselName: '',
    voyageNo: '',
    pol: '',
    pod: '',
    shippedOnBoardDate: new Date().toISOString().slice(0, 10),
    issueDate: new Date().toISOString().slice(0, 10),
    freightTerm: 'PREPAID',
    containers: [
      {
        id: 'c-1',
        containerNumber: 'MSKU9070323',
        sizeType: '40HC',
        sealNumber: 'SEAL-987654',
        grossWeightKg: 24500,
        tareWeightKg: 3900,
        vgmWeightKg: 28400,
        volumeCbm: 68.5,
      },
    ],
  });

  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const jobInputRef = useRef<HTMLInputElement>(null);

  // Keyboard Shortcuts (Alt + N for Add Row, Alt + A for Auto-fill, Alt + S for Save)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && e.key.toLowerCase() === 'n') {
        e.preventDefault();
        handleAddContainer();
      } else if (e.altKey && e.key.toLowerCase() === 'a') {
        e.preventDefault();
        handleAutoFillFromJob('SE26080001');
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [formData.containers]);

  // Real-time Validation Check
  useEffect(() => {
    const errors: string[] = [];
    if (!formData.jobNo) errors.push('Job Number is required.');
    if (!formData.shipper) errors.push('Shipper Name is required.');
    if (!formData.consignee) errors.push('Consignee Name is required.');

    formData.containers.forEach((c, idx) => {
      if (!c.containerNumber) errors.push(`Container #${idx + 1}: Serial Number missing.`);
      if (!c.sealNumber) errors.push(`Container #${idx + 1}: Seal Number missing.`);
      if (c.vgmWeightKg <= 0) errors.push(`Container #${idx + 1}: VGM Weight must be > 0.`);
    });

    setValidationErrors(errors);
  }, [formData]);

  // Smart Auto-fill Mock when typing Job Number
  const handleJobNoChange = (val: string) => {
    setFormData((prev) => ({ ...prev, jobNo: val }));
    if (val.trim().length >= 4) {
      handleAutoFillFromJob(val);
    }
  };

  const handleAutoFillFromJob = (jobNo: string) => {
    setFormData((prev) => ({
      ...prev,
      jobNo: jobNo.toUpperCase(),
      shipper: 'NATTAYARAAT TRADING CO., LTD.',
      consignee: 'GLOBAL FREIGHT LOGISTICS INC. (USA)',
      vesselName: 'MAERSK MC-KINNEY MOLLER',
      voyageNo: 'V.2608E',
      pol: 'THLCH - LAEM CHABANG, THAILAND',
      pod: 'USLAX - LOS ANGELES, CA, USA',
      freightTerm: 'PREPAID',
    }));
  };

  const handleAddContainer = () => {
    const newId = `c-${Date.now()}`;
    setFormData((prev) => ({
      ...prev,
      containers: [
        ...prev.containers,
        {
          id: newId,
          containerNumber: '',
          sizeType: '40HC',
          sealNumber: '',
          grossWeightKg: 0,
          tareWeightKg: 3900,
          vgmWeightKg: 3900,
          volumeCbm: 0,
        },
      ],
    }));
  };

  const handleContainerChange = (id: string, field: keyof ContainerRow, val: any) => {
    setFormData((prev) => ({
      ...prev,
      containers: prev.containers.map((c) => {
        if (c.id !== id) return c;
        const updated = { ...c, [field]: val };

        // Auto-fill Tare Weight & Calculate VGM
        if (field === 'sizeType') {
          updated.tareWeightKg = TARE_MATRIX[val] || 3900;
          updated.vgmWeightKg = updated.grossWeightKg + updated.tareWeightKg;
        } else if (field === 'grossWeightKg' || field === 'tareWeightKg') {
          const gw = field === 'grossWeightKg' ? Number(val) : updated.grossWeightKg;
          const tw = field === 'tareWeightKg' ? Number(val) : updated.tareWeightKg;
          updated.vgmWeightKg = gw + tw;
        }

        return updated;
      }),
    }));
  };

  const handleRemoveContainer = (id: string) => {
    setFormData((prev) => ({
      ...prev,
      containers: prev.containers.filter((c) => c.id !== id),
    }));
  };

  const totalGrossKg = formData.containers.reduce((sum, c) => sum + Number(c.grossWeightKg || 0), 0);
  const totalVgmKg = formData.containers.reduce((sum, c) => sum + Number(c.vgmWeightKg || 0), 0);
  const totalCbm = formData.containers.reduce((sum, c) => sum + Number(c.volumeCbm || 0), 0);

  return (
    <div className="max-w-6xl mx-auto p-6 bg-slate-900 text-slate-100 rounded-xl border border-slate-800 shadow-2xl space-y-6 font-sans">
      {/* HEADER BAR */}
      <div className="flex justify-between items-center pb-4 border-b border-slate-800">
        <div>
          <span className="text-xs uppercase font-bold tracking-widest text-sky-400">Enterprise Forwarding OS</span>
          <h2 className="text-2xl font-black text-slate-50 flex items-center gap-2">
            🚢 House Bill of Lading (HBL) Management
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => handleAutoFillFromJob('SE26080001')}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-sky-400 text-xs font-bold rounded-md border border-slate-700 transition"
          >
            ⚡ Auto-Fill Defaults (Alt+A)
          </button>
          <span
            className={`px-3 py-1 text-xs font-bold rounded-full border ${
              validationErrors.length === 0
                ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                : 'bg-rose-950 text-rose-400 border-rose-800'
            }`}
          >
            {validationErrors.length === 0 ? '✓ Ready for Issuance' : `⚠️ ${validationErrors.length} Errors`}
          </span>
        </div>
      </div>

      {/* VALIDATION ALERT BANNER */}
      {validationErrors.length > 0 && (
        <div className="p-3 bg-rose-950/60 border border-rose-800/80 rounded-lg text-rose-300 text-xs space-y-1">
          <p className="font-bold text-rose-400">Compliance & Validation Intercept Warnings:</p>
          <ul className="list-disc list-inside space-y-0.5">
            {validationErrors.map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {/* SECTION 1: HEADER & ROUTING PARAMETERS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 bg-slate-950/60 border border-slate-800/80 rounded-lg">
        <div>
          <label className="block text-xs font-bold text-slate-400 mb-1">Job Number *</label>
          <input
            ref={jobInputRef}
            type="text"
            value={formData.jobNo}
            onChange={(e) => handleJobNoChange(e.target.value)}
            placeholder="Type Job No (e.g. SE26080001)..."
            className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm font-semibold text-slate-100 focus:outline-none focus:border-sky-500"
          />
        </div>

        <div>
          <label className="block text-xs font-bold text-slate-400 mb-1">HBL Document No *</label>
          <input
            type="text"
            value={formData.hblNo}
            onChange={(e) => setFormData({ ...formData, hblNo: e.target.value })}
            className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
          />
        </div>

        <div>
          <label className="block text-xs font-bold text-slate-400 mb-1">Freight Payment Term</label>
          <select
            value={formData.freightTerm}
            onChange={(e) => setFormData({ ...formData, freightTerm: e.target.value as any })}
            className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
          >
            <option value="PREPAID">FREIGHT PREPAID</option>
            <option value="COLLECT">FREIGHT COLLECT</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-bold text-slate-400 mb-1">Shipped On Board Date</label>
          <input
            type="date"
            value={formData.shippedOnBoardDate}
            onChange={(e) => setFormData({ ...formData, shippedOnBoardDate: e.target.value })}
            className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
          />
        </div>
      </div>

      {/* SECTION 2: SHIPPER / CONSIGNEE & VESSEL */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-lg space-y-3">
          <h3 className="text-xs font-bold text-sky-400 uppercase tracking-wider">Trading Parties</h3>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Shipper Name & Address *</label>
            <textarea
              rows={2}
              value={formData.shipper}
              onChange={(e) => setFormData({ ...formData, shipper: e.target.value })}
              className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-100 focus:outline-none focus:border-sky-500"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Consignee Name & Address *</label>
            <textarea
              rows={2}
              value={formData.consignee}
              onChange={(e) => setFormData({ ...formData, consignee: e.target.value })}
              className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-100 focus:outline-none focus:border-sky-500"
            />
          </div>
        </div>

        <div className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-lg space-y-3">
          <h3 className="text-xs font-bold text-sky-400 uppercase tracking-wider">Vessel & Routing Manifest</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Vessel Name</label>
              <input
                type="text"
                value={formData.vesselName}
                onChange={(e) => setFormData({ ...formData, vesselName: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-100 focus:outline-none focus:border-sky-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Voyage No</label>
              <input
                type="text"
                value={formData.voyageNo}
                onChange={(e) => setFormData({ ...formData, voyageNo: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-100 focus:outline-none focus:border-sky-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Port of Loading (POL)</label>
              <input
                type="text"
                value={formData.pol}
                onChange={(e) => setFormData({ ...formData, pol: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-100 focus:outline-none focus:border-sky-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Port of Discharge (POD)</label>
              <input
                type="text"
                value={formData.pod}
                onChange={(e) => setFormData({ ...formData, pod: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-100 focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 3: CONTAINERS MATRIX TABLE */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <h3 className="text-sm font-bold text-slate-200">📦 Container Equipment & SOLAS VGM Matrix</h3>
          <button
            type="button"
            onClick={handleAddContainer}
            className="px-3 py-1 bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold rounded transition flex items-center gap-1"
          >
            <span>+ Add Container</span>
            <span className="text-[10px] text-sky-200">(Alt+N)</span>
          </button>
        </div>

        <div className="overflow-x-auto border border-slate-800 rounded-lg">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-bold uppercase border-b border-slate-800">
              <tr>
                <th className="p-2.5">Container Serial No *</th>
                <th className="p-2.5">Size/Type</th>
                <th className="p-2.5">Seal No *</th>
                <th className="p-2.5">Gross Wt (kg)</th>
                <th className="p-2.5">Tare Wt (kg)</th>
                <th className="p-2.5 text-sky-400">VGM Wt (kg)</th>
                <th className="p-2.5">Volume (CBM)</th>
                <th className="p-2.5 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 bg-slate-900/50">
              {formData.containers.map((c, i) => (
                <tr key={c.id} className="hover:bg-slate-800/40">
                  <td className="p-2">
                    <input
                      type="text"
                      value={c.containerNumber}
                      onChange={(e) => handleContainerChange(c.id, 'containerNumber', e.target.value.toUpperCase())}
                      placeholder="e.g. MSKU9070323"
                      className={`w-full bg-slate-950 border rounded px-2 py-1 uppercase font-mono font-bold ${
                        !c.containerNumber ? 'border-rose-600/80 text-rose-300' : 'border-slate-700 text-slate-100'
                      }`}
                    />
                  </td>
                  <td className="p-2">
                    <select
                      value={c.sizeType}
                      onChange={(e) => handleContainerChange(c.id, 'sizeType', e.target.value)}
                      className="bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-100"
                    >
                      <option value="20GP">20'GP</option>
                      <option value="40GP">40'GP</option>
                      <option value="40HC">40'HC</option>
                      <option value="45HC">45'HC</option>
                      <option value="20RF">20'RF</option>
                      <option value="40RF">40'RF</option>
                    </select>
                  </td>
                  <td className="p-2">
                    <input
                      type="text"
                      value={c.sealNumber}
                      onChange={(e) => handleContainerChange(c.id, 'sealNumber', e.target.value)}
                      placeholder="Seal No..."
                      className={`w-full bg-slate-950 border rounded px-2 py-1 font-mono ${
                        !c.sealNumber ? 'border-rose-600/80 text-rose-300' : 'border-slate-700 text-slate-100'
                      }`}
                    />
                  </td>
                  <td className="p-2">
                    <input
                      type="number"
                      value={c.grossWeightKg || ''}
                      onChange={(e) => handleContainerChange(c.id, 'grossWeightKg', e.target.value)}
                      className="w-24 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-right font-mono"
                    />
                  </td>
                  <td className="p-2">
                    <input
                      type="number"
                      value={c.tareWeightKg || ''}
                      onChange={(e) => handleContainerChange(c.id, 'tareWeightKg', e.target.value)}
                      className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-right font-mono text-slate-400"
                    />
                  </td>
                  <td className="p-2">
                    <input
                      type="number"
                      readOnly
                      value={c.vgmWeightKg || 0}
                      className="w-24 bg-slate-950/90 border border-sky-800 rounded px-2 py-1 text-right font-mono font-bold text-sky-400 cursor-not-allowed"
                    />
                  </td>
                  <td className="p-2">
                    <input
                      type="number"
                      step="0.1"
                      value={c.volumeCbm || ''}
                      onChange={(e) => handleContainerChange(c.id, 'volumeCbm', e.target.value)}
                      className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-right font-mono"
                    />
                  </td>
                  <td className="p-2 text-center">
                    <button
                      type="button"
                      onClick={() => handleRemoveContainer(c.id)}
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

      {/* SECTION 4: READ-ONLY HIGHLIGHTED TOTALS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-slate-950 border border-slate-800 rounded-lg">
        <div className="p-3 bg-slate-900 border border-slate-800 rounded">
          <span className="text-[11px] font-bold text-slate-400 uppercase">Total Gross Weight</span>
          <p className="text-xl font-black text-slate-100 font-mono">{totalGrossKg.toLocaleString()} kg</p>
        </div>
        <div className="p-3 bg-slate-900 border border-sky-900/60 rounded">
          <span className="text-[11px] font-bold text-sky-400 uppercase">Total SOLAS VGM Mass</span>
          <p className="text-xl font-black text-sky-400 font-mono">{totalVgmKg.toLocaleString()} kg</p>
        </div>
        <div className="p-3 bg-slate-900 border border-slate-800 rounded">
          <span className="text-[11px] font-bold text-slate-400 uppercase">Total Volume (CBM)</span>
          <p className="text-xl font-black text-amber-400 font-mono">{totalCbm.toFixed(2)} CBM</p>
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
          disabled={validationErrors.length > 0}
          className={`px-6 py-2 text-xs font-bold rounded transition shadow-lg ${
            validationErrors.length === 0
              ? 'bg-sky-600 hover:bg-sky-500 text-white shadow-sky-900/40 cursor-pointer'
              : 'bg-slate-800 text-slate-600 cursor-not-allowed border border-slate-800'
          }`}
        >
          🚀 Issue HBL Document
        </button>
      </div>
    </div>
  );
};
