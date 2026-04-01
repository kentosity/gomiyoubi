import fs from "node:fs/promises";
import path from "node:path";

const wards = [
  { slug: "adachi", nameJa: "足立区", nameEn: "Adachi" },
  { slug: "arakawa", nameJa: "荒川区", nameEn: "Arakawa" },
  { slug: "bunkyo", nameJa: "文京区", nameEn: "Bunkyo" },
  { slug: "chiyoda", nameJa: "千代田区", nameEn: "Chiyoda" },
  { slug: "chuo", nameJa: "中央区", nameEn: "Chuo" },
  { slug: "edogawa", nameJa: "江戸川区", nameEn: "Edogawa" },
  { slug: "itabashi", nameJa: "板橋区", nameEn: "Itabashi" },
  { slug: "katsushika", nameJa: "葛飾区", nameEn: "Katsushika" },
  { slug: "kita", nameJa: "北区", nameEn: "Kita" },
  { slug: "koto", nameJa: "江東区", nameEn: "Koto" },
  { slug: "meguro", nameJa: "目黒区", nameEn: "Meguro" },
  { slug: "minato", nameJa: "港区", nameEn: "Minato" },
  { slug: "nakano", nameJa: "中野区", nameEn: "Nakano" },
  { slug: "nerima", nameJa: "練馬区", nameEn: "Nerima" },
  { slug: "ota", nameJa: "大田区", nameEn: "Ota" },
  { slug: "setagaya", nameJa: "世田谷区", nameEn: "Setagaya" },
  { slug: "shibuya", nameJa: "渋谷区", nameEn: "Shibuya" },
  { slug: "shinagawa", nameJa: "品川区", nameEn: "Shinagawa" },
  { slug: "shinjuku", nameJa: "新宿区", nameEn: "Shinjuku" },
  { slug: "suginami", nameJa: "杉並区", nameEn: "Suginami" },
  { slug: "sumida", nameJa: "墨田区", nameEn: "Sumida" },
  { slug: "taito", nameJa: "台東区", nameEn: "Taito" },
  { slug: "toshima", nameJa: "豊島区", nameEn: "Toshima" },
];

const outputPath = path.join(process.cwd(), "public", "data", "ward-boundaries.geojson");

async function fetchWardBoundary(ward) {
  const params = new URLSearchParams({
    q: `${ward.nameJa}, 東京都, 日本`,
    format: "jsonv2",
    polygon_geojson: "1",
    polygon_threshold: "0.0005",
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
