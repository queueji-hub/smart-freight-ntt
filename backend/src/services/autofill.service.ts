/**
 * Freight Forwarding ERP Document Management Engine
 * Auto-fill & Financial Auto-Calculation Service
 */

import { ContainerSizeType, ContainerSpec, ContainerDetail, CurrencyCode } from '../types/document.types';

export class AutofillService {
  /**
   * Container Specifications & Tare Weight Standard Matrix (CargoWise Standard)
   */
  private static readonly CONTAINER_SPEC_MATRIX: Record<ContainerSizeType, ContainerSpec> = {
    '20GP': { sizeType: '20GP', tareWeightKg: 2200, maxPayloadKg: 28200, maxCbm: 33.2 },
    '40GP': { sizeType: '40GP', tareWeightKg: 3750, maxPayloadKg: 26730, maxCbm: 67.7 },
    '40HC': { sizeType: '40HC', tareWeightKg: 3900, maxPayloadKg: 28600, maxCbm: 76.4 },
    '45HC': { sizeType: '45HC', tareWeightKg: 4800, maxPayloadKg: 29600, maxCbm: 86.0 },
    '20RF': { sizeType: '20RF', tareWeightKg: 3080, maxPayloadKg: 27400, maxCbm: 28.3 },
    '40RF': { sizeType: '40RF', tareWeightKg: 4500, maxPayloadKg: 29500, maxCbm: 67.3 },
    '20OT': { sizeType: '20OT', tareWeightKg: 2350, maxPayloadKg: 27800, maxCbm: 32.5 },
    '40OT': { sizeType: '40OT', tareWeightKg: 3850, maxPayloadKg: 28150, maxCbm: 65.5 },
    '20FR': { sizeType: '20FR', tareWeightKg: 2750, maxPayloadKg: 31000, maxCbm: 27.9 },
    '40FR': { sizeType: '40FR', tareWeightKg: 5200, maxPayloadKg: 39000, maxCbm: 54.8 }
  };

  /**
   * 1. Get Standard Container Specifications by Size Type
   */
  public static getContainerSpec(sizeType: ContainerSizeType): ContainerSpec {
    return this.CONTAINER_SPEC_MATRIX[sizeType] || this.CONTAINER_SPEC_MATRIX['40HC'];
  }

  /**
   * 2. Auto-calculate Invoice Due Date based on Issue Date + Payment Term Days
   */
  public static calculateDueDate(issueDate: Date, paymentTermDays: number = 30): Date {
    const baseDate = new Date(issueDate);
    baseDate.setDate(baseDate.getDate() + paymentTermDays);
    return baseDate;
  }

  /**
   * 3. Generate Legal Cargo Summary Clause for Bills of Lading
   * e.g., "SAY: TWO (2) x 40' HIGH CUBE CONTAINERS ONLY"
   */
  public static generateCargoSummary(containers: ContainerDetail[]): string {
    if (!containers || containers.length === 0) {
      return 'SAY: ZERO (0) CONTAINERS ONLY';
    }

    const counts: Record<string, number> = {};
    const names: Record<string, string> = {
      '20GP': "20' GENERAL PURPOSE",
      '40GP': "40' GENERAL PURPOSE",
      '40HC': "40' HIGH CUBE",
      '45HC': "45' HIGH CUBE",
      '20RF': "20' REEFER",
      '40RF': "40' REEFER",
      '20OT': "20' OPEN TOP",
      '40OT': "40' OPEN TOP",
      '20FR': "20' FLAT RACK",
      '40FR': "40' FLAT RACK"
    };

    containers.forEach((c) => {
      counts[c.sizeType] = (counts[c.sizeType] || 0) + 1;
    });

    const numberWords = ['ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN'];

    const summaryParts = Object.entries(counts).map(([size, count]) => {
      const numWord = count <= 10 ? numberWords[count] : count.toString();
      const typeDesc = names[size] || size;
      const plural = count > 1 ? 'CONTAINERS' : 'CONTAINER';
      return `${numWord} (${count}) x ${typeDesc} ${plural}`;
    });

    return `SAY: ${summaryParts.join(' AND ')} ONLY`;
  }

