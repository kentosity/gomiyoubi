import { useState } from "react";
import { categoryMeta, type CategoryKey, type DayKey } from "../data/prototypeData";
import { getTomorrowDayKey } from "../lib/day";

const ALL_CATEGORIES = Object.keys(categoryMeta) as CategoryKey[];

export function useTrashFilters() {
  const [selectedDay, setSelectedDay] = useState<DayKey>(() => getTomorrowDayKey());
  const [selectedCategories, setSelectedCategories] = useState<CategoryKey[]>(ALL_CATEGORIES);

  function chooseDay(day: DayKey) {
    setSelectedDay(day);
  }

  function toggleCategory(category: CategoryKey) {
    setSelectedCategories((current) => {
      if (current.includes(category)) {
        return current.filter((entry) => entry !== category);
      }

      return [...current, category];
    });
  }

  return {
    chooseDay,
    selectedCategories,
    selectedDay,
    toggleCategory,
  };
}
