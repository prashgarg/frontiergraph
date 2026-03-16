import broadSiteData from "../generated/site-data-broad.json";
import type {
  CentralConcept,
  CuratedQuestion,
  CuratedQuestionGroup,
  DownloadFile,
  DownloadArtifactMap,
  MetricBundle,
  Opportunity,
  PublicLabelGloss,
  QuestionCarouselGroup,
  SiteData,
} from "./site-data";

export type {
  CentralConcept,
  CuratedQuestion,
  CuratedQuestionGroup,
  DownloadArtifactMap,
  DownloadFile,
  MetricBundle,
  Opportunity,
  PublicLabelGloss,
  QuestionCarouselGroup,
  SiteData,
};

export const data = broadSiteData as SiteData;

export function getPublicLabelGloss(conceptId: string | undefined): PublicLabelGloss | null {
  if (!conceptId) return null;
  return data.public_label_glossary[conceptId] ?? null;
}

export function getPublicLabel(conceptId: string | undefined, rawLabel: string): string {
  return getPublicLabelGloss(conceptId)?.plain_label || rawLabel;
}

export function getPublicLabelSubtitle(conceptId: string | undefined): string | null {
  return getPublicLabelGloss(conceptId)?.subtitle || null;
}

export function formatCompact(value: number): string {
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  const digits = size >= 100 || unit === 0 ? 0 : size >= 10 ? 1 : 2;
  return `${size.toFixed(digits)} ${units[unit]}`;
}
