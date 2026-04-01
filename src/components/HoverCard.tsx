import type { HoverPanelModel } from "../types/ui";

type HoverCardProps = {
  activeCategorySummary: string;
  isFocusLocked: boolean;
  panel: HoverPanelModel;
  selectedDayLabel: string;
};

export function HoverCard({
  activeCategorySummary,
  isFocusLocked,
  panel,
  selectedDayLabel,
}: HoverCardProps) {
  return (
    <aside className="hover-card surface-card">
      <div className="panel-intro panel-intro-spaced">
        <p className="eyebrow">{panel.eyebrow}</p>
        <h2>{panel.title}</h2>
      </div>

      {panel.kind === "empty" ? (
        <>
          <p className="panel-copy">{panel.copy}</p>

          <div className="empty-state-summary">
            <div className="info-row">
              <span>曜日</span>
              <strong>{selectedDayLabel}</strong>
            </div>
            <div className="info-row">
              <span>モード</span>
              <strong>{isFocusLocked ? "固定中" : "ホバー"}</strong>
            </div>
            <div className="info-row">
              <span>品目</span>
              <strong>{activeCategorySummary}</strong>
            </div>
          </div>
        </>
      ) : (
        <>
          {panel.note ? <p className="panel-copy">{panel.note}</p> : null}

          {panel.scheduleRows && panel.scheduleRows.length > 0 ? (
            <>
              <p className="section-label">{panel.scheduleLabel ?? "曜日ごとの収集"}</p>

              <div className="schedule-grid">
                {panel.scheduleRows.map((row) => (
                  <div
                    className={row.isActive ? "schedule-row active" : "schedule-row"}
                    key={row.day}
                  >
                    <span className="schedule-day">{row.shortLabel}</span>
                    {row.categories.length > 0 ? (
                      <div className="schedule-types">
                        {row.categories.map((category) => (
                          <div
                            className="signal-chip schedule-chip"
                            key={`${row.day}-${category.category}`}
                          >
                            <span
                              className="signal-dot"
                              style={{ backgroundColor: category.color }}
                            />
                            <span>{category.label}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="schedule-empty">{row.emptyLabel}</span>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : null}

          <div className="info-section">
            <div className="info-grid">
              {panel.infoRows.map((row) => (
                <div className="info-row" key={row.label}>
                  <span>{row.label}</span>
                  {row.url ? (
                    <a href={row.url} target="_blank" rel="noreferrer">
                      {row.value}
                    </a>
                  ) : (
                    <strong>{row.value}</strong>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </aside>
  );
}
