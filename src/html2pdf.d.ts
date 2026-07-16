// Minimal typing for html2pdf.js (no official types shipped).
declare module 'html2pdf.js' {
  interface Html2PdfOptions {
    margin?: number | number[];
    filename?: string;
    image?: { type?: string; quality?: number };
    html2canvas?: Record<string, unknown>;
    jsPDF?: Record<string, unknown>;
    pagebreak?: { mode?: string | string[] };
  }
  interface Html2Pdf {
    set(opt: Html2PdfOptions): Html2Pdf;
    from(el: HTMLElement | string): Html2Pdf;
    save(): Promise<void>;
    toPdf(): Html2Pdf;
    outputPdf(type?: string): Promise<unknown>;
  }
  function html2pdf(): Html2Pdf;
  export default html2pdf;
}
