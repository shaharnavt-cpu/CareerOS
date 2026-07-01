import { KnowledgeSection } from "@/components/knowledge/knowledge-section";
import {
  categoryOrder,
  type KnowledgeItem,
} from "@/lib/onboarding-data";

export function KnowledgePanel({
  items,
  stage,
}: {
  items: KnowledgeItem[];
  stage: number;
}) {
  return (
    <aside className="overflow-hidden rounded-[26px] border border-[#d9e3dc] bg-[#f8faf7] shadow-[0_24px_70px_-48px_rgba(20,58,46,0.65)] lg:sticky lg:top-5 lg:max-h-[calc(100vh-7.5rem)]">
      <div className="border-b border-[#dde5df] bg-white/80 px-5 py-4 backdrop-blur">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#3d8064]">
              Live Knowledge Panel
            </p>
            <h2 className="mt-1 text-lg font-semibold tracking-[-0.02em] text-[#18372d]">
              What I’m understanding
            </h2>
          </div>
          <span className="relative flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#55a47f] opacity-35" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-[#4a9b76]" />
          </span>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#e4ebe6]">
            <div
              className="h-full rounded-full bg-[#4c9573] transition-all duration-500"
              style={{ width: `${Math.min(stage * 34, 100)}%` }}
            />
          </div>
          <span className="text-[10px] font-semibold text-[#80908a]">
            {items.length} items
          </span>
        </div>
      </div>

      <div className="space-y-5 overflow-y-auto p-4 lg:max-h-[calc(100vh-14rem)]">
        {categoryOrder.map((category) => (
          <KnowledgeSection
            category={category}
            items={items.filter((item) => item.category === category)}
            key={category}
          />
        ))}
      </div>
    </aside>
  );
}
