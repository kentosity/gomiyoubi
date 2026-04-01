import { type DayKey, weekdayOrder } from "../data/schedule";

export function getDayKeyFromDate(date: Date): DayKey {
  return weekdayOrder[date.getDay()];
}

export function getTomorrowDayKey(): DayKey {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return getDayKeyFromDate(tomorrow);
}
