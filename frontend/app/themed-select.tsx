"use client";

import Select, { type StylesConfig } from "react-select";

export interface SelectOption {
  value: string;
  label: string;
}

// react-select styled entirely through our CSS design tokens, so it adapts to
// light/dark automatically and never introduces off-theme (e.g. blue) colors.
const styles: StylesConfig<SelectOption, false> = {
  control: (base, state) => ({
    ...base,
    minWidth: "13rem",
    backgroundColor: "var(--surface-2)",
    borderColor: state.isFocused ? "var(--accent)" : "var(--border)",
    borderRadius: "0.5rem",
    minHeight: "2.5rem",
    boxShadow: state.isFocused ? "0 0 0 3px var(--ring)" : "none",
    ":hover": { borderColor: "var(--accent)" },
    transition: "border-color 0.15s ease, box-shadow 0.15s ease",
  }),
  singleValue: (base) => ({ ...base, color: "var(--text)" }),
  input: (base) => ({ ...base, color: "var(--text)" }),
  placeholder: (base) => ({ ...base, color: "var(--muted)" }),
  indicatorSeparator: (base) => ({ ...base, backgroundColor: "var(--border)" }),
  dropdownIndicator: (base, state) => ({
    ...base,
    color: state.isFocused ? "var(--accent)" : "var(--muted)",
    ":hover": { color: "var(--accent)" },
  }),
  menu: (base) => ({
    ...base,
    backgroundColor: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: "0.75rem",
    overflow: "hidden",
    boxShadow: "var(--shadow-lg)",
    zIndex: 30,
  }),
  menuList: (base) => ({ ...base, padding: "0.25rem" }),
  option: (base, state) => ({
    ...base,
    cursor: "pointer",
    borderRadius: "0.5rem",
    color: state.isSelected ? "var(--accent-foreground)" : "var(--text)",
    backgroundColor: state.isSelected
      ? "var(--accent)"
      : state.isFocused
      ? "var(--surface-2)"
      : "transparent",
    ":active": { backgroundColor: "var(--surface-2)" },
  }),
};

export default function ThemedSelect({
  options,
  value,
  onChange,
  inputId,
  ariaLabel,
}: {
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  inputId?: string;
  ariaLabel?: string;
}) {
  const selected = options.find((o) => o.value === value) ?? null;
  return (
    <Select<SelectOption, false>
      inputId={inputId}
      aria-label={ariaLabel}
      options={options}
      value={selected}
      onChange={(opt) => opt && onChange(opt.value)}
      isSearchable={false}
      styles={styles}
      // Avoid SSR/hydration id mismatches in Next.js.
      instanceId={inputId ?? "themed-select"}
    />
  );
}
