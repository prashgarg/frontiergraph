import siteData from "../generated/site-data.json";

export type Opportunity = {
  opportunity: string;
  code_pair: string;
  source_field: string;
  source_field_name: string;
  target_field: string;
  target_field_name: string;
  novelty: string;
  priority: number;
  base_score: number;
  prior_contact: number;
  mediators: number;
  motifs: number;
  project_shape: string;
  why_now: string;
  app_link: string;
};

export const data = siteData as any;

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
