/**
 * Builds a self-contained JSON export of a scan report, meant to be handed
 * directly to a coding agent (GitHub Copilot, Claude Code, ...) so it can fix
 * every finding without re-running AgentCompass. See ExportForAgentButton.tsx
 * for the UI entry point.
 */
import type { Finding, RemediationEntry, Report, SeverityLevel } from "./api";

export interface AgentFixItem {
  /** 1-based, ordered by expected score impact (highest first). */
  rank: number;
  rule_id: string;
  pillar: string;
  severity: SeverityLevel;
  /** Which agent platform this rule applies to ("all" when it applies to both). */
  platform: string;
  effort: string;
  /** Score points regained if every finding for this rule is fixed (0 when not in the remediation plan). */
  score_gain: number;
  path: string | null;
  line: number | null;
  message: string;
  context: string | null;
  /** Why this matters. */
  why: string | null;
  /** How to fix it. */
  how_to_fix: string | null;
  /** Suggested concrete action from the remediation plan, when available. */
  recommended_action: string | null;
  /** Source / citation for the underlying rule (documentation URL). */
  source: string | null;
}

export interface AgentFixExport {
  generator: "AgentCompass";
  generated_at: string;
  tool_version: string;
  ruleset_version: string;
  schema_version: string;
  repository: { source: string; ref: string | null; resolved_sha: string | null };
  score: {
    current_overall: number;
    grade: string;
    copilot: number | null;
    claude: number | null;
    target_overall: 100;
  };
  summary: {
    total_findings: number;
    errors: number;
    warnings: number;
    info: number;
    /** Sum of remediation_plan score_gain values — an estimate, not a guarantee. */
    projected_score_gain: number;
  };
  instructions_for_agent: string;
  fixes: AgentFixItem[];
}

export interface FixGroup {
  /** Best (lowest / most impactful) rank among this rule's fixes. */
  rank: number;
  rule_id: string;
  pillar: string;
  /** Worst severity across all findings for this rule. */
  severity: SeverityLevel;
  effort: string;
  /** Score points regained if every finding for this rule is fixed. */
  score_gain: number;
  /** Representative message (from the highest-ranked finding). */
  message: string;
  /** How many individual findings share this rule_id. */
  count: number;
}

const SEVERITY_RANK: Record<SeverityLevel, number> = { error: 0, warning: 1, info: 2 };

