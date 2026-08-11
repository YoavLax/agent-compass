import { useEffect, useMemo, useRef, useState } from "react";
import type { Report } from "../api";
import { buildAgentFixExport, groupFixesByRule, type FixGroup } from "../agentExport";
import { effortStyle, formatPoints } from "../format";
import { SEVERITY_LABELS } from "../format";
import type { SeverityLevel } from "../api";

interface ExportSelectionModalProps {
  report: Report;
  onClose: () => void;
  /** Fires with the set of rule_ids the user checked, then the caller downloads. */
  onHandoff: (selectedRuleIds: Set<string>) => void;
}

const SEVERITY_DOT: Record<SeverityLevel, string> = {
  error: "bg-danger-500",
  warning: "bg-warning-500",
  info: "bg-brandblue",
};

/**
 * Full-screen-style overlay listing every recommendation (grouped by
 * rule_id) with a checkbox, so the user can pick a subset before exporting.
 * Opened from ExportForAgentButton.tsx; purely client-side, same underlying
 * data (report.findings + report.remediation_plan) as the direct export.
 */
export function ExportSelectionModal({ report, onClose, onHandoff }: ExportSelectionModalProps) {
  const groups = useMemo<FixGroup[]>(
    () => groupFixesByRule(buildAgentFixExport(report).fixes),
    [report],
  );
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(groups.map((g) => g.rule_id)),
  );
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  useEffect(() => {
    dialogRef.current?.focus();
  }, []);

  const allSelected = selected.size === groups.length && groups.length > 0;
  const noneSelected = selected.size === 0;

  function toggleAll() {
    setSelected(allSelected ? new Set() : new Set(groups.map((g) => g.rule_id)));
  }

  function toggleOne(ruleId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(ruleId)) next.delete(ruleId);
      else next.add(ruleId);
      return next;
    });
  }

  // Recomputed from the same buildAgentFixExport() the actual download uses
  // (rather than summing each group's already-rounded score_gain), so the
  // live preview here always matches the exported file's projected_score_gain.
  const selectedGain = useMemo(
    () => buildAgentFixExport(report, selected).summary.projected_score_gain,
    [report, selected],
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 p-4 backdrop-blur-sm dark:bg-black/70"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-selection-title"
        tabIndex={-1}
        className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-card-md focus:outline-none dark:border-night-border dark:bg-night-card"
      >
        <div className="flex items-start justify-between gap-4 border-b border-gray-200 px-5 py-4 dark:border-night-border">
          <div>
            <h2 id="export-selection-title" className="text-base font-semibold text-gray-900 dark:text-night-text">
              Select recommendations to hand off
            </h2>
            <p className="mt-0.5 text-sm text-gray-500 dark:text-night-muted">
              Choose which findings to include, then hand the rest off to your agent.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="focus-ring shrink-0 rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-night-border dark:hover:text-night-text"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6 6 18" />
            </svg>
          </button>
        </div>

        <div className="flex items-center justify-between gap-3 border-b border-gray-100 bg-gray-50 px-5 py-2.5 dark:border-night-border dark:bg-night-page/60">
          <label className="focus-ring flex cursor-pointer items-center gap-2 rounded text-sm font-medium text-gray-700 dark:text-night-text">
            <input
              type="checkbox"
              checked={allSelected}
              ref={(el) => {
                if (el) el.indeterminate = !allSelected && !noneSelected;
              }}
              onChange={toggleAll}
              className="h-4 w-4 rounded border-gray-300 text-brand focus:ring-primary-500 dark:border-night-border"
            />
            Select all
          </label>
          <span className="text-xs text-gray-500 dark:text-night-muted">
            {selected.size} of {groups.length} selected
          </span>
        </div>

        <ul className="flex-1 divide-y divide-gray-100 overflow-y-auto dark:divide-night-border">
          {groups.map((group) => {
            const checked = selected.has(group.rule_id);
            return (
              <li key={group.rule_id}>
                <label className="flex cursor-pointer items-start gap-3 px-5 py-3 hover:bg-gray-50 dark:hover:bg-night-border/40">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleOne(group.rule_id)}
                    className="mt-1 h-4 w-4 shrink-0 rounded border-gray-300 text-brand focus:ring-primary-500 dark:border-night-border"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap text-xs font-medium text-gray-600 dark:text-night-muted">
                        <span className={`h-1.5 w-1.5 rounded-full ${SEVERITY_DOT[group.severity]}`} aria-hidden="true" />
                        {SEVERITY_LABELS[group.severity]}
                      </span>
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${effortStyle(group.effort)}`}>
                        {group.effort}
                      </span>
                      {group.score_gain > 0 && (
                        <span className="inline-flex items-center rounded-full bg-brand px-2 py-0.5 text-[11px] font-semibold text-white">
                          +{formatPoints(group.score_gain)} pts
                        </span>
                      )}
                      {group.count > 1 && (
                        <span className="text-[11px] text-gray-400 dark:text-gray-500">
                          &times;{group.count}
                        </span>
                      )}
                    </span>
                    <span className="mt-1 block text-sm text-gray-700 [overflow-wrap:anywhere] dark:text-night-text">
                      {group.message}
                    </span>
                    <span className="mt-0.5 block font-mono text-xs text-gray-400 [overflow-wrap:anywhere] dark:text-gray-500">
                      {group.rule_id}
                    </span>
                  </span>
                </label>
              </li>
            );
          })}
        </ul>

        <div className="flex items-center justify-between gap-3 border-t border-gray-200 px-5 py-4 dark:border-night-border">
          <span className="text-xs text-gray-500 dark:text-night-muted">
            {noneSelected ? "Nothing selected" : `+${formatPoints(selectedGain)} pts if fixed`}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="focus-ring inline-flex h-9 items-center rounded-lg border border-gray-300 px-3.5 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-night-border dark:text-night-text dark:hover:bg-night-border/40"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={noneSelected}
              onClick={() => onHandoff(selected)}
              className="focus-ring inline-flex h-9 items-center rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              Handoff to your agent
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ExportSelectionModal;
