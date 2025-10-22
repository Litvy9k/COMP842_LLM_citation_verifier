import React from "react";
import "./CitationCard.css";

const defaultPlaceholders = {
  doi: "10.1109/SUMMA64428.2024.10803746",
  title:
    "Utilizing Modern Large Language Models (LLM) for Financial Trend Analysis and Digest Creation",
  authors: "Andrei Lazarev, Dmitrii Sedov",
  date: "2025-09-22",
  abstract:
    "This paper introduces a framework using LLMs for automated financial digest generation...",
  journal:
    "2024 6th International Conference on Control Systems, Mathematical Modeling, Automation and Energy Efficiency (SUMMA)",
};

const CitationCard = ({
  title,
  fields = [],
  buttonText,
  onActionClick,
  extraButtons = [],
  disabled = false,
  tooltip = "",
}) => {
  const isButtonDisabled = disabled || fields.some((f) => !f.value);

  return (
    <div className="citation-card">
      <h3>{title}</h3>

      {fields.map((f) => (
        <div key={f.name} className="citation-field">
          <label>{f.label}</label>

          {f.type === "select" ? (
            <select value={f.value} onChange={f.onChange}>
              {f.options.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          ) : (
            <input
              type={f.type || "text"}
              value={f.value}
              onChange={f.onChange}
              placeholder={f.placeholder || defaultPlaceholders[f.name] || `Enter ${f.label}`}
            />
          )}
        </div>
      ))}

      <div className="citation-buttons">
        {buttonText && onActionClick && (
          <button
            onClick={onActionClick}
            disabled={isButtonDisabled}
            title={tooltip}
            className={isButtonDisabled ? "disabled" : ""}
          >
            {buttonText}
          </button>
        )}

        {extraButtons.map((btn, i) => (
          <button key={i} onClick={btn.onClick} className={btn.className || ""}>
            {btn.text}
          </button>
        ))}
      </div>
    </div>
  );
};

export default CitationCard;
