import { StatusBadge } from "@/components/common/status-badge";
import type {
  KnowledgeCategory,
  KnowledgeItem,
} from "@/lib/onboarding-data";

const categoryIcons: Record<KnowledgeCategory, string> = {
  Education: "ED",
  Programs: "PR",
  Experience: "EX",
  Projects: "PJ",
  Achievements: "AC",
  Skills: "SK",
};

export function KnowledgeSection({
  category,
  items,
}: {
  category: KnowledgeCategory;
  items: KnowledgeItem[];
}) {
  return (
    <section aria-labelledby={`knowledge-${category.toLowerCase()}`}>
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-[#eef3ef] text-[9px] font-extrabold tracking-wide text-[#547067]">
            {categoryIcons[category]}
          </span>
          <h3
            className="text-xs font-bold uppercase tracking-[0.13em] text-[#52665f]"
            id={`knowledge-${category.toLowerCase()}`}
          >
            {category}
          </h3>
        </div>
        <span className="text-xs font-medium text-[#94a19c]">{items.length}</span>
      </div>

      {items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[#dbe3de] bg-[#fafbf8] px-4 py-3 text-xs text-[#98a49f]">
          Listening for details…
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <article
              className="animate-[fade-in_350ms_ease-out] rounded-2xl border border-[#dde5df] bg-white p-3.5 shadow-[0_8px_20px_-18px_rgba(20,58,46,0.6)]"
              key={item.id}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="text-sm font-semibold leading-5 text-[#1d3a31]">
                  {item.title}
                </p>
                <StatusBadge status={item.status} />
              </div>
              <p className="mt-1.5 text-xs leading-5 text-[#6e7e78]">
                {item.detail}
              </p>
              {item.evidence && (
                <p className="mt-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-[#91a09a]">
                  Source · {item.evidence}
                </p>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