  /**
   * 4. Convert Amount into Official Thai Baht Text (เช่น หนึ่งพันห้าร้อยบาทถ้วน)
   */
  public static convertAmountToThaiBahtText(amount: number): string {
    if (!amount || amount === 0) return 'ศูนย์บาทถ้วน';

    const numText = ['ศูนย์', 'หนึ่ง', 'สอง', 'สาม', 'สี่', 'ห้า', 'หก', 'เจ็ด', 'แปด', 'เก้า'];
    const unitText = ['', 'สิบ', 'ร้อย', 'พัน', 'หมื่น', 'แสน', 'ล้าน'];

    const baht = Math.floor(Math.abs(amount));
    const satang = Math.round((Math.abs(amount) - baht) * 100);

    const convertSection = (n: number): string => {
      const s = n.toString();
      const len = s.length;
      let res = '';
      for (let i = 0; i < len; i++) {
        const digit = parseInt(s[i]);
        const pos = len - i - 1;
        if (digit !== 0) {
          if (pos === 1 && digit === 1) res += 'สิบ';
          else if (pos === 1 && digit === 2) res += 'ยี่สิบ';
          else if (pos === 0 && digit === 1 && len > 1) res += 'เอ็ด';
          else res += numText[digit] + unitText[pos];
        }
      }
      return res;
    };

    let result = amount < 0 ? 'ลบ' : '';
    result += baht > 0 ? convertSection(baht) + 'บาท' : 'ศูนย์บาท';

    if (satang === 0) {
      result += 'ถ้วน';
    } else {
      result += convertSection(satang) + 'สตางค์';
    }

    return result;
  }

  /**
   * 5. Convert Amount into English Words (e.g. SAY ONE THOUSAND FIVE HUNDRED US DOLLARS ONLY)
   */
  public static convertAmountToEnglishWords(amount: number, currency: CurrencyCode = 'USD'): string {
    if (!amount || amount === 0) return `SAY ZERO ${currency} ONLY`;

    const units = ['', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN',
      'ELEVEN', 'TWELVE', 'THIRTEEN', 'FOURTEEN', 'FIFTEEN', 'SIXTEEN', 'SEVENTEEN', 'EIGHTEEN', 'NINETEEN'];
    const tens = ['', '', 'TWENTY', 'THIRTY', 'FORTY', 'FIFTY', 'SIXTY', 'SEVENTY', 'EIGHTY', 'NINETY'];

    const convertHundreds = (n: number): string => {
      let str = '';
      if (n >= 100) {
        str += units[Math.floor(n / 100)] + ' HUNDRED ';
        n %= 100;
      }
      if (n >= 20) {
        str += tens[Math.floor(n / 10)] + (n % 10 ? '-' + units[n % 10] : '');
      } else if (n > 0) {
        str += units[n];
      }
      return str.trim();
    };

    const dollars = Math.floor(Math.abs(amount));
    const cents = Math.round((Math.abs(amount) - dollars) * 100);

    const parts: string[] = [];
    const billions = Math.floor(dollars / 1_000_000_000);
    const millions = Math.floor((dollars % 1_000_000_000) / 1_000_000);
    const thousands = Math.floor((dollars % 1_000_000) / 1_000);
    const rem = dollars % 1_000;

    if (billions) parts.push(`${convertHundreds(billions)} BILLION`);
    if (millions) parts.push(`${convertHundreds(millions)} MILLION`);
    if (thousands) parts.push(`${convertHundreds(thousands)} THOUSAND`);
    if (rem) parts.push(convertHundreds(rem));

    const words = parts.join(' ') || 'ZERO';
    const mainUnit = currency === 'USD' ? 'US DOLLARS' : currency === 'THB' ? 'BAHT' : currency;

    if (cents > 0) {
      return `SAY ${words} ${mainUnit} AND ${convertHundreds(cents)} CENTS ONLY`;
    }
    return `SAY ${words} ${mainUnit} ONLY`;
  }
}
