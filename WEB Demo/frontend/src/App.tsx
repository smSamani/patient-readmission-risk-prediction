import { Navigate, Route, Routes } from 'react-router-dom';
import { ClinicalPortalPage } from './pages/ClinicalPortalPage';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ClinicalPortalPage view="home" />} />
      <Route path="/queue" element={<ClinicalPortalPage view="queue" />} />
      <Route path="/patients/:patientId" element={<ClinicalPortalPage view="chart" />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
