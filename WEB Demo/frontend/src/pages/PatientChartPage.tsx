import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchPatientChart, type DiagnosisTimelineItem, type PatientChartResponse } from '../api/patientsApi';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { RiskBadge } from '../components/RiskBadge';
import { WorkspaceChrome } from '../components/WorkspaceChrome';
import { displayAge, formatDisplayLabel } from '../utils/formatters';

function textValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'number') return String(value);
  return formatDisplayLabel(value) ?? '—';
}

function plainValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '—';
  return String(value);
}

function dateTimeValue(date: string | null | undefined, time?: string | null) {
  if (!date && !time) return '—';
  return [date, time].filter(Boolean).join(' at ');
}

function notePreview(value: string | null | undefined) {
  if (!value) return '—';
  return value.length > 112 ? `${value.slice(0, 112).trim()}...` : value;
}

function Field({ label, value, subtle }: { label: string; value: ReactNode; subtle?: boolean }) {
  return (
    <div className={`detail-field ${subtle ? 'detail-field--subtle' : ''}`}>
      <span>{label}</span>
      <strong>{value ?? '—'}</strong>
    </div>
  );
}

function IconGlyph({ name }: { name: 'back' | 'user' | 'users' | 'bed' | 'chart' | 'clipboard' | 'lab' | 'pill' | 'note' | 'building' | 'outpatient' | 'clock' | 'activity' | 'spark' | 'shield' }) {
  const common = { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', xmlns: 'http://www.w3.org/2000/svg', 'aria-hidden': true };
  const stroke = { stroke: 'currentColor', strokeWidth: 2.2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };

  if (name === 'back') return <svg {...common}><path {...stroke} d="M19 12H5" /><path {...stroke} d="m12 19-7-7 7-7" /></svg>;
  if (name === 'user') return <svg {...common}><path {...stroke} d="M20 21a8 8 0 0 0-16 0" /><circle {...stroke} cx="12" cy="7" r="4" /></svg>;
  if (name === 'users') return <svg {...common}><path {...stroke} d="M16 21a6 6 0 0 0-12 0" /><circle {...stroke} cx="10" cy="7" r="4" /><path {...stroke} d="M20 20a5 5 0 0 0-4-4.9" /><path {...stroke} d="M17 3.4a4 4 0 0 1 0 7.2" /></svg>;
  if (name === 'bed') return <svg {...common}><path {...stroke} d="M4 18V6" /><path {...stroke} d="M20 18v-5a3 3 0 0 0-3-3H8v8" /><path {...stroke} d="M4 13h16" /><path {...stroke} d="M7 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" /></svg>;
  if (name === 'chart') return <svg {...common}><path {...stroke} d="M4 19V5" /><path {...stroke} d="M8 17v-5" /><path {...stroke} d="M13 17V8" /><path {...stroke} d="M18 17v-8" /></svg>;
  if (name === 'clipboard') return <svg {...common}><path {...stroke} d="M9 5h6" /><path {...stroke} d="M9 12h6" /><path {...stroke} d="M9 16h6" /><path {...stroke} d="M8 3h8l1 2h2v16H5V5h2l1-2Z" /></svg>;
  if (name === 'lab') return <svg {...common}><path {...stroke} d="M9 3h6" /><path {...stroke} d="M10 3v5l-5 10a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3L14 8V3" /><path {...stroke} d="M8 15h8" /></svg>;
  if (name === 'pill') return <svg {...common}><path {...stroke} d="M10.5 21 21 10.5a5 5 0 0 0-7-7L3.5 14a5 5 0 0 0 7 7Z" /><path {...stroke} d="m8 9 7 7" /></svg>;
  if (name === 'note') return <svg {...common}><path {...stroke} d="M6 3h9l3 3v15H6z" /><path {...stroke} d="M14 3v4h4" /><path {...stroke} d="M9 12h6" /><path {...stroke} d="M9 16h6" /></svg>;
  if (name === 'building') return <svg {...common}><path {...stroke} d="M4 21V7h8v14" /><path {...stroke} d="M12 11h8v10" /><path {...stroke} d="M7 10h2" /><path {...stroke} d="M7 14h2" /><path {...stroke} d="M15 14h2" /></svg>;
  if (name === 'clock') return <svg {...common}><circle {...stroke} cx="12" cy="12" r="9" /><path {...stroke} d="M12 7v5l3 2" /></svg>;
  if (name === 'activity') return <svg {...common}><path {...stroke} d="M3 12h4l3 7 4-14 3 7h4" /></svg>;
  if (name === 'spark') return <svg {...common}><path {...stroke} d="M12 3 9.5 9.5 3 12l6.5 2.5L12 21l2.5-6.5L21 12l-6.5-2.5Z" /></svg>;
  if (name === 'shield') return <svg {...common}><path {...stroke} d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" /><path {...stroke} d="m9 12 2 2 4-5" /></svg>;
  return <svg {...common}><path {...stroke} d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" /><path {...stroke} d="M4 21a8 8 0 0 1 16 0" /><path {...stroke} d="M17 11h4" /><path {...stroke} d="M19 9v4" /></svg>;
}

function InfoRow({ label, value, tone = 'default' }: { label: string; value: ReactNode; tone?: 'default' | 'danger' | 'success' | 'muted' }) {
  return (
    <div className={`reference-info-row reference-info-row--${tone}`}>
      <span>{label}</span>
      <strong>{value ?? '—'}</strong>
    </div>
  );
}

function ReferencePanel({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return (
    <article className="reference-mini-panel">
      <h3>{icon}{title}</h3>
      <div className="reference-mini-panel__body">{children}</div>
    </article>
  );
}

function ReferenceMetricCard({ title, caption, value, tone = 'neutral' }: { title: string; caption?: string; value: ReactNode; tone?: 'neutral' | 'danger' | 'success' | 'blue' | 'orange' | 'muted' }) {
  return (
    <div className={`reference-metric-card reference-metric-card--${tone}`}>
      <div>
        <span>{title}</span>
        {caption ? <small>{caption}</small> : null}
      </div>
      <strong>{value ?? '—'}</strong>
    </div>
  );
}

function LevelBadge({ value }: { value: string | null | undefined }) {
  const label = textValue(value);
  const tone = label.toLowerCase().includes('high') ? 'high' : label.toLowerCase().includes('medium') ? 'medium' : label.toLowerCase().includes('low') ? 'low' : 'neutral';
  return <span className={`level-badge level-badge--${tone}`}>{label}</span>;
}

function StatTile({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="stat-tile">
      <span>{label}</span>
      <strong>{value ?? '—'}</strong>
    </div>
  );
}

function ReferenceProgressRow({ label, value, caption, tone = 'blue' }: { label: string; value: number | null | undefined; caption?: string; tone?: 'blue' | 'green' | 'orange' }) {
  const safeValue = typeof value === 'number' ? value : 0;
  const width = Math.max(3, Math.min(100, (safeValue / 10) * 100));
  return (
    <div className={`reference-progress-row reference-progress-row--${tone}`}>
      <div>
        <span>{label}</span>
        <strong>{safeValue} / 10 {caption ? <em>({caption})</em> : null}</strong>
      </div>
      <div className="reference-progress-track"><span style={{ width: `${width}%` }} /></div>
    </div>
  );
}

function BurdenRow({ icon, label, value }: { icon: ReactNode; label: string; value: number | null | undefined }) {
  const safeValue = typeof value === 'number' ? value : 0;
  const width = Math.max(6, Math.min(100, (safeValue / 10) * 100));

  return (
    <div className="burden-row">
      <span className="burden-icon">{icon}</span>
      <strong>{label}</strong>
      <div className="burden-track"><span style={{ width: `${width}%` }} /></div>
      <em>{safeValue} / 10</em>
    </div>
  );
}

function statusTone(value: string | number | null | undefined) {
  const text = String(value ?? '').toLowerCase();
  if (text.includes('high') || text.includes('critical')) return 'danger';
  if (text.includes('yes') || text.includes('active') || text.includes('diabetes')) return 'success';
  if (text.includes('low') || text.includes('no')) return 'muted';
  return 'blue';
}

function DiagnosisTimelineCompact({ items }: { items: DiagnosisTimelineItem[] }) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  if (items.length === 0) return <p className="muted-text">No diagnosis timeline rows are available.</p>;

  const toggleRow = (key: string) => {
    setExpandedRows((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="reference-timeline" aria-label="Diagnosis timeline">
      <div className="reference-timeline__head">
        <span>Date</span>
        <span>Diagnosis / Note Summary</span>
        <span>Type</span>
        <span>Status</span>
      </div>
      {items.map((item) => {
        const rowKey = `${item.diagnosis_rank}-${item.diagnosis_label}`;
        const expanded = expandedRows.has(rowKey);
        return (
          <article className="reference-timeline-row" key={rowKey}>
            <div className="reference-timeline-row__summary">
              <span>{plainValue(item.date_recorded)}</span>
              <div>
                <h4>{textValue(item.diagnosis_label)}</h4>
                <p>{notePreview(item.clinical_note)}</p>
              </div>
              <span className="reference-chip reference-chip--muted">Diagnosis</span>
              <button className="reference-chip reference-chip--success" type="button" onClick={() => toggleRow(rowKey)}>
                {expanded ? 'Hide' : 'Details'}
              </button>
            </div>
            {expanded ? (
              <div className="reference-timeline-row__details">
                <span>{plainValue(item.diagnosed_by)}</span>
                <p>{plainValue(item.clinical_note)}</p>
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}

export function PatientChartPage() {
  const { patientId } = useParams();
  const [chart, setChart] = useState<PatientChartResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestToken, setRequestToken] = useState(0);

  useEffect(() => {
    if (!patientId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchPatientChart(patientId)
      .then((response) => {
        if (!cancelled) setChart(response);
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setChart(null);
          setError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [patientId, requestToken]);

  const retry = () => setRequestToken((token) => token + 1);

  const patientIdentity = chart?.box_1_demographics_encounter.patient_identity;
  const demographics = chart?.box_1_demographics_encounter.demographics;
  const encounter = chart?.box_1_demographics_encounter.encounter_context;
  const priorUtilization = chart?.box_2_clinical_snapshot.prior_utilization;
  const admissionBurden = chart?.box_2_clinical_snapshot.current_admission_burden;
  const labs = chart?.box_3_clinical_review.labs_glycemic_monitoring;
  const medications = chart?.box_3_clinical_review.medication_review;
  const diagnosis = chart?.box_3_clinical_review.diagnosis_review;
  const mainDisplayAge = useMemo(() => displayAge(demographics?.display_age ?? (typeof demographics?.age === 'number' ? demographics.age : null), demographics?.age_band ?? null), [demographics]);

  return (
    <main className="app-shell chart-shell chart-shell--reference">
      <WorkspaceChrome active="chart" chartPath={patientId ? `/patients/${patientId}` : undefined} />

      {loading ? <section className="queue-panel"><LoadingState /></section> : null}
      {!loading && error ? <section className="queue-panel"><ErrorState message={error} onRetry={retry} /></section> : null}
      {!loading && !error && !chart ? <section className="queue-panel"><EmptyState onReset={retry} /></section> : null}

      {!loading && !error && chart && patientIdentity && demographics && encounter && priorUtilization && admissionBurden && labs && medications && diagnosis ? (
        <div className="reference-dashboard">
          <div className="reference-content">
            <Link className="reference-back-link" to="/"><IconGlyph name="back" />Back to Queue</Link>

            <section className="reference-card reference-patient-card" aria-label="Patient overview">
              <div className="reference-patient-card__top">
                <span className="reference-avatar" aria-hidden="true"><IconGlyph name="user" /></span>
                <div>
                  <div className="reference-title-row">
                    <h1>{plainValue(patientIdentity.patient_name)}</h1>
                    <RiskBadge category={patientIdentity.risk_category} />
                  </div>
                  <p className="reference-patient-meta">
                    <span>{plainValue(patientIdentity.mrn)}</span>
                    <span>{textValue(demographics.gender)}</span>
                    <span>{mainDisplayAge} years old</span>
                    <span>{plainValue(patientIdentity.ward_unit)}</span>
                  </p>
                </div>
              </div>

              <div className="reference-panel-grid reference-panel-grid--three">
                <ReferencePanel title="Primary Provider" icon={<IconGlyph name="shield" />}>
                  <InfoRow label="Physician:" value={plainValue(patientIdentity.primary_physician)} />
                  <InfoRow label="Ward / Unit:" value={plainValue(patientIdentity.ward_unit)} />
                  <InfoRow label="Room Number:" value={plainValue(patientIdentity.room_number)} />
                </ReferencePanel>

                <ReferencePanel title="Demographics" icon={<IconGlyph name="users" />}>
                  <InfoRow label="Age / Gender:" value={`${mainDisplayAge} / ${textValue(demographics.gender)}`} />
                  <InfoRow label="Age Band:" value={plainValue(demographics.age_band)} />
                  <InfoRow label="Race:" value={textValue(demographics.race)} />
                </ReferencePanel>

                <ReferencePanel title="Encounter Context" icon={<IconGlyph name="clock" />}>
                  <InfoRow label="Admission Type:" value={textValue(encounter.admission_type)} tone={textValue(encounter.admission_type).toLowerCase().includes('emergency') ? 'danger' : 'default'} />
                  <InfoRow label="Time in Hospital:" value={encounter.time_in_hospital === null ? '—' : `${encounter.time_in_hospital} Days`} />
                  <InfoRow label="Scheduled Discharge:" value={dateTimeValue(encounter.scheduled_discharge_date, encounter.scheduled_discharge_time)} />
                </ReferencePanel>
              </div>
            </section>

            <div className="reference-snapshot-grid">
              <section className="reference-card reference-snapshot-card">
                <div className="reference-section-heading">
                  <div><span className="reference-heading-icon reference-heading-icon--orange"><IconGlyph name="clock" /></span><h2>Prior Utilization (Last 12m)</h2></div>
                  <LevelBadge value={priorUtilization.utilization_level} />
                </div>
                <div className="reference-stat-grid">
                  <StatTile label="Inpatient" value={priorUtilization.prior_inpatient_visits} />
                  <StatTile label="ED Visits" value={priorUtilization.prior_emergency_visits} />
                  <StatTile label="Outpatient" value={priorUtilization.prior_outpatient_visits} />
                </div>
              </section>

              <section className="reference-card reference-snapshot-card">
                <div className="reference-section-heading">
                  <div><span className="reference-heading-icon reference-heading-icon--green"><IconGlyph name="activity" /></span><h2>Current Admission Burden</h2></div>
                  <LevelBadge value={admissionBurden.clinical_burden_level} />
                </div>
                <div className="reference-progress-list">
                  <ReferenceProgressRow label="Inpatient Utilization" value={admissionBurden.diagnoses_recorded} caption={textValue(admissionBurden.clinical_burden_level)} />
                  <ReferenceProgressRow label="Emergency Admission" value={admissionBurden.procedures} caption={admissionBurden.procedures ? undefined : 'Zero'} />
                  <ReferenceProgressRow label="Outpatient Burden" value={priorUtilization.prior_outpatient_visits} caption={priorUtilization.prior_outpatient_visits ? undefined : 'Zero'} tone="green" />
                </div>
              </section>
            </div>

            <section className="reference-card reference-clinical-card">
              <div className="reference-card-title">
                <span className="reference-card-title__icon"><IconGlyph name="clipboard" /></span>
                <div>
                  <h2>Clinical Review Panel</h2>
                  <p>Comprehensive review of lab results, active medical prescriptions, and diagnosis metrics</p>
                </div>
              </div>

              <div className="reference-review-grid">
                <article>
                  <h3><IconGlyph name="lab" />Labs & Glycemic</h3>
                  <ReferenceMetricCard title="HbA1c Status" caption="Glycemic marker" value={textValue(labs.hba1c_result_status)} />
                  <ReferenceMetricCard title="Max Glucose" caption="Highest recorded" value={textValue(labs.max_glucose_result_status)} />
                  <ReferenceMetricCard title="Lab Procedures" caption="Total count" value={labs.lab_procedures_count} tone={typeof labs.lab_procedures_count === 'number' && labs.lab_procedures_count > 30 ? 'danger' : 'neutral'} />
                </article>

                <article>
                  <h3><IconGlyph name="pill" />Medication Review</h3>
                  <ReferenceMetricCard title="Diabetes Meds" caption="Medication used" value={textValue(medications.diabetes_medication_used)} tone={statusTone(medications.diabetes_medication_used)} />
                  <ReferenceMetricCard title="Insulin Status" caption="Current insulin record" value={textValue(medications.insulin_status)} tone={statusTone(medications.insulin_status)} />
                  <ReferenceMetricCard title="Active Prescriptions" caption="Total count" value={`${medications.active_medication_count ?? '—'} Medications`} tone="blue" />
                </article>

                <article>
                  <h3><IconGlyph name="activity" />Diagnosis Review</h3>
                  <ReferenceMetricCard title="Primary Code" caption="Admission diagnosis" value={textValue(diagnosis.primary_diagnosis)} tone={statusTone(diagnosis.primary_diagnosis)} />
                  <ReferenceMetricCard title="Secondary Code" caption="Comorbidities" value={textValue(diagnosis.secondary_diagnosis)} />
                  <ReferenceMetricCard title="Registered Diagnoses" caption="Total count" value={`${diagnosis.total_diagnoses_recorded ?? '—'} Registered`} tone="blue" />
                </article>
              </div>

              <div className="reference-timeline-panel">
                <h3><IconGlyph name="clock" />Diagnosis Timeline & Clinical Notes</h3>
                <DiagnosisTimelineCompact items={diagnosis.diagnosis_timeline} />
              </div>
            </section>
          </div>

          <aside className="reference-ai-panel" aria-label="AI Copilot reserved panel">
            <div className="reference-ai-panel__inner">
              <div className="reference-ai-header">
                <span><IconGlyph name="spark" /></span>
                <div>
                  <h2>Clinical AI Copilot</h2>
                  <p>Reserved workspace</p>
                </div>
              </div>
              <div className="reference-ai-placeholder">
                <strong>AI panel reserved</strong>
                <p>Future patient-specific reasoning, discharge drafting, and interactive AI tools will appear here.</p>
                <small>No AI recommendations are generated in this demo phase.</small>
              </div>
            </div>
          </aside>
        </div>
      ) : null}
    </main>
  );
}