function roundTo(value: number, decimals = 1): number {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

function formatScoreValue(value: number): string {
  const rounded = roundTo(value);
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

function countBySeverity(findings: Finding[], severity: SeverityLevel): number {
  return findings.filter((f) => f.severity === severity).length;
}

function buildInstructions(report: Report): string {
  const { score, meta } = report;
  const repoLabel = meta.ref ? `${meta.source}@${meta.ref}` : meta.source;
  return (
    `This file was exported from AgentCompass, an automated auditor that scores how ready a ` +
    `repository is for AI coding agents (GitHub Copilot / Claude Code). "${repoLabel}" currently ` +
    `scores ${formatScoreValue(score.overall)}/100 (grade ${score.grade}). The "fixes" array below lists ` +
    `every warning, error, and recommendation from the scan, ordered by impact (highest score_gain ` +
    `first). For each item: read "message" and "why" to understand the problem, apply the change ` +
    `described in "how_to_fix" (and "recommended_action" when present), and check "source" if you ` +
    `need to verify against the original documentation. Work through the list in order and resolve ` +
    `every item, prioritizing "error" severity first — doing so should raise this repository's score ` +
    `to 100/100.`
  );
}

/**
 * Groups an (already rank-sorted) fixes array by rule_id, one card per
 * distinct recommendation, preserving the best rank/worst severity seen.
 * Used to render the per-recommendation checkbox list in
 * ExportSelectionModal.tsx.
 */
export function groupFixesByRule(fixes: AgentFixItem[]): FixGroup[] {
  const groups = new Map<string, FixGroup>();
  for (const fix of fixes) {
    const existing = groups.get(fix.rule_id);
    if (!existing) {
      groups.set(fix.rule_id, {
        rank: fix.rank,
        rule_id: fix.rule_id,
        pillar: fix.pillar,
        severity: fix.severity,
        effort: fix.effort,
        score_gain: fix.score_gain,
        message: fix.message,
        count: 1,
      });
      continue;
    }
    existing.count += 1;
    if (SEVERITY_RANK[fix.severity] < SEVERITY_RANK[existing.severity]) {
      existing.severity = fix.severity;
    }
    if (fix.rank < existing.rank) existing.rank = fix.rank;
  }
  return Array.from(groups.values()).sort((a, b) => a.rank - b.rank);
}

/**
 * Joins findings to the remediation plan (by rule_id) and sorts by expected
 * impact. When `selectedRuleIds` is provided, only findings/plan entries for
 * those rule_ids are included (used by the "handoff to your agent" selection
 * flow); omit it (or pass `null`) to include everything, as before.
 */
export function buildAgentFixExport(
  report: Report,
  selectedRuleIds?: ReadonlySet<string> | null,
): AgentFixExport {
  const { remediation_plan, score, meta } = report;
  const findings = selectedRuleIds
    ? report.findings.filter((f) => selectedRuleIds.has(f.rule_id))
    : report.findings;
  const relevantPlan = selectedRuleIds
    ? remediation_plan.filter((entry) => selectedRuleIds.has(entry.rule_id))
    : remediation_plan;

  const planByRule = new Map<string, RemediationEntry>();
  for (const entry of remediation_plan) {
    if (!planByRule.has(entry.rule_id)) planByRule.set(entry.rule_id, entry);
  }

  const fixes: AgentFixItem[] = findings.map((finding) => {
    const plan = planByRule.get(finding.rule_id);
    return {
      rank: plan?.rank ?? Number.MAX_SAFE_INTEGER,
      rule_id: finding.rule_id,
      pillar: finding.pillar,
      severity: finding.severity,
      platform: finding.source,
      effort: finding.effort,
      score_gain: plan ? roundTo(plan.score_gain) : 0,
      path: finding.path,
      line: finding.line,
      message: finding.message,
      context: finding.context,
      why: finding.why,
      how_to_fix: finding.fix,
      recommended_action: plan?.action ?? null,
      source: finding.doc_url,
    };
  });

  fixes.sort((a, b) => {
    if (a.rank !== b.rank) return a.rank - b.rank;
    if (a.score_gain !== b.score_gain) return b.score_gain - a.score_gain;
    const severityDiff = SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity];
    if (severityDiff !== 0) return severityDiff;
    return a.rule_id.localeCompare(b.rule_id);
  });
  fixes.forEach((fix, index) => {
    fix.rank = index + 1;
  });

  const projectedGain = relevantPlan.reduce((sum, entry) => sum + entry.score_gain, 0);

  return {
    generator: "AgentCompass",
    generated_at: new Date().toISOString(),
    tool_version: report.tool_version,
    ruleset_version: report.ruleset_version,
    schema_version: report.schema_version,
    repository: { source: meta.source, ref: meta.ref, resolved_sha: meta.resolved_sha },
    score: {
      current_overall: roundTo(score.overall),
      grade: score.grade,
      copilot: score.copilot === null ? null : roundTo(score.copilot),
      claude: score.claude === null ? null : roundTo(score.claude),
      target_overall: 100,
    },
    summary: {
      total_findings: findings.length,
      errors: countBySeverity(findings, "error"),
      warnings: countBySeverity(findings, "warning"),
      info: countBySeverity(findings, "info"),
      projected_score_gain: roundTo(projectedGain),
    },
    instructions_for_agent: buildInstructions(report),
    fixes,
  };
}

function slugify(source: string): string {
  return source.replace(/[^a-z0-9]+/gi, "-").replace(/^-+|-+$/g, "").toLowerCase();
}

/**
 * Builds the export and triggers a browser download of the JSON file.
 * `selectedRuleIds`, when provided, restricts the export to those rule_ids
 * (see buildAgentFixExport).
 */
export function downloadAgentFixExport(report: Report, selectedRuleIds?: ReadonlySet<string> | null): void {
  const data = buildAgentFixExport(report, selectedRuleIds);
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const date = new Date().toISOString().slice(0, 10);
  const filename = `agentcompass-fixes-${slugify(report.meta.source)}-${date}.json`;
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
