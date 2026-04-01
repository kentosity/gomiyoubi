import { type CSSProperties } from "react";
import type { CategoryKey, DayKey } from "../data/schedule";
import type { CategoryOptionModel, DayOptionModel } from "../types/ui";
import { MULTI_CATEGORY_COLOR } from "../lib/mapData";

type ControlPanelProps = {
  onChooseDay: (day: DayKey) => void;
  onToggleCategory: (category: CategoryKey) => void;
  dayOptions: DayOptionModel[];
  categoryOptions: CategoryOptionModel[];
};

export function ControlPanel({
  onChooseDay,
  onToggleCategory,
  dayOptions,
  categoryOptions,
}: ControlPanelProps) {
  return (
    <section className="control-panel surface-card">
      <div className="filter-block filter-block-first">
        <div className="filter-header">
          <span>曜日</span>
        </div>

        <div className="weekday-grid">
          {dayOptions.map((option) => (
            <button
              key={option.day}
              className={option.isActive ? "weekday-pill active" : "weekday-pill"}
              onClick={() => onChooseDay(option.day)}
              type="button"
              title={option.label}
            >
              {option.shortLabel}
            </button>
          ))}
        </div>
      </div>

      <div className="filter-block">
        <div className="filter-header">
          <span>品目</span>
        </div>

        <div className="category-grid">
          {categoryOptions.map((option) => (
            <button
              key={option.category}
              className={option.isActive ? "category-pill active" : "category-pill"}
              onClick={() => onToggleCategory(option.category)}
              style={{ "--category-color": option.color } as CSSProperties}
              type="button"
              title={option.label}
            >
              <span className="legend-swatch" style={{ backgroundColor: option.color }} />
              <span>{option.shortLabel}</span>
            </button>
          ))}
        </div>

        <p className="mini-caption">
          <span className="legend-swatch" style={{ backgroundColor: MULTI_CATEGORY_COLOR }} />
          複数品目は黄色で表示
        </p>
      </div>
    </section>
  );
}
