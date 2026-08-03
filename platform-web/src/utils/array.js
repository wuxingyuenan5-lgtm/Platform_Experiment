// 将数组按长度分成多段
export function arrayChunks(arr, size) {
  const result = [];
  const len = Math.ceil(arr.length / size);

  for (let i = 0; i < len; i++) {
    result.push(arr.slice(i * size, (i + 1) * size));
  }

  return result;
}
