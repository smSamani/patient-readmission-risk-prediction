import { API_BASE_URL } from './config';

export type RiskCategory = 'High Risk' | 'Medium Risk' | 'Low Risk';
export type SortOrder = 'asc' | 'desc';

export interface PatientQueueItem {
  patient_id: string;
  encounter_id: number;
  model_row_id: number;
  patient_name: string;
  age: string;
  age_band: string | null;
  display_age: number | null;
  gender: string;
  gender_raw: string | null;
  primary_diagnosis_group: string | null;
  primary_diagnosis_group_raw: string | null;
  admission_source: string | null;
  admission_source_raw: string | null;
  discharge_destination: string | null;
  discharge_destination_raw: string | null;
  calibrated_risk_pct: number | null;
  risk_category: RiskCategory | string | null;
  risk_category_raw: string | null;
  view_digital_chart_url: string;
}

export interface PatientQueueResponse {
  items: PatientQueueItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface PatientQueueParams {
  risk_category?: string;
  gender?: string;
  primary_diagnosis_group?: string;
  admission_source?: string;
  discharge_destination?: string;
  search?: string;
  min_age?: number;
  max_age?: number;
  min_time_in_hospital?: number;
  max_time_in_hospital?: number;
  duplicate_first_name?: boolean;
  first_name?: string;
  race?: string;
  primary_physician?: string;
  ward_unit?: string;
  room_number?: string;
  has_lab_report?: boolean;
  lab_report_type?: string;
  lab_report_status?: string;
  lab_report_source_basis?: string;
  min_risk?: number;
  max_risk?: number;
  sort_by?: string;
  sort_order?: SortOrder;
  limit?: number;
  offset?: number;
}

export interface PatientChartResponse {
  patient_id: string;
  encounter_id: number;
  model_row_id: number;
  box_1_demographics_encounter: {
    patient_identity: {
      patient_name: string | null;
      mrn: string | null;
      primary_physician: string | null;
      ward_unit: string | null;
      room_number: string | null;
      risk_category: string | null;
      risk_category_raw?: string | null;
    };
    demographics: {
      age: number | string | null;
      display_age?: number | null;
      age_band?: string | null;
      age_numeric?: number | null;
      gender: string | null;
      gender_raw?: string | null;
      race: string | null;
      race_raw?: string | null;
    };
    encounter_context: {
      admission_type: string | null;
      admission_type_raw?: string | null;
      admission_source: string | null;
      admission_source_raw?: string | null;
      discharge_destination: string | null;
      discharge_destination_raw?: string | null;
      time_in_hospital: number | null;
      scheduled_discharge_date: string | null;
      scheduled_discharge_time: string | null;
      discharge_planner: string | null;
    };
  };
  box_2_clinical_snapshot: {
    prior_utilization: {
      prior_inpatient_visits: number | null;
      prior_emergency_visits: number | null;
      prior_outpatient_visits: number | null;
      total_prior_utilization: number | null;
      utilization_level: string | null;
    };
    current_admission_burden: {
      diagnoses_recorded: number | null;
      active_medications: number | null;
      lab_procedures: number | null;
      procedures: number | null;
      clinical_burden_level: string | null;
    };
    visualization_data: {
      utilization_chart: Array<{ label: string; value: number }>;
    };
  };
  box_3_clinical_review: {
    labs_glycemic_monitoring: {
      hba1c_result_status: string | null;
      hba1c_tested: number | null;
      max_glucose_result_status: string | null;
      max_glu_tested: number | null;
      lab_procedures_count: number | null;
      last_lab_review_timestamp: string | null;
      reviewed_by: string | null;
    };
    medication_review: {
      diabetes_medication_used: string | null;
      diabetes_medication_used_raw?: string | null;
      insulin_status: string | null;
      insulin_status_raw?: string | null;
      medication_change_during_stay: string | null;
      medication_change_during_stay_raw?: string | null;
      active_medication_count: number | null;
      key_diabetes_medications: string | string[] | null;
      medication_reconciliation_status: string | null;
      diabetes_education_status: string | null;
      reviewed_by_pharmacist: string | null;
    };
    diagnosis_review: {
      primary_diagnosis: string | null;
      primary_diagnosis_raw?: string | null;
      secondary_diagnosis: string | null;
      secondary_diagnosis_raw?: string | null;
      third_diagnosis: string | null;
      third_diagnosis_raw?: string | null;
      total_diagnoses_recorded: number | null;
      diagnosis_timeline: DiagnosisTimelineItem[];
      diagnosis_limitation_note: string | null;
    };
  };
  risk_prediction: {
    calibrated_risk_pct: number | null;
    predicted_probability_calibrated: number | null;
    risk_category: string | null;
    risk_category_raw?: string | null;
    predicted_class: number | null;
    actual_readmitted_30d: number | null;
  };
  shap_top3: ShapDriver[];
  interventions: Intervention[];
  synthetic_context?: Record<string, string | null>;
}

export interface DiagnosisTimelineItem {
  encounter_id?: number;
  model_row_id?: number;
  diagnosis_rank: number | null;
  diagnosis_label: string | null;
  diagnosis_group: string | null;
  diagnosis_owner?: string | null;
  diagnosed_by: string | null;
  department_specialty: string | null;
  date_recorded: string | null;
  clinical_note: string | null;
}

export interface ShapDriver {
  rank: number | null;
  feature: string;
  feature_label: string | null;
  feature_value: string | number | null;
  shap_value: number | null;
  effect_direction: string | null;
}

export interface Intervention {
  intervention_id?: string;
  intervention_type: string | null;
  intervention_status: string | null;
  status?: string | null;
  created_by: string | null;
  created_at: string | null;
  notes: string | null;
  source_type?: string | null;
  is_user_created?: boolean;
  is_editable?: boolean;
}

function appendParam(params: URLSearchParams, key: string, value: string | number | undefined) {
  if (value === undefined || value === '') return;
  params.set(key, String(value));
}

export async function fetchPatients(query: PatientQueueParams = {}): Promise<PatientQueueResponse> {
  const params = new URLSearchParams();
  appendParam(params, 'risk_category', query.risk_category);
  appendParam(params, 'gender', query.gender);
  appendParam(params, 'primary_diagnosis_group', query.primary_diagnosis_group);
  appendParam(params, 'admission_source', query.admission_source);
  appendParam(params, 'discharge_destination', query.discharge_destination);
  appendParam(params, 'search', query.search?.trim());
  appendParam(params, 'min_age', query.min_age);
  appendParam(params, 'max_age', query.max_age);
  appendParam(params, 'min_time_in_hospital', query.min_time_in_hospital);
  appendParam(params, 'max_time_in_hospital', query.max_time_in_hospital);
  appendParam(params, 'duplicate_first_name', query.duplicate_first_name ? 'true' : undefined);
  appendParam(params, 'first_name', query.first_name);
  appendParam(params, 'race', query.race);
  appendParam(params, 'primary_physician', query.primary_physician);
  appendParam(params, 'ward_unit', query.ward_unit);
  appendParam(params, 'room_number', query.room_number);
  appendParam(params, 'has_lab_report', query.has_lab_report === undefined ? undefined : String(query.has_lab_report));
  appendParam(params, 'lab_report_type', query.lab_report_type);
  appendParam(params, 'lab_report_status', query.lab_report_status);
  appendParam(params, 'lab_report_source_basis', query.lab_report_source_basis);
  appendParam(params, 'min_risk', query.min_risk);
  appendParam(params, 'max_risk', query.max_risk);
  appendParam(params, 'sort_by', query.sort_by);
  appendParam(params, 'sort_order', query.sort_order);
  appendParam(params, 'limit', query.limit);
  appendParam(params, 'offset', query.offset);

  const response = await fetch(`${API_BASE_URL}/api/patients?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Patient queue request failed with ${response.status}`);
  }
  return response.json();
}

