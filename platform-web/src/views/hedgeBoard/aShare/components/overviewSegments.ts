/** Preserve missing dates as gaps in the full-history navigator. */
export function overviewSegments(values: Array<number | null | undefined>): string[] {
  const finite = values.filter((value): value is number => value != null && Number.isFinite(value));
  if (!finite.length) return [];
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  const segments: string[] = [];
  let segment: string[] = [];
  values.forEach((value, index) => {
    if (value == null || !Number.isFinite(value)) {
      if (segment.length) segments.push(segment.join(' '));
      segment = [];
      return;
    }
    const x = (index / Math.max(values.length - 1, 1)) * 100;
    const y = max === min ? 10 : 18 - ((value - min) / (max - min)) * 16;
    segment.push(`${x.toFixed(2)},${y.toFixed(2)}`);
  });
  if (segment.length) segments.push(segment.join(' '));
  return segments;
}
