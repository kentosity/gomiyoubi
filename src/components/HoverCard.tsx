import type { HoverPanelModel } from "../types/ui";

type HoverCardProps = {
  panel: HoverPanelModel;
};

export function HoverCard({ panel }: HoverCardProps) {
  return (
    <aside className="hover-card surface-card">
      {panel.kind === "zone" ? (
        <>
          <div className="panel-header panel-header-tight">
            <h2>{panel.title}</h2>
          </div>

          <p className="eyebrow">曜日ごとの収集</p>

          <div className="schedule-grid">
            {panel.scheduleRows.map((row) => (
              <div className={row.isActive ? "schedule-row active" : "schedule-row"} key={row.day}>
                <span className="schedule-day">{row.shortLabel}</span>
                {row.categories.length > 0 ? (
                  <div className="schedule-types">
                    {row.categories.map((category) => (
                      <div
                        className="signal-chip schedule-chip"
                        key={`${row.day}-${category.category}`}
                      >
                        <span className="signal-dot" style={{ backgroundColor: category.color }} />
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

          <div className="info-grid">
            {panel.infoRows.map((row) => (
              <div className="info-row" key={row.label}>
                <span>{row.label}</span>
                {row.kind === "text" ? (
                  <strong>{row.value}</strong>
                ) : (
                  <div className="info-value-inline">
                    <span className={`quality-badge ${row.badge.tone}`}>{row.badge.label}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      ) : panel.kind === "ward" ? (
        <>
          <div className="panel-header panel-header-tight">
            <h2>{panel.title}</h2>
          </div>

          <div className="info-grid">
            {panel.infoRows.map((row) => (
              <div className="info-row" key={row.label}>
                <span>{row.label}</span>
                {row.kind === "text" ? (
                  <strong>{row.value}</strong>
                ) : (
                  <div className="info-value-inline">
                    <span className={`quality-badge ${row.badge.tone}`}>{row.badge.label}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      ) : (
        <>
          <p className="eyebrow">詳細</p>
          <h2>{panel.title}</h2>
          <p className="panel-copy">{panel.copy}</p>
        </>
      )}
    </aside>
  );
}