export async function fetchPatientChart(patientId: string): Promise<PatientChartResponse> {
  const response = await fetch(`${API_BASE_URL}/api/patients/${encodeURIComponent(patientId)}`);
  if (!response.ok) {
    throw new Error(`Patient chart request failed with ${response.status}`);
  }
  return response.json();
}

export interface AiRouteResponse {
  route: 'queue' | 'chart';
  patient_id?: string;
  filters?: {
    risk_category?: string;
    gender?: string;
    primary_diagnosis_group?: string;
    admission_source?: string;
    discharge_destination?: string;
    min_age?: number;
    max_age?: number;
    min_time_in_hospital?: number;
    max_time_in_hospital?: number;
    duplicate_first_name?: boolean;
    first_name?: string;
    race?: string;
    primary_physician?: string;
    ward_unit?: string;
    room_number?: string;
    has_lab_report?: boolean;
    lab_report_type?: string;
    lab_report_status?: string;
    lab_report_source_basis?: string;
    min_risk?: number;
    max_risk?: number;
    search?: string;
  };
}

export async function routeNaturalLanguageQuery(prompt: string): Promise<AiRouteResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ai/route`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });
  if (!response.ok) {
    throw new Error(`AI routing request failed with ${response.status}`);
  }
  return response.json();
}

export interface CopilotPhase {
  phase_number: number;
  phase_name: string;
  status: 'concern' | 'review' | 'clear';
  evidence_used: string[];
  shap_context: string[];
  copilot_note: string;
}

export interface CopilotEvaluateResponse {
  patient_id: string;
  mode: string;
  model_context_note: string;
  overall_assessment: {
    risk_category: string;
    calibrated_risk_pct: number;
    summary: string;
  };
  phases: CopilotPhase[];
  key_review_items: string[];
  data_limitations: string[];
}

export async function evaluateDischargeReadiness(patientId: string): Promise<CopilotEvaluateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/patients/${encodeURIComponent(patientId)}/copilot/evaluate`);
  if (!response.ok) {
    throw new Error(`AI Copilot evaluation failed with status ${response.status}`);
  }
  return response.json();
}

