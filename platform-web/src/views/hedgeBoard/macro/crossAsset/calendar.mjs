const closedDays = {
  2026: new Set(['01-01','01-19','02-16','04-03','05-25','06-19','07-03','09-07','11-26','12-25']),
  2027: new Set(['01-01','01-18','02-15','03-26','05-31','06-18','07-05','09-06','11-25','12-24']),
  2028: new Set(['01-17','02-21','04-14','05-29','06-19','07-04','09-04','11-23','12-25']),
};
const earlyCloses = new Set(['2026-11-27','2026-12-24','2027-11-26','2028-07-03','2028-11-24']);
const nyTime = new Intl.DateTimeFormat('en-CA', { timeZone:'America/New_York', year:'numeric',month:'2-digit',day:'2-digit',weekday:'short',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23' });
export function sessionAt(now = Date.now()) {
  const parts = Object.fromEntries(nyTime.formatToParts(now).map(p=>[p.type,p.value]));
  const monthDay = `${parts.month}-${parts.day}`, date = `${parts.year}-${monthDay}`;
  const holidays = closedDays[parts.year];
  if (!holidays) return { date, open:false, phase:'calendar-unavailable' };
  if (['Sat','Sun'].includes(parts.weekday) || holidays.has(monthDay)) return { date, open:false, phase:'closed-day' };
  const seconds = +parts.hour*3600 + +parts.minute*60 + +parts.second;
  const opening = 9*3600 + 30*60, closing = (earlyCloses.has(date) ? 13 : 16)*3600;
  const phase = seconds<opening ? 'before-open' : seconds<closing ? 'open' : 'after-close';
  const boundary = phase==='before-open' ? opening : phase==='open' ? closing : null;
  return { date, open:phase==='open', phase, earlyClose:closing===13*3600,
    ...(boundary !== null && { recheckInMs:(boundary-seconds)*1000-now%1000 }) };
}
