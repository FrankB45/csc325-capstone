export const formatDate = (iso) =>
  new Date(iso).toLocaleDateString("en-US", {
    month: "2-digit",
    day: "2-digit",
    year: "numeric",
  });

export const formatShortDate = (iso) =>
  new Date(iso).toLocaleDateString("en-US", { month: "numeric", day: "numeric", year: "2-digit" });
