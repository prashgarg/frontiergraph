import siteData from "../generated/site-data.json";
import editorialSource from "../content/editorial-opportunities.json";
import questionsCarouselAssignmentsSource from "../content/questions-carousel-assignments.json";
import publicLabelGlossarySource from "../content/public-label-glossary.json";

export type MetricBundle = {
  papers: number;
  papers_with_extracted_edges: number;
  normalized_graph_papers: number;
  node_instances: number;
  edges: number;
  normalized_links: number;
  normalized_directed_links: number;
  normalized_undirected_links: number;
  native_concepts: number;
  visible_public_questions: number;
};

export type RepresentativePaper = {
  paper_id: string;
  title: string;
  year: number;
  edge_src: string;
  edge_dst: string;
  edge_src_display_label?: string;
  edge_dst_display_label?: string;
};

export type Opportunity = {
  pair_key: string;
  source_id: string;
  target_id: string;
  source_label: string;
  target_label: string;
  source_display_label?: string;
  target_display_label?: string;
  source_display_concept_id?: string;
  target_display_concept_id?: string;
  source_display_refined?: boolean;
  target_display_refined?: boolean;
  display_refinement_confidence?: number;
  source_alternate_display_labels?: string[];
  target_alternate_display_labels?: string[];
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
  question_family: string;
  suppress_from_public_ranked_window?: boolean;
  top_mediator_labels: string[];
  top_mediator_display_labels?: string[];
  top_mediator_baseline_labels?: string[];
  representative_papers: RepresentativePaper[];
  top_countries_source: string[];
  top_countries_target: string[];
  source_context_summary: string;
  target_context_summary: string;
  common_contexts?: string;
  public_specificity_score?: number;
  app_link: string;
  display_title?: string;
  display_why?: string;
  display_first_step?: string;
  display_category?: string;
};

export type PublicLabelGloss = {
  concept_id: string;
  plain_label?: string;
  subtitle: string;
};

export type EditorialQuestion = {
  pair_key: string;
  question_title: string;
  short_why: string;
  first_next_step: string;
  who_its_for: string;
  homepage_featured: boolean;
  questions_featured: boolean;
  display_order: number;
  homepage_role: "lead" | "supporting" | "none";
  field_shelves: string[];
  collection_tags: string[];
  editorial_strength: "flagship" | "field" | "collection" | "none";
  question_family: string;
  suppress_from_public_ranked_window?: boolean;
};

export type CuratedQuestion = Opportunity & EditorialQuestion;

export type CuratedQuestionGroup = {
  slug: string;
  title: string;
  caption: string;
  items: CuratedQuestion[];
};

export type QuestionCarouselGroup = {
  slug: string;
  title: string;
  caption: string;
  items: Opportunity[];
};

export type QuestionCarouselAssignmentItem = {
  pair_key: string;
  display_title?: string;
  display_why?: string;
  display_first_step?: string;
  display_category?: string;
};

export type QuestionCarouselAssignmentGroup = {
  slug: string;
  title: string;
  items: QuestionCarouselAssignmentItem[];
};

