import { apiClient } from './api';
import html2canvas from 'html2canvas';

export interface ExportRequestPayload {
  columns: string[];
  rows: Array<Record<string, any>>;
  question?: string;
  insight?: string;
  truncated?: boolean;
  total_rows?: number;
  include_visualization?: boolean;
  chart_image_base64?: string;
}

export const captureChartImage = async (chartElement: HTMLElement): Promise<string | null> => {
  if (!chartElement) return null;
  try {
    // Wait for animation frame so SVG paths and styles are completely rendered in final state
    await new Promise((resolve) => requestAnimationFrame(resolve));

    const canvas = await html2canvas(chartElement, {
      scale: 3, // High resolution (3x) capture so chart text, lines, and shapes stay sharp in PDF/Word
      useCORS: true,
      allowTaint: true,
      backgroundColor: null, // Preserves container background, colors, and theme (Dark/Light mode)
      logging: false
    } as any);
    return canvas.toDataURL('image/png');
  } catch (err) {
    console.error('Failed to capture chart DOM element:', err);
    return null;
  }
};

export const copyResultsToClipboard = async (
  columns: string[],
  rows: Array<Record<string, any>>
): Promise<{ success: boolean; message: string }> => {
  if (!rows || rows.length === 0 || !columns || columns.length === 0) {
    return { success: false, message: 'Nothing to copy.' };
  }

  try {
    // Generate TSV format (Tab Separated Values)
    const headerLine = columns.join('\t');
    const rowLines = rows.map((row) =>
      columns
        .map((col) => {
          const val = row[col];
          if (val === null || val === undefined) return '';
          // Remove newlines and tabs inside cell values for clean copy
          return String(val).replace(/[\t\r\n]+/g, ' ');
        })
        .join('\t')
    );

    const tsvContent = [headerLine, ...rowLines].join('\n');

    // Clipboard API with fallback
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(tsvContent);
    } else {
      const textarea = document.createElement('textarea');
      textarea.value = tsvContent;
      textarea.style.position = 'fixed';
      textarea.style.left = '-999999px';
      textarea.style.top = '-999999px';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      const successful = document.execCommand('copy');
      document.body.removeChild(textarea);
      if (!successful) throw new Error('DOM copy command failed');
    }

    return { success: true, message: 'Copied to clipboard' };
  } catch (err: any) {
    console.error('Clipboard copy error:', err);
    return { success: false, message: 'Failed to copy results to clipboard.' };
  }
};

export const exportCSV = (
  columns: string[],
  rows: Array<Record<string, any>>,
  filename: string = 'results.csv'
): { success: boolean; message?: string } => {
  if (!rows || rows.length === 0 || !columns || columns.length === 0) {
    return { success: false, message: 'Nothing to export.' };
  }

  try {
    const escapeCSV = (val: any): string => {
      if (val === null || val === undefined) return '';
      const str = String(val);
      if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    };

    const header = columns.map(escapeCSV).join(',');
    const body = rows.map((row) => columns.map((col) => escapeCSV(row[col])).join(',')).join('\r\n');

    // Add UTF-8 BOM (\uFEFF) for Excel UTF-8 compatibility
    const csvContent = '\uFEFF' + header + '\r\n' + body;

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    return { success: true };
  } catch (err: any) {
    console.error('CSV export error:', err);
    return { success: false, message: 'Failed to generate CSV file.' };
  }
};

const triggerBlobDownload = (data: Blob, defaultFilename: string, contentDisposition?: string) => {
  let filename = defaultFilename;
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^";]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const url = window.URL.createObjectURL(data);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export const exportExcel = async (
  payload: ExportRequestPayload
): Promise<{ success: boolean; message?: string }> => {
  if (!payload.rows || payload.rows.length === 0) {
    return { success: false, message: 'Nothing to export.' };
  }

  try {
    const response = await apiClient.post('/export/excel', payload, {
      responseType: 'blob'
    });
    triggerBlobDownload(response.data, 'results.xlsx', response.headers['content-disposition']);
    return { success: true };
  } catch (err: any) {
    console.error('Excel export error:', err);
    return { success: false, message: 'Failed to generate Excel file.' };
  }
};

export const exportDocx = async (
  payload: ExportRequestPayload
): Promise<{ success: boolean; message?: string }> => {
  if (!payload.rows || payload.rows.length === 0) {
    return { success: false, message: 'Nothing to export.' };
  }

  try {
    const response = await apiClient.post('/export/docx', payload, {
      responseType: 'blob'
    });
    triggerBlobDownload(response.data, 'results.docx', response.headers['content-disposition']);
    return { success: true };
  } catch (err: any) {
    console.error('Word export error:', err);
    return { success: false, message: 'Failed to generate Word document.' };
  }
};

export const exportPDF = async (
  payload: ExportRequestPayload
): Promise<{ success: boolean; message?: string }> => {
  if (!payload.rows || payload.rows.length === 0) {
    return { success: false, message: 'Nothing to export.' };
  }

  try {
    const response = await apiClient.post('/export/pdf', payload, {
      responseType: 'blob'
    });
    triggerBlobDownload(response.data, 'results.pdf', response.headers['content-disposition']);
    return { success: true };
  } catch (err: any) {
    console.error('PDF export error:', err);
    return { success: false, message: 'Failed to generate PDF file.' };
  }
};
