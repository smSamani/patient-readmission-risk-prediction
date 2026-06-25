import { Link } from 'react-router-dom';
import type { PatientQueueItem, SortOrder } from '../api/patientsApi';
import { RiskBadge } from './RiskBadge';
import { displayAge, formatDisplayLabel } from '../utils/formatters';

interface PatientQueueTableProps {
  patients: PatientQueueItem[];
  sortBy: string;
  sortOrder: SortOrder;
  onSort: (column: string) => void;
}

const sortableLabels: Record<string, string> = {
  patient_name: 'Patient Name',
  age: 'Age',
  calibrated_risk_pct: 'Calibrated Risk %',
  risk_category: 'Risk Category',
};

function riskValue(value: number | null) {
  if (value === null || Number.isNaN(value)) return '—';
  return `${value.toFixed(2)}%`;
}

function SortButton({ column, sortBy, sortOrder, onSort }: { column: string; sortBy: string; sortOrder: SortOrder; onSort: (column: string) => void }) {
  const active = sortBy === column;
  const direction = active ? (sortOrder === 'asc' ? '↑' : '↓') : '↕';
  return (
    <button className={`sort-button ${active ? 'sort-button--active' : ''}`} type="button" onClick={() => onSort(column)}>
      {sortableLabels[column]} <span aria-hidden="true">{direction}</span>
    </button>
  );
}

export function PatientQueueTable({ patients, sortBy, sortOrder, onSort }: PatientQueueTableProps) {
  return (
    <div className="table-shell">
      <table className="patient-table">
        <thead>
          <tr>
            <th>Patient ID</th>
            <th><SortButton column="patient_name" sortBy={sortBy} sortOrder={sortOrder} onSort={onSort} /></th>
            <th><SortButton column="age" sortBy={sortBy} sortOrder={sortOrder} onSort={onSort} /></th>
            <th>Gender</th>
            <th>Primary Diagnosis Group</th>
            <th>Admission Source</th>
            <th>Discharge Destination</th>
            <th className="risk-column"><SortButton column="calibrated_risk_pct" sortBy={sortBy} sortOrder={sortOrder} onSort={onSort} /></th>
            <th><SortButton column="risk_category" sortBy={sortBy} sortOrder={sortOrder} onSort={onSort} /></th>
            <th>View Digital Chart</th>
          </tr>
        </thead>
        <tbody>
          {patients.map((patient) => (
            <tr key={patient.patient_id}>
              <td className="mono-cell">{patient.patient_id}</td>
              <td className="name-cell">{patient.patient_name}</td>
              <td>{displayAge(patient.display_age, patient.age_band)}</td>
              <td>{formatDisplayLabel(patient.gender) ?? '—'}</td>
              <td>{formatDisplayLabel(patient.primary_diagnosis_group) ?? '—'}</td>
              <td>{formatDisplayLabel(patient.admission_source) ?? '—'}</td>
              <td>{formatDisplayLabel(patient.discharge_destination) ?? '—'}</td>
              <td className="risk-cell">{riskValue(patient.calibrated_risk_pct)}</td>
              <td><RiskBadge category={patient.risk_category} /></td>
              <td>
                <Link className="chart-button chart-button--link" to={patient.view_digital_chart_url || `/patients/${patient.patient_id}`}>
                  Open chart
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