export type CentralConcept = {
  concept_id: string;
  label: string;
  plain_label?: string;
  subtitle?: string;
  display_concept_id?: string;
  display_refined?: boolean;
  display_refinement_confidence?: number;
  alternate_display_labels?: string[];
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
  display_concept_id?: string;
  display_refined?: boolean;
  display_refinement_confidence?: number;
  alternate_display_labels?: string[];
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

export type DownloadArtifactMap = {
  [key: string]: string;
};

export type DownloadFile = {
  path: string;
  filename: string;
  size_bytes: number;
};

export type SiteData = {
  generated_at: string;
  app_url: string;
  repo_url: string;
  public_label_glossary: Record<string, PublicLabelGloss>;
  metrics: MetricBundle;
  home: {
    featured_questions: Opportunity[];
    curated_questions: CuratedQuestion[];
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
  questions: {
    slices_path: string;
    concept_opportunities_index_path: string;
    curated_front_set: CuratedQuestion[];
    field_shelves: CuratedQuestionGroup[];
    collections: CuratedQuestionGroup[];
    field_carousels: QuestionCarouselGroup[];
    use_case_carousels: QuestionCarouselGroup[];
    ranked_questions: Opportunity[];
    top_slices: Record<string, Opportunity[]>;
  };
  downloads: {
    public_db: {
      filename: string;
      public_url: string;
      sha256: string;
      db_size_bytes: number;
      db_size_gb: number;
    };
    checksum_path: string;
    manifest_path: string;
    guides: {
      readme: DownloadFile;
      data_dictionary: DownloadFile;
    };
    tier_bundles: {
      tier1: DownloadFile;
      tier2: DownloadFile;
    };
    artifacts: DownloadArtifactMap;
    artifact_details: Record<string, DownloadFile>;
  };
};

function invariant(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function normalizeEditorialSource(): EditorialQuestion[] {
  const payload = editorialSource as Record<string, EditorialQuestion>;
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

function normalizeQuestionsCarouselAssignmentsSource(): {
  field_carousels: QuestionCarouselAssignmentGroup[];
  use_case_carousels: QuestionCarouselAssignmentGroup[];
} {
  const payload = questionsCarouselAssignmentsSource as {
    field_carousels?: QuestionCarouselAssignmentGroup[];
    use_case_carousels?: QuestionCarouselAssignmentGroup[];
  };
  invariant(Array.isArray(payload.field_carousels), "Carousel assignments must include field_carousels");
  invariant(Array.isArray(payload.use_case_carousels), "Carousel assignments must include use_case_carousels");
  return {
    field_carousels: payload.field_carousels,
    use_case_carousels: payload.use_case_carousels,
  };
}

function validateCuratedSet(
  actual: CuratedQuestion[],
  expected: EditorialQuestion[],
  label: string,
): CuratedQuestion[] {
  invariant(actual.length === expected.length, `${label} is out of sync with editorial-opportunities.json`);
  const actualByPair = new Map(actual.map((item) => [item.pair_key, item]));
  const ordered: CuratedQuestion[] = [];
  for (const entry of expected) {
    const item = actualByPair.get(entry.pair_key);
    invariant(item, `${label} is missing curated pair_key ${entry.pair_key}`);
    invariant(item.display_order === entry.display_order, `${label} has stale display order for ${entry.pair_key}`);
    invariant(item.question_title === entry.question_title, `${label} has stale question_title for ${entry.pair_key}`);
    invariant(item.short_why === entry.short_why, `${label} has stale short_why for ${entry.pair_key}`);
    invariant(item.first_next_step === entry.first_next_step, `${label} has stale first_next_step for ${entry.pair_key}`);
    invariant(item.who_its_for === entry.who_its_for, `${label} has stale who_its_for for ${entry.pair_key}`);
    invariant(item.homepage_role === entry.homepage_role, `${label} has stale homepage_role for ${entry.pair_key}`);
    invariant(item.question_family === entry.question_family, `${label} has stale question_family for ${entry.pair_key}`);
    ordered.push(item);
  }
  return ordered;
}

function validateQuestionGroups(
  groups: CuratedQuestionGroup[],
  label: string,
  expectedCount: number,
): CuratedQuestionGroup[] {
  invariant(groups.length === expectedCount, `${label} should contain exactly ${expectedCount} groups`);
  for (const group of groups) {
    invariant(group.items.length === 3, `${label}.${group.slug} should contain exactly 3 questions`);
  }
  return groups;
}

function validateCarouselGroups(
  groups: QuestionCarouselGroup[],
  label: string,
  expectedAssignments: QuestionCarouselAssignmentGroup[],
): QuestionCarouselGroup[] {
  invariant(groups.length === expectedAssignments.length, `${label} should contain exactly ${expectedAssignments.length} groups`);
  for (let index = 0; index < expectedAssignments.length; index += 1) {
    const group = groups[index];
    const expected = expectedAssignments[index];
    invariant(group.slug === expected.slug, `${label}[${index}] should use slug ${expected.slug}`);
    invariant(group.title === expected.title, `${label}.${group.slug} title is out of sync with assignments`);
    invariant(group.items.length === expected.items.length, `${label}.${group.slug} should contain exactly ${expected.items.length} questions`);
    for (let itemIndex = 0; itemIndex < expected.items.length; itemIndex += 1) {
      const actualItem = group.items[itemIndex];
      const expectedItem = expected.items[itemIndex];
      invariant(
        actualItem?.pair_key === expectedItem?.pair_key,
        `${label}.${group.slug}[${itemIndex}] should contain pair_key ${expectedItem?.pair_key}`,
      );
    }
  }
  return groups;
}

function invariantGlobalCarouselUniqueness(groups: QuestionCarouselGroup[]): void {
  const seen = new Set<string>();
  const duplicates = new Set<string>();
  for (const group of groups) {
    for (const item of group.items) {
      if (seen.has(item.pair_key)) duplicates.add(item.pair_key);
      seen.add(item.pair_key);
    }
  }
  invariant(
    duplicates.size === 0,
    `Top carousel pair_keys must stay globally unique; duplicates: ${Array.from(duplicates).join(", ")}`,
  );
}

function buildSiteData(): SiteData {
  const payload = siteData as SiteData;
  const editorialItems = normalizeEditorialSource();
  const carouselAssignments = normalizeQuestionsCarouselAssignmentsSource();
  const glossarySource = normalizePublicLabelGlossarySource();
  const questionPayload = payload.questions;
  invariant(questionPayload, "Generated site data is missing questions payload");
  const availablePairs = new Set<string>();
  for (const row of Object.values(questionPayload?.top_slices ?? {}).flat()) availablePairs.add(row.pair_key);
  for (const row of questionPayload?.curated_front_set ?? []) availablePairs.add(row.pair_key);
  for (const group of questionPayload?.field_shelves ?? []) {
    for (const row of group.items ?? []) availablePairs.add(row.pair_key);
  }
  for (const group of questionPayload?.collections ?? []) {
    for (const row of group.items ?? []) availablePairs.add(row.pair_key);
  }
  for (const group of questionPayload?.field_carousels ?? []) {
    for (const row of group.items ?? []) availablePairs.add(row.pair_key);
  }
  for (const group of questionPayload?.use_case_carousels ?? []) {
    for (const row of group.items ?? []) availablePairs.add(row.pair_key);
  }
  for (const item of editorialItems) {
    invariant(availablePairs.has(item.pair_key), `Curated pair_key ${item.pair_key} is not present in generated opportunity slices`);
  }

  const expectedHome = editorialItems.filter((item) => item.homepage_featured);
  const expectedQuestions = editorialItems.filter((item) => item.questions_featured);
  invariant(expectedHome.length === 3, "Homepage curation must contain exactly 3 curated questions");
  invariant(expectedQuestions.length === 6, "Questions curation must contain exactly 6 curated questions");
  invariant(
    expectedHome.filter((item) => item.homepage_role === "lead").length === 1,
    "Homepage curation must contain exactly one lead question",
  );
  invariant(
    expectedHome.filter((item) => item.homepage_role === "supporting").length === 2,
    "Homepage curation must contain exactly two supporting questions",
  );
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

  const validatedFieldCarousels = validateCarouselGroups(
    questionPayload?.field_carousels ?? [],
    "questions.field_carousels",
    carouselAssignments.field_carousels,
  );
  const validatedUseCaseCarousels = validateCarouselGroups(
    questionPayload?.use_case_carousels ?? [],
    "questions.use_case_carousels",
    carouselAssignments.use_case_carousels,
  );
  invariantGlobalCarouselUniqueness([...validatedFieldCarousels, ...validatedUseCaseCarousels]);

  return {
    ...payload,
    home: {
      ...payload.home,
      curated_questions: validateCuratedSet(
        payload.home.curated_questions ?? [],
        expectedHome,
        "home.curated_questions",
      ),
    },
    questions: {
      ...(questionPayload ?? {}),
      curated_front_set: validateCuratedSet(
        questionPayload?.curated_front_set ?? [],
        expectedQuestions,
        "questions.curated_front_set",
      ),
      field_shelves: validateQuestionGroups(questionPayload?.field_shelves ?? [], "questions.field_shelves", 5),
      collections: validateQuestionGroups(questionPayload?.collections ?? [], "questions.collections", 5),
      field_carousels: validatedFieldCarousels,
      use_case_carousels: validatedUseCaseCarousels,
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

export function shortList(values: string[] | undefined, limit = 3): string {
  if (!values || values.length === 0) return "No dominant setting in the current public release";
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
