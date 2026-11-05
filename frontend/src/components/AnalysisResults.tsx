import {
  AlertTriangle,
  ClipboardList,
  ShieldAlert,
  Stethoscope,
  TestTube2,
} from "lucide-react";
import type { AnalysisResult, AnalysisValue } from "../types/api";
import { Badge } from "./WorkspaceUI";

function ResultValue({ value }: { value: AnalysisValue }) {
  if (value === null) return <span>Not provided</span>;
  if (Array.isArray(value))
    return (
      <ul className="result-list">
        {value.map((item, i) => (
          <li key={i}>
            <ResultValue value={item} />
          </li>
        ))}
      </ul>
    );
  if (typeof value === "object")
    return (
      <dl className="result-properties">
        {Object.entries(value).map(([key, item]) => (
          <div key={key}>
            <dt>{key.replace(/_/g, " ")}</dt>
            <dd>
              <ResultValue value={item} />
            </dd>
          </div>
        ))}
      </dl>
    );
  return <span>{String(value)}</span>;
}

export function AnalysisResults({
  analysis,
  stale,
}: {
  analysis: AnalysisResult;
  stale: boolean;
}) {
  const groups = [
    {
      title: "Critical alerts",
      values: analysis.critical_alerts,
      icon: ShieldAlert,
      tone: "critical",
    },
    {
      title: "Medication warnings",
      values: analysis.medication_warnings,
      icon: AlertTriangle,
      tone: "warning",
    },
    {
      title: "Possible diagnoses",
      values: analysis.possible_diagnoses,
      icon: Stethoscope,
      tone: "neutral",
    },
    {
      title: "Recommended tests",
      values: analysis.recommended_tests,
      icon: TestTube2,
      tone: "neutral",
    },
  ];
  return (
    <div className="analysis-results" aria-label="Clinical analysis results">
      <div className="results-heading">
        <h3>Clinical review</h3>
        <Badge tone={stale ? "warning" : "success"}>
          {stale ? "Context changed" : "Response received"}
        </Badge>
      </div>
      {stale ? (
        <div className="notice notice-warning">
          <AlertTriangle size={18} />
          <span>
            Patient information has changed since this analysis. Run it again to
            include the latest saved information.
          </span>
        </div>
      ) : null}
      <div className="result-summary">
        <span className="small-caps">
          AI-GENERATED SUMMARY · ANALYSIS #{analysis.analysis_id}
        </span>
        <p>{analysis.summary || "No summary returned."}</p>
      </div>
      <div className="result-groups">
        {groups.map(({ title, values, icon: Icon, tone }) => (
          <section
            key={title}
            className={`result-group ${values?.length ? `result-${tone}` : ""}`}
          >
            <h4>
              <Icon size={17} />
              {title}
            </h4>
            {values?.length ? (
              <ul className="result-list">
                {values.map((value, i) => (
                  <li key={i}>
                    <ResultValue value={value} />
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty-caption">
                No {title.toLowerCase()} returned.
              </p>
            )}
          </section>
        ))}
        <section className="result-group">
          <h4>
            <ClipboardList size={17} />
            Recommended specialist
          </h4>
          <p>
            {analysis.recommended_specialist ||
              "No specialist recommendation returned."}
          </p>
        </section>
      </div>
    </div>
  );
}
