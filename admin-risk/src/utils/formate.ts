// 转换为数字型字符串
// 是否保留末尾0,默认保留
export function formateNumStr(
  str,
  params: any = { decimals: 4, multiple: 1, suffix: '', keepZero: true },
) {
  if (!str) return '0';
  if (str == 0) return '0';
  const { decimals, multiple = 1, suffix } = params;
  let _res: any = (Number(str) * multiple).toFixed(decimals);
  if (Number(_res) == 0) {
    _res = str;
  }
  if (!params.keepZero) {
    _res = parseFloat(_res);
  }
  return formatNumberWithCommas(_res) + (suffix || '');
}

// 转换为数字型字符串保存原始精度值
export function formateNumStrSavePrecision(str, params: any = { multiple: 0, suffix: '' }) {
  if (!str) return '0';
  if (str == 0) return '0';
  const { multiple, suffix } = params;
  let _str = str.toString();
  const _len = _str.split('.')[1]?.length || 0;
  // 先化整数
  _str = Number(_str) * Math.pow(10, multiple >= 0 ? _len + multiple : _len);
  // 再转回原数
  _str = Number(_str) / Math.pow(10, multiple >= 0 ? _len : _len - multiple);
  return _str + (suffix || '');
}

// 数字加千分号
export function formatNumberWithCommas(x: any) {
  return x?.toString()?.replace(/\B(?<!\.\d*)(?=(\d{3})+(?!\d))/g, ',') || 0;
}

// 数字添加单位 万/亿
export function formatNumberWithUnit(value: any, decimals = 2) {
  // 处理无效值
  if (value === null || value === undefined || isNaN(value)) {
    return '0';
  }

  const num = Number(value);
  if (isNaN(num)) {
    return '0';
  }

  const isNegative = num < 0;
  const absValue = Math.abs(num);

  let result: string;

  if (absValue >= 100000000) {
    result = (absValue / 100000000).toFixed(decimals) + '亿';
  } else if (absValue >= 10000) {
    result = (absValue / 10000).toFixed(decimals) + '万';
  } else {
    result = absValue.toFixed(decimals);
  }

  return isNegative ? `-${result}` : result;
}
