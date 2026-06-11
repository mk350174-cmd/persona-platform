import React, { useState } from 'react';
import jsPDF from 'jspdf';
import Papa from 'papaparse';

export default function ConversationExport({ conversation = [], personaName = 'Persona' }) {
  const [exporting, setExporting] = useState(false);

  const exportAsMarkdown = () => {
    setExporting(true);
    try {
      const markdown = conversation
        .map((msg) => {
          const speaker = msg.role === 'user' ? '**You:**' : `**${personaName}:**`;
          return `${speaker}\n${msg.content}\n`;
        })
        .join('\n---\n\n');

      const filename = `${personaName}-conversation-${new Date().toISOString().slice(0, 10)}.md`;
      downloadFile(markdown, filename, 'text/markdown');
    } finally {
      setExporting(false);
    }
  };

  const exportAsJSON = () => {
    setExporting(true);
    try {
      const json = JSON.stringify(
        {
          persona: personaName,
          exportDate: new Date().toISOString(),
          messages: conversation,
        },
        null,
        2
      );

      const filename = `${personaName}-conversation-${new Date().toISOString().slice(0, 10)}.json`;
      downloadFile(json, filename, 'application/json');
    } finally {
      setExporting(false);
    }
  };

  const exportAsCSV = () => {
    setExporting(true);
    try {
      const csv = Papa.unparse(
        conversation.map((msg) => ({
          role: msg.role,
          speaker: msg.role === 'user' ? 'You' : personaName,
          message: msg.content,
          timestamp: new Date().toISOString(),
        }))
      );

      const filename = `${personaName}-conversation-${new Date().toISOString().slice(0, 10)}.csv`;
      downloadFile(csv, filename, 'text/csv');
    } finally {
      setExporting(false);
    }
  };

  const exportAsPDF = () => {
    setExporting(true);
    try {
      const doc = new jsPDF();
      let yPosition = 20;
      const pageHeight = doc.internal.pageSize.getHeight();
      const margin = 20;
      const maxWidth = doc.internal.pageSize.getWidth() - 2 * margin;

      // Title
      doc.setFontSize(16);
      doc.text(`${personaName} - Conversation Export`, margin, yPosition);
      yPosition += 15;

      // Metadata
      doc.setFontSize(10);
      doc.setTextColor(100);
      doc.text(`Exported: ${new Date().toLocaleString()}`, margin, yPosition);
      yPosition += 10;

      doc.setDrawColor(200);
      doc.line(margin, yPosition, maxWidth + margin, yPosition);
      yPosition += 10;

      // Conversation
      doc.setFontSize(11);
      doc.setTextColor(0);

      conversation.forEach((msg) => {
        const speaker = msg.role === 'user' ? 'You' : personaName;
        const lines = doc.splitTextToSize(`${speaker}:\n${msg.content}`, maxWidth);

        // Check if we need a new page
        if (yPosition + lines.length * 7 > pageHeight - margin) {
          doc.addPage();
          yPosition = margin;
        }

        doc.setFont(undefined, 'bold');
        doc.text(`${speaker}:`, margin, yPosition);
        yPosition += 7;

        doc.setFont(undefined, 'normal');
        doc.text(lines, margin, yPosition);
        yPosition += lines.length * 7 + 5;
      });

      doc.save(`${personaName}-conversation-${new Date().toISOString().slice(0, 10)}.pdf`);
    } finally {
      setExporting(false);
    }
  };

  const downloadFile = (content, filename, mimeType) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const isDisabled = conversation.length === 0 || exporting;

  return (
    <div className="glass-panel rounded-xl p-6 space-y-4">
      <h3 className="font-headline-md text-on-surface">Export Conversation</h3>
      <p className="text-on-surface-variant text-sm">
        Download your conversation in multiple formats
      </p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <button
          onClick={exportAsMarkdown}
          disabled={isDisabled}
          className="py-2 px-3 rounded-lg bg-primary-container/20 border border-primary/30 text-primary hover:bg-primary-container/40 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-semibold flex items-center justify-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">description</span>
          Markdown
        </button>

        <button
          onClick={exportAsJSON}
          disabled={isDisabled}
          className="py-2 px-3 rounded-lg bg-ethics-blue/20 border border-ethics-blue/30 text-ethics-blue hover:bg-ethics-blue/40 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-semibold flex items-center justify-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">data_object</span>
          JSON
        </button>

        <button
          onClick={exportAsCSV}
          disabled={isDisabled}
          className="py-2 px-3 rounded-lg bg-science-cyan/20 border border-science-cyan/30 text-science-cyan hover:bg-science-cyan/40 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-semibold flex items-center justify-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">table_chart</span>
          CSV
        </button>

        <button
          onClick={exportAsPDF}
          disabled={isDisabled}
          className="py-2 px-3 rounded-lg bg-fiction-pink/20 border border-fiction-pink/30 text-fiction-pink hover:bg-fiction-pink/40 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-semibold flex items-center justify-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">picture_as_pdf</span>
          PDF
        </button>
      </div>

      {exporting && <p className="text-on-surface-variant text-sm">Exporting...</p>}
    </div>
  );
}
