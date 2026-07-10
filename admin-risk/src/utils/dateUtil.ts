/**
 * Independent time operation tool to facilitate subsequent switch to dayjs
 */
import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';
// 配置 duration 插件
dayjs.extend(duration);

const DATE_TIME_FORMAT = 'YYYY-MM-DD HH:mm:ss';
const DATE_TIME_M_FORMAT = 'YYYY-MM-DD HH:mm';
const DATE_TIME_H_FORMAT = 'YYYY-MM-DD HH';
const TIME_FORMAT = 'HH:mm:ss';
const DATE_FORMAT = 'YYYY-MM-DD';

export function formatToDateTime(date?: dayjs.ConfigType, format = DATE_TIME_FORMAT): string {
  return dayjs(date).format(format);
}

export function formatToTime(date?: dayjs.ConfigType, format = TIME_FORMAT): string {
  return dayjs(date).format(format);
}

export function formatToDate(date?: dayjs.ConfigType, format = DATE_FORMAT): string {
  return dayjs(date).format(format);
}

export function formatToDateTimeM(date?: dayjs.ConfigType, format = DATE_TIME_M_FORMAT): string {
  return dayjs(date).format(format);
}
export function formatToDateTimeH(date?: dayjs.ConfigType, format = DATE_TIME_H_FORMAT): string {
  return dayjs(date).format(format);
}

// 时间点距离现在时长-时间段展示
export function diffTime(time: string, endTime?: string, tz?: string) {
  if (!time) return '0';
  let _time = '';
  let _diff = new Date().getTime() - new Date(time).getTime();
  if (endTime) {
    _diff = new Date(endTime).getTime() - new Date(time).getTime();
  }
  const m = Math.floor(_diff / 1000);
  const mm = m % 60; // 秒
  const f = Math.floor(m / 60);
  const ff = f % 60; // 分钟
  const s = Math.floor(f / 60); // 小时
  const ss = s % 24;
  const day = Math.floor(s / 24); // 天数
  // _time = ss + '时' + ff + '分' + mm + '秒';

  if (day < 0) {
    return '0秒';
  }

  if (day) {
    _time = day + '天';
  }
  if (_time || ss) {
    _time += ss + '时';
  }
  if (_time || ff) {
    _time += ff + '分';
  }
  _time += mm + '秒';

  return _time;
}

// 时间点距离现在时长-倒计时
export function diffTime2(beginTime, endTime) {
  const _time = beginTime - endTime + 1000;
  return dateUtil.duration(_time > 0 ? _time : 0).format(TIME_FORMAT);
}
export const dateUtil = dayjs;

// 根据数字算出时间范围
export function getDayRangeByNum(num: number) {
  const _now = new Date();
  const _start = new Date(_now.getTime() - 1000 * 60 * 60 * 24 * num);
  return {
    start: formatToDate(_start),
    end: formatToDate(_now),
  };
}
