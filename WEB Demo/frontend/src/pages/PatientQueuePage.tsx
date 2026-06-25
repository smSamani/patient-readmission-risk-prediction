import { useEffect, useMemo, useState } from 'react';
import { fetchPatients, type PatientQueueItem, type SortOrder } from '../api/patientsApi';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { FilterBar, type FilterOption, type FilterValues } from '../components/FilterBar';
import { LoadingState } from '../components/LoadingState';
import { PatientQueueTable } from '../components/PatientQueueTable';
import { WorkspaceChrome } from '../components/WorkspaceChrome';

const PAGE_SIZE = 20;
const initialFilters: FilterValues = {
  search: '',
  risk_category: '',
  gender: '',
  primary_diagnosis_group: '',
};

interface SummaryStats {
  total: number;
  highRisk: number;
  mediumRisk: number;
  lowRisk: number;
}

function calculateSummary(patients: PatientQueueItem[]): SummaryStats {
  return {
    total: patients.length,
    highRisk: patients.filter((patient) => patient.risk_category_raw === 'High Risk' || patient.risk_category === 'High Risk').length,
    mediumRisk: patients.filter((patient) => patient.risk_category_raw === 'Medium Risk' || patient.risk_category === 'Medium Risk').length,
    lowRisk: patients.filter((patient) => patient.risk_category_raw === 'Low Risk' || patient.risk_category === 'Low Risk').length,
  };
}

function uniqueOptions(items: PatientQueueItem[], rawKey: keyof PatientQueueItem, labelKey: keyof PatientQueueItem): FilterOption[] {
  const seen = new Map<string, string>();
  for (const item of items) {
    const raw = item[rawKey];
    if (typeof raw !== 'string' || raw === '') continue;
    const label = item[labelKey];
    seen.set(raw, typeof label === 'string' && label ? label : raw);
  }
  return Array.from(seen.entries())
    .map(([value, label]) => ({ value, label }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

export function PatientQueuePage() {
  const [patients, setPatients] = useState<PatientQueueItem[]>([]);
  const [allPatients, setAllPatients] = useState<PatientQueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [sortBy, setSortBy] = useState('calibrated_risk_pct');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [filters, setFilters] = useState<FilterValues>(initialFilters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestToken, setRequestToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetchPatients({ limit: 100, offset: 0, sort_by: 'calibrated_risk_pct', sort_order: 'desc' })
      .then((response) => {
        if (!cancelled) setAllPatients(response.items);
      })
      .catch(() => {
        if (!cancelled) setAllPatients([]);
      });
    return () => {
      cancelled = true;
    };
  }, [requestToken]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchPatients({
      ...filters,
      sort_by: sortBy,
      sort_order: sortOrder,
      limit: PAGE_SIZE,
      offset,
    })
      .then((response) => {
        if (cancelled) return;
        setPatients(response.items);
        setTotal(response.total);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setPatients([]);
        setTotal(0);
        setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filters, offset, requestToken, sortBy, sortOrder]);

  const summary = useMemo(() => calculateSummary(allPatients), [allPatients]);
  const genderOptions = useMemo(() => uniqueOptions(allPatients, 'gender_raw', 'gender'), [allPatients]);
  const diagnosisOptions = useMemo(() => uniqueOptions(allPatients, 'primary_diagnosis_group_raw', 'primary_diagnosis_group'), [allPatients]);

  const showingStart = total === 0 ? 0 : offset + 1;
  const showingEnd = Math.min(offset + PAGE_SIZE, total);
  const canGoPrevious = offset > 0;
  const canGoNext = offset + PAGE_SIZE < total;

  const updateFilters = (next: FilterValues) => {
    setFilters(next);
    setOffset(0);
  };

  const resetFilters = () => {
    setFilters(initialFilters);
    setOffset(0);
  };

  const retry = () => setRequestToken((token) => token + 1);

  const handleSort = (column: string) => {
    setOffset(0);
    if (sortBy === column) {
      setSortOrder((current) => (current === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortBy(column);
    setSortOrder(column === 'calibrated_risk_pct' ? 'desc' : 'asc');
  };

  return (
    <main className="app-shell queue-shell--reference">
      <WorkspaceChrome active="queue" />

      <header className="page-header">
        <div>
          <h1>Clinical Patients Dashboard</h1>
          <p>Backend-powered queue for patient readmission risk review.</p>
        </div>
        <div className="backend-status" aria-label="Backend status">
          <span className="status-dot" aria-hidden="true" />
          Active monitoring - {summary.total || total} patients
        </div>
      </header>

      <section className="summary-grid" aria-label="Queue summary">
        <article className="summary-card">
          <span>Total Patients</span>
          <strong>{summary.total || '—'}</strong>
        </article>
        <article className="summary-card summary-card--high">
          <span>High Risk</span>
          <strong>{summary.highRisk}</strong>
        </article>
        <article className="summary-card summary-card--medium">
          <span>Medium Risk</span>
          <strong>{summary.mediumRisk}</strong>
        </article>
        <article className="summary-card summary-card--low">
          <span>Low Risk</span>
          <strong>{summary.lowRisk}</strong>
        </article>
      </section>

      <FilterBar
        filters={filters}
        genderOptions={genderOptions}
        diagnosisOptions={diagnosisOptions}
        onChange={updateFilters}
        onReset={resetFilters}
      />

      <section className="queue-panel" aria-label="Patient queue table">
        <div className="queue-panel__header">
          <div>
            <h2>Patient risk queue</h2>
            <p>Sorted by calibrated readmission risk unless changed.</p>
          </div>
          <span className="result-count">Showing {showingStart}–{showingEnd} of {total}</span>
        </div>

        {loading ? <LoadingState /> : null}
        {!loading && error ? <ErrorState message={error} onRetry={retry} /> : null}
        {!loading && !error && patients.length === 0 ? <EmptyState onReset={resetFilters} /> : null}
        {!loading && !error && patients.length > 0 ? (
          <>
            <PatientQueueTable patients={patients} sortBy={sortBy} sortOrder={sortOrder} onSort={handleSort} />
            <div className="pagination-bar">
              <button className="secondary-button" type="button" disabled={!canGoPrevious} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                Previous
              </button>
              <span>Showing {showingStart}–{showingEnd} of {total}</span>
              <button className="secondary-button" type="button" disabled={!canGoNext} onClick={() => setOffset(offset + PAGE_SIZE)}>
                Next
              </button>
            </div>
          </>
        ) : null}
      </section>
    </main>
  );
}
