export interface FilterValues {
  search: string;
  risk_category: string;
  gender: string;
  primary_diagnosis_group: string;
}

export interface FilterOption {
  value: string;
  label: string;
}

interface FilterBarProps {
  filters: FilterValues;
  genderOptions: FilterOption[];
  diagnosisOptions: FilterOption[];
  onChange: (next: FilterValues) => void;
  onReset: () => void;
}

export function FilterBar({ filters, genderOptions, diagnosisOptions, onChange, onReset }: FilterBarProps) {
  const update = (key: keyof FilterValues, value: string) => {
    onChange({ ...filters, [key]: value });
  };

  return (
    <section className="filter-bar" aria-label="Patient queue filters">
      <label className="field field--search">
        <span>Search</span>
        <input
          value={filters.search}
          onChange={(event) => update('search', event.target.value)}
          placeholder="Name, patient ID, or encounter"
          type="search"
        />
      </label>
      <label className="field">
        <span>Risk Category</span>
        <select value={filters.risk_category} onChange={(event) => update('risk_category', event.target.value)}>
          <option value="">All risks</option>
          <option value="High Risk">High Risk</option>
          <option value="Medium Risk">Medium Risk</option>
          <option value="Low Risk">Low Risk</option>
        </select>
      </label>
      <label className="field">
        <span>Gender</span>
        <select value={filters.gender} onChange={(event) => update('gender', event.target.value)}>
          <option value="">All genders</option>
          {genderOptions.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>
      <label className="field field--diagnosis">
        <span>Diagnosis Group</span>
        <select value={filters.primary_diagnosis_group} onChange={(event) => update('primary_diagnosis_group', event.target.value)}>
          <option value="">All diagnosis groups</option>
          {diagnosisOptions.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>
      <button className="secondary-button filter-reset" type="button" onClick={onReset}>
        Clear
      </button>
    </section>
  );
}
