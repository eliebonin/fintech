export function getCataloguePage({ page, pageSize, total }: { page: number; pageSize: number; total: number }) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const boundedPage = Math.min(Math.max(page, 1), pageCount);
  const offset = (boundedPage - 1) * pageSize;
  return {
    offset,
    pageCount,
    firstResult: total === 0 ? 0 : offset + 1,
    lastResult: Math.min(offset + pageSize, total),
  };
}
