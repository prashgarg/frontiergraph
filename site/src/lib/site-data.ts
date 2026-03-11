import siteData from "../generated/site-data.json";
import editorialSource from "../content/editorial-opportunities.json";
import publicLabelGlossarySource from "../content/public-label-glossary.json";

export type MetricBundle = {
  papers: number;
  node_instances: number;
  edges: number;
  baseline_head_concepts: number;
  baseline_soft_coverage: number;
  suppressed_candidate_count: number;
  duplicate_loops_removed_top100: number;
};

export type RepresentativePaper = {
  paper_id: string;
  title: string;
  year: number;
  edge_src: string;
  edge_dst: string;
};

export type Opportunity = {
  pair_key: string;
  source_id: string;
  target_id: string;
  source_label: string;
  target_label: string;
  source_bucket: string;
  target_bucket: string;
  cross_field: boolean;
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
  public_pair_label: string;
  top_mediator_labels: string[];
  representative_papers: RepresentativePaper[];
  top_countries_source: string[];
  top_countries_target: string[];
  source_context_summary: string;
  target_context_summary: string;
  app_link: string;
};

export type PublicLabelGloss = {
  concept_id: string;
  plain_label?: string;
  subtitle: string;
};

export type EditorialOpportunity = {
  pair_key: string;
  headline: string;
  summary: string;
  why_it_matters: string;
  how_to_start: string;
  public_source_label: string;
  public_target_label: string;
  next_study: string;
  homepage_featured: boolean;
  opportunities_featured: boolean;
  display_order: number;
};

export type CuratedOpportunity = Opportunity & EditorialOpportunity;

export type CentralConcept = {
  concept_id: string;
  label: string;
  plain_label?: string;
  subtitle?: string;
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
  plain_label?: string;
  subtitle?: string;
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
  public_label_glossary: Record<string, PublicLabelGloss>;
  default_view: {
    regime: string;
    mapping: string;
  };
  metrics: MetricBundle;
  home: {
    featured_opportunities: Opportunity[];
    curated_opportunities: CuratedOpportunity[];
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
    curated_front_set: CuratedOpportunity[];
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

function invariant(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function normalizeEditorialSource(): EditorialOpportunity[] {
  const payload = editorialSource as Record<string, EditorialOpportunity>;
  const items = Object.values(payload);
  invariant(items.length > 0, "Editorial opportunities source is empty");
  return items.sort((left, right) => left.display_order - right.display_order);
}

function normalizePublicLabelGlossarySource(): Record<string, PublicLabelGloss> {
  const payload = publicLabelGlossarySource as Record<string, PublicLabelGloss>;
  for (const [conceptId, entry] of Object.entries(payload)) {
    invariant(entry.concept_id === conceptId, `Glossary entry ${conceptId} must keep concept_id in sync with its object key`);
    invariant(Boolean(entry.subtitle), `Glossary entry ${conceptId} must include a subtitle`);
  }
  return payload;
}

function validateCuratedSet(
  actual: CuratedOpportunity[],
  expected: EditorialOpportunity[],
  label: string,
): CuratedOpportunity[] {
  invariant(actual.length === expected.length, `${label} is out of sync with editorial-opportunities.json`);
  const actualByPair = new Map(actual.map((item) => [item.pair_key, item]));
  const ordered: CuratedOpportunity[] = [];
  for (const entry of expected) {
    const item = actualByPair.get(entry.pair_key);
    invariant(item, `${label} is missing curated pair_key ${entry.pair_key}`);
    invariant(item.display_order === entry.display_order, `${label} has stale display order for ${entry.pair_key}`);
    ordered.push(item);
  }
  return ordered;
}

function buildSiteData(): SiteData {
  const payload = siteData as SiteData;
  const editorialItems = normalizeEditorialSource();
  const glossarySource = normalizePublicLabelGlossarySource();
  const availablePairs = new Set(
    Object.values(payload.opportunities.top_slices)
      .flat()
      .map((item) => item.pair_key),
  );
  for (const item of editorialItems) {
    invariant(availablePairs.has(item.pair_key), `Curated pair_key ${item.pair_key} is not present in generated opportunity slices`);
  }

  const expectedHome = editorialItems.filter((item) => item.homepage_featured);
  const expectedOpportunities = editorialItems.filter((item) => item.opportunities_featured);
  invariant(expectedHome.length === 4, "Homepage curation must contain exactly 4 curated opportunities");
  invariant(expectedOpportunities.length === 8, "Opportunities curation must contain exactly 8 curated opportunities");
  invariant(
    Object.keys(payload.public_label_glossary ?? {}).length === Object.keys(glossarySource).length,
    "public_label_glossary is out of sync with public-label-glossary.json",
  );
  for (const [conceptId, entry] of Object.entries(glossarySource)) {
    const actual = payload.public_label_glossary?.[conceptId];
    invariant(actual, `public_label_glossary is missing ${conceptId}`);
    invariant(actual.subtitle === entry.subtitle, `public_label_glossary has stale subtitle for ${conceptId}`);
    invariant((actual.plain_label ?? "") === (entry.plain_label ?? ""), `public_label_glossary has stale plain_label for ${conceptId}`);
  }

  return {
    ...payload,
    home: {
      ...payload.home,
      curated_opportunities: validateCuratedSet(
        payload.home.curated_opportunities ?? [],
        expectedHome,
        "home.curated_opportunities",
      ),
    },
    opportunities: {
      ...payload.opportunities,
      curated_front_set: validateCuratedSet(
        payload.opportunities.curated_front_set ?? [],
        expectedOpportunities,
        "opportunities.curated_front_set",
      ),
    },
  };
}

export const data = buildSiteData();

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
