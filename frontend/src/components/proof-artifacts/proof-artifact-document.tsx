import type { ReactNode } from "react";

export function ProofArtifactDocument({ content }: { content: string }) {
  const lines = content.split("\n");
  const blocks: ReactNode[] = [];
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const key = `${index}-${line.slice(0, 24)}`;
    if (line.startsWith("- ")) {
      const items: string[] = [];
      const firstIndex = index;
      while (index < lines.length && lines[index].startsWith("- ")) {
        items.push(lines[index].slice(2));
        index += 1;
      }
      index -= 1;
      blocks.push(
        <ul className="m-0 list-none p-0" key={`list-${firstIndex}`}>
          {items.map((item, itemIndex) => (
            <li className="proof-document-list-item" key={`${itemIndex}-${item}`}>
              <span aria-hidden="true">•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>,
      );
      continue;
    }
    if (line.startsWith("# ")) {
      blocks.push(
        <h1 className="proof-document-title" key={key}>
          {line.slice(2)}
        </h1>,
      );
      continue;
    }
    if (line.startsWith("## ")) {
      blocks.push(
        <h2 className="proof-document-heading" key={key}>
          {line.slice(3)}
        </h2>,
      );
      continue;
    }
    if (!line.trim()) {
      blocks.push(<div className="h-2" key={key} />);
      continue;
    }
    blocks.push(
      <p className="proof-document-paragraph" key={key}>
        {line}
      </p>,
    );
  }

  return (
    <div className="proof-document text-[#263e35]">{blocks}</div>
  );
}
