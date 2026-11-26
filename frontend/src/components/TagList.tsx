interface TagListProps {
  items: string[];
  emptyText?: string;
}

export default function TagList({ items, emptyText = "None detected" }: TagListProps) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">{emptyText}</p>;
  }

  return (
    <ul className="flex flex-wrap gap-2">
      {items.map((item, index) => (
        <li
          key={`${item}-${index}`}
          className="rounded-full border border-indigo-400/20 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-200"
        >
          {item}
        </li>
      ))}
    </ul>
  );
}
