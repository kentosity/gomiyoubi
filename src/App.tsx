import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl, { Map } from "maplibre-gl";
import {
  categoryMeta,
  type CategorySignal,
  type DayKey,
  wardSchedules,
  weekdayMeta,
  weekdayOrder
} from "./data/prototypeData";

type WardFeature = GeoJSON.Feature<GeoJSON.Geometry, Record<string, unknown>>;
type WardFeatureCollection = GeoJSON.FeatureCollection<
  GeoJSON.Geometry,
  Record<string, unknown>
>;

const TOKYO_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "&copy; OpenStreetMap contributors"
    }
  },
  layers: [
    {
      id: "osm",
      type: "raster",
      source: "osm"
    }
  ]
};

function getDayKeyFromDate(date: Date): DayKey {
  return weekdayOrder[date.getDay()];
}

function getDefaultTomorrow(): DayKey {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return getDayKeyFromDate(tomorrow);
}

function getToday(): DayKey {
  return getDayKeyFromDate(new Date());
}

function getSignalsForWard(slug: string, day: DayKey): CategorySignal[] {
  return wardSchedules[slug]?.daySignals[day] ?? [];
}

function getDominantColor(slug: string, day: DayKey): string {
  const signals = getSignalsForWard(slug, day);
  if (signals.length === 0) {
    return "#475569";
  }

  const dominant = [...signals].sort((left, right) => right.areas - left.areas)[0];
  return categoryMeta[dominant.category].color;
}

function buildWardData(features: WardFeature[], selectedDay: DayKey): WardFeatureCollection {
  return {
    type: "FeatureCollection",
    features: features.map((feature) => {
      const slug = String(feature.properties?.slug ?? "");
      const signals = getSignalsForWard(slug, selectedDay);
      return {
        ...feature,
        properties: {
          ...feature.properties,
          fillColor: getDominantColor(slug, selectedDay),
          signalCount: signals.length,
          sourceQuality: wardSchedules[slug]?.sourceQuality ?? "pending"
        }
      };
    })
  };
}