export interface TechnicalEvidence {
  shap_context: string[];
  structured_fields_used: string[];
}

export interface CopilotChatResponse {
  patient_id: string;
  mode: string;
  intent: string;
  answer?: string;
  evidence_used?: string[];
  related_phases?: string[];
  shap_context?: string[];
  answer_markdown?: string;
  plain_language_summary?: string;
  evidence_summary?: string[];
  technical_evidence?: TechnicalEvidence;
  follow_up_questions?: string[];
  limitations?: string[];
  overall_assessment?: {
    risk_category: string;
    calibrated_risk_pct: number;
    summary: string;
  } | null;
  phases?: CopilotPhase[] | null;
}

export async function chatWithCopilot(patientId: string, message: string): Promise<CopilotChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/patients/${encodeURIComponent(patientId)}/copilot/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    throw new Error(`AI Copilot chat failed with status ${response.status}`);
  }
  return response.json();
}

export interface CopilotAskResponse {
  patient_id: string;
  mode: string;
  answer_markdown: string;
  follow_up_questions: string[];
  context_used: {
    structured_patient_data: boolean;
    risk_prediction: boolean;
    shap_summary: boolean;
    clinical_reviews: boolean;
    diagnosis_timeline: boolean;
    lab_reports: boolean;
  };
  safety_note: string;
}

export async function askGeminiCopilot(
  patientId: string,
  message: string,
  conversationHistory: Array<{ role: string; content: string }> = []
): Promise<CopilotAskResponse> {
  const response = await fetch(`${API_BASE_URL}/api/patients/${encodeURIComponent(patientId)}/copilot/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_history: conversationHistory }),
  });
  if (!response.ok) {
    throw new Error(`AI Copilot ask failed with status ${response.status}`);
  }
  return response.json();
}
