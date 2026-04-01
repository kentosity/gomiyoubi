import fs from "node:fs/promises";
import path from "node:path";

const wards = [
  { slug: "chuo", nameJa: "中央区", nameEn: "Chuo" },
  { slug: "koto", nameJa: "江東区", nameEn: "Koto" },
  { slug: "sumida", nameJa: "墨田区", nameEn: "Sumida" },
];

const outputPath = path.join(process.cwd(), "public", "data", "ward-boundaries.geojson");

async function fetchWardBoundary(ward) {
  const params = new URLSearchParams({
    q: `${ward.nameJa}, 東京都, 日本`,
    format: "jsonv2",
    polygon_geojson: "1",
    limit: "1",
  });

  const response = await fetch(`https://nominatim.openstreetmap.org/search?${params.toString()}`, {
    headers: {
      "User-Agent": "gomiyoubi prototype boundary fetcher",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch ${ward.slug}: ${response.status}`);
  }

  const items = await response.json();
  if (!Array.isArray(items) || items.length === 0 || !items[0].geojson) {
    throw new Error(`No polygon returned for ${ward.slug}`);
  }

  return {
    type: "Feature",
    properties: {
      slug: ward.slug,
      nameJa: ward.nameJa,
      nameEn: ward.nameEn,
      source: "OpenStreetMap Nominatim",
    },
    geometry: items[0].geojson,
  };
}

async function main() {
  const features = [];

  for (const ward of wards) {
    features.push(await fetchWardBoundary(ward));
  }

  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(
    outputPath,
    `${JSON.stringify(
      {
        type: "FeatureCollection",
        features,
      },
      null,
      2,
    )}\n`,
  );

  console.log(`Wrote ${outputPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
