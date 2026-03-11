import siteData from "../generated/site-data.json";

export type MetricBundle = {
  papers: number;
  node_instances: number;
  edges: number;
  baseline_head_concepts: number;
  baseline_soft_coverage: number;
  suppressed_candidate_count: number;
  duplicate_loops_removed_top100: number;
};

export type Opportunity = {
  pair_key: string;
  source_id: string;
  target_id: string;
  source_label: string;
  target_label: string;
  source_bucket: string;
  target_bucket: string;
  score: number;
  base_score: number;
  duplicate_penalty: number;
  path_support_norm: number;
  gap_bonus: number;
  mediator_count: number;
  motif_count: number;
  cooc_count: number;
  direct_link_status: string;
  supporting_path_count: number;
  why_now: string;
  recommended_move: string;
  slice_label: string;
  top_countries_source: string[];
  top_countries_target: string[];
  source_context_summary: string;
  target_context_summary: string;
  app_link: string;
};

export type CentralConcept = {
  concept_id: string;
  label: string;
  bucket_hint: string;
  instance_support: number;
  distinct_paper_support: number;
  weighted_degree: number;
  pagerank: number;
  in_degree: number;
  out_degree: number;
  neighbor_count: number;
  top_countries: string[];
  top_units: string[];
  app_link: string;
};

export type ConceptLookupRecord = {
  concept_id: string;
  label: string;
  aliases: string[];
  bucket_hint: string;
  instance_support: number;
  distinct_paper_support: number;
  weighted_degree: number;
  pagerank: number;
  in_degree: number;
  out_degree: number;
  neighbor_count: number;
  top_countries: string[];
  top_units: string[];
  search_terms: string[];
  app_link: string;
};

export type CompareRegime = {
  regime: string;
  label: string;
  head_count: number;
  hard_coverage: number;
  soft_coverage: number;
  strict_candidate_rows: number;
  exploratory_candidate_rows: number;
  strict_concept_edges: number;
  exploratory_concept_edges: number;
};

export type CompareOverlap = {
  left: string;
  right: string;
  intersection_top100: number;
  jaccard_top100: number;
};

export type SuppressionSummary = {
  candidate_count: number;
  suppressed_count: number;
  hard_same_family_count: number;
  override_count: number;
  visible_count: number;
  top100_removed_count: number;
  top100_overlap_count: number;
  mean_duplicate_penalty_top100_after: number;
  mean_duplicate_penalty_top500_before: number;
  build_seconds: number;
  lambda_weight: number;
  generated_at: string;
  top100_after_count: number;
  removed_by_hard_block_count: number;
};

export type DownloadArtifactMap = {
  [key: string]: string;
};

export type SiteData = {
  generated_at: string;
  app_url: string;
  repo_url: string;
  default_view: {
    regime: string;
    mapping: string;
  };
  metrics: MetricBundle;
  home: {
    featured_opportunities: Opportunity[];
    featured_central_concepts: CentralConcept[];
    graph_snapshot: {
      nodes: number;
      edges: number;
      path: string;
    };
  };
  graph: {
    backbone_path: string;
    concept_index_path: string;
    concept_neighborhoods_index_path: string;
    concept_opportunities_index_path: string;
    central_concepts_path: string;
  };
  opportunities: {
    slices_path: string;
    concept_opportunities_index_path: string;
    top_slices: Record<string, Opportunity[]>;
  };
  compare: {
    summary_path: string;
    default_reason: string;
    strict_reason: string;
    regimes: CompareRegime[];
    overlaps_preview: CompareOverlap[];
  };
  suppression: {
    summary_path: string;
    summary: SuppressionSummary;
    top_before: Record<string, unknown>[];
    top_after: Record<string, unknown>[];
    removed_preview: Record<string, unknown>[];
  };
  downloads: {
    beta_db: {
      filename: string;
      public_url: string;
      sha256: string;
      db_size_gb: number;
    };
    checksum_path: string;
    manifest_path: string;
    artifacts: DownloadArtifactMap;
  };
};

export const data = siteData as SiteData;

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function formatCompact(value: number): string {
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function shortList(values: string[] | undefined, limit = 3): string {
  if (!values || values.length === 0) return "No dominant setting in the current public sample";
  return values.slice(0, limit).join(", ");
}

export function safeCount(value: number | null | undefined): number {
  if (typeof value !== "number" || Number.isNaN(value) || !Number.isFinite(value)) return 0;
  return value;
}

export function titleCase(value: string): string {
  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