function App() {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const rawFeaturesRef = useRef<WardFeature[]>([]);
  const [selectedDay, setSelectedDay] = useState<DayKey>(getDefaultTomorrow);
  const [hoveredWardSlug, setHoveredWardSlug] = useState<string>("chuo");
  const [activeMode, setActiveMode] = useState<"today" | "tomorrow" | "manual">("tomorrow");

  const hoveredWard = wardSchedules[hoveredWardSlug];
  const hoveredSignals = useMemo(
    () => getSignalsForWard(hoveredWardSlug, selectedDay),
    [hoveredWardSlug, selectedDay]
  );

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) {
      return;
    }

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: TOKYO_STYLE,
      center: [139.805, 35.67],
      zoom: 10.8,
      minZoom: 9.8
    });

    map.addControl(new maplibregl.NavigationControl(), "bottom-right");
    mapRef.current = map;

    map.on("load", async () => {
      const response = await fetch("/data/ward-boundaries.geojson");
      const geojson: WardFeatureCollection = await response.json();
      rawFeaturesRef.current = geojson.features;

      map.addSource("wards", {
        type: "geojson",
        data: buildWardData(geojson.features, selectedDay)
      });

      map.addLayer({
        id: "ward-fill",
        type: "fill",
        source: "wards",
        paint: {
          "fill-color": ["coalesce", ["get", "fillColor"], "#334155"],
          "fill-opacity": [
            "case",
            ["==", ["get", "sourceQuality"], "pending"],
            0.26,
            0.52
          ]
        }
      });

      map.addLayer({
        id: "ward-outline",
        type: "line",
        source: "wards",
        paint: {
          "line-color": [
            "case",
            ["==", ["get", "slug"], hoveredWardSlug],
            "#f8fafc",
            "#dbe4f0"
          ],
          "line-width": [
            "case",
            ["==", ["get", "slug"], hoveredWardSlug],
            3,
            1.4
          ],
          "line-opacity": 0.95
        }
      });

      map.on("mousemove", "ward-fill", (event) => {
        const ward = event.features?.[0];
        const slug = ward?.properties?.slug;
        if (typeof slug === "string") {
          setHoveredWardSlug(slug);
        }
      });

      map.on("mouseleave", "ward-fill", () => {
        setHoveredWardSlug("");
      });

      const bounds = new maplibregl.LngLatBounds();
      for (const feature of geojson.features) {
        const geometry = feature.geometry;
        if (geometry.type === "Polygon") {
          for (const ring of geometry.coordinates) {
            for (const [lng, lat] of ring) {
              bounds.extend([lng, lat]);
            }
          }
        }
      }
      map.fitBounds(bounds, { padding: 64, duration: 0 });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [hoveredWardSlug, selectedDay]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const source = map.getSource("wards") as maplibregl.GeoJSONSource | undefined;
    if (source && rawFeaturesRef.current.length > 0) {
      source.setData(buildWardData(rawFeaturesRef.current, selectedDay));
    }

    if (map.getLayer("ward-outline")) {
      map.setPaintProperty("ward-outline", "line-color", [
        "case",
        ["==", ["get", "slug"], hoveredWardSlug],
        "#f8fafc",
        "#dbe4f0"
      ]);
      map.setPaintProperty("ward-outline", "line-width", [
        "case",
        ["==", ["get", "slug"], hoveredWardSlug],
        3,
        1.4
      ]);
    }
  }, [hoveredWardSlug, selectedDay]);

  function chooseToday() {
    setSelectedDay(getToday());
    setActiveMode("today");
  }

  function chooseTomorrow() {
    setSelectedDay(getDefaultTomorrow());
    setActiveMode("tomorrow");
  }

  function chooseManual(day: DayKey) {
    setSelectedDay(day);
    setActiveMode("manual");
  }

  return (
    <div className="app-shell">
      <div className="map-canvas" ref={mapContainerRef} />

      <section className="control-panel">
        <p className="eyebrow">Tokyo Trash Prototype</p>
        <h1>Pick the day. Read the map.</h1>
        <p className="panel-copy">
          Default mode is <strong>tomorrow</strong>, so people can decide today where they
          need to go next. The current prototype shows ward-level signals for Chuo and Koto
          and keeps Sumida visible as an unfinished source.
        </p>

        <div className="mode-row">
          <button
            className={activeMode === "tomorrow" ? "mode-pill active" : "mode-pill"}
            onClick={chooseTomorrow}
            type="button"
          >
            Tomorrow
          </button>
          <button
            className={activeMode === "today" ? "mode-pill active" : "mode-pill"}
            onClick={chooseToday}
            type="button"
          >
            Today
          </button>
        </div>

        <div className="weekday-grid">
          {weekdayOrder.map((day) => (
            <button
              key={day}
              className={selectedDay === day ? "weekday-pill active" : "weekday-pill"}
              onClick={() => chooseManual(day)}
              type="button"
            >
              {weekdayMeta[day].shortLabel}
            </button>
          ))}
        </div>

        <div className="legend">
          {Object.entries(categoryMeta).map(([key, meta]) => (
            <div className="legend-row" key={key}>
              <span className="legend-swatch" style={{ backgroundColor: meta.color }} />
              <span>{meta.label}</span>
            </div>
          ))}
        </div>
      </section>

      <aside className="hover-card">
        {hoveredWard ? (
          <>
            <p className="eyebrow">{hoveredWard.wardNameJa}</p>
            <h2>{hoveredWard.wardNameEn}</h2>
            <p className="hover-day">{weekdayMeta[selectedDay].label}</p>
            <p className="granularity">{hoveredWard.granularity}</p>

            <div className="quality-row">
              <span className={`quality-badge ${hoveredWard.sourceQuality}`}>
                {hoveredWard.sourceQuality}
              </span>
              <span className="quality-copy">
                {hoveredSignals.length > 0
                  ? `${hoveredSignals.length} category signals on this day`
                  : "No normalized day signal yet"}
              </span>
            </div>

            <div className="signal-list">
              {hoveredSignals.length > 0 ? (
                hoveredSignals.map((signal) => (
                  <div className="signal-chip" key={signal.category}>
                    <span
                      className="signal-dot"
                      style={{ backgroundColor: categoryMeta[signal.category].color }}
                    />
                    <span>{categoryMeta[signal.category].label}</span>
                    <strong>{signal.areas}</strong>
                  </div>
                ))
              ) : (
                <div className="empty-state">
                  Sumida is on the map so the UI reflects the real backlog, but its schedule
                  PDFs still need weekday extraction.
                </div>
              )}
            </div>

            <div className="notes">
              {hoveredWard.notes.map((note) => (
                <p key={note}>{note}</p>
              ))}
            </div>
          </>
        ) : (
          <>
            <p className="eyebrow">Hover a ward</p>
            <h2>Ward details</h2>
            <p className="panel-copy">
              Move over Chuo, Koto, or Sumida to inspect the day-specific signal summary.
            </p>
          </>
        )}
      </aside>
    </div>
  );
}

export default App;
