export function validSurfaceIndices(indices: ArrayLike<number>, validityData?: readonly boolean[] | null): number[] {
  if (!validityData) return Array.from(indices);
  const visible: number[] = [];
  for (let offset = 0; offset + 2 < indices.length; offset += 3) {
    const a = indices[offset];
    const b = indices[offset + 1];
    const c = indices[offset + 2];
    if (validityData[a] && validityData[b] && validityData[c]) visible.push(a, b, c);
  }
  return visible;
}
