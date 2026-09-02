export function formatHeight(heightIn) {
  if (heightIn == null) return "—";
  const feet = Math.floor(heightIn / 12);
  const inches = Math.round(heightIn % 12);
  return `${feet}'${inches}"`;
}
