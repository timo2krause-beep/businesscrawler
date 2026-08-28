/** Entfernt Markdown-Syntax aus einem Report-Text für eine lesbare Kurzvorschau. */
export function stripMarkdownPreview(markdown: string, maxLength = 150): string {
  const text = markdown
    .replace(/\*Generiert:[^*]*\*/g, "") // "Generiert: ..." Zeile
    .replace(/```[\s\S]*?```/g, " ") // Codeblöcke
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "") // Bilder
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1") // Links -> nur Linktext
    .replace(/^#{1,6}\s*/gm, "") // Heading-Marker
    .replace(/[*_`]/g, "") // Fett/Kursiv/Inline-Code-Marker
    .replace(/^>\s?/gm, "") // Blockquote-Marker
    .replace(/^[-•]\s+/gm, "") // Listen-Marker
    .replace(/\s+/g, " ") // Whitespace/Zeilenumbrüche zusammenfassen
    .trim();

  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength).trimEnd() + "…";
}
