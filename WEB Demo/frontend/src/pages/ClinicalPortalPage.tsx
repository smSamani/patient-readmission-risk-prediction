import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal, flushSync } from 'react-dom';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { fetchPatientChart, fetchPatients, routeNaturalLanguageQuery, evaluateDischargeReadiness, chatWithCopilot, askGeminiCopilot, type PatientChartResponse, type PatientQueueItem, type CopilotEvaluateResponse, type CopilotChatResponse, type CopilotAskResponse } from '../api/patientsApi';
import { displayAge, formatDisplayLabel } from '../utils/formatters';

type PortalView = 'home' | 'queue' | 'chart';

function isDischargeReadinessPrompt(text: string) {
  const normalized = text.toLowerCase().replace(/\s+/g, ' ').trim();
  const directPhrases = [
    'evaluate discharge',
    'discharge readiness',
    'is this patient ready for discharge',
    'review discharge plan',
    'ready for discharge',
    'discharge ready',
    'amade discharge',
    'amade dischurge',
    'amadeye discharge',
    'amadeye dischurge',
    'evaluate discharge readiness',
    'ارزیابی ترخیص',
    'آماده ترخیص',
  ];
  const dischargeTerms = ['discharge', 'dischurge', 'discharg', 'tarkhis', 'tarkhish', 'tarkhise', 'tarkhishe', 'ترخیص'];
  const evaluationTerms = ['evaluate', 'evaluation', 'readiness', 'ready', 'review', 'check', 'assess', 'assessment', 'amade', 'amadeye', 'amadeh', 'bebin', 'hast', 'arzyabi', 'arzyaby', 'arz yabi', 'arzyaabi', 'arziabi', 'ارزیابی', 'بررسی', 'آماده'];
  const possibilityTerms = ['can we', 'can this', 'can the', 'could we', 'mitoonim', 'mitunim', 'mitonim', 'mitoonam', 'mishe', 'mishavad', 'mishavad', 'میتونیم', 'می‌تونیم', 'می توانیم', 'میشه', 'آیا'];

  return directPhrases.some((phrase) => normalized.includes(phrase)) ||
    (dischargeTerms.some((term) => normalized.includes(term)) &&
      (evaluationTerms.some((term) => normalized.includes(term)) || possibilityTerms.some((term) => normalized.includes(term))));
}

function useSwipeNavigate() {
  const navigate = useNavigate();
  const location = useLocation();

  return (to: string) => {
    if (to === location.pathname) return;
    navigate(to);
  };
}

function SvgIcon({ name }: { name: 'home' | 'list' | 'folder' | 'arrow' | 'search' | 'shield' | 'users' | 'chevron' | 'mic' | 'send' | 'copy' | 'dots' }) {
  const common = { viewBox: '0 0 24 24', fill: 'none', xmlns: 'http://www.w3.org/2000/svg', 'aria-hidden': true };
  const stroke = { stroke: 'currentColor', strokeWidth: 2.3, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  if (name === 'home') return <svg {...common}><path fill="currentColor" d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z" /></svg>;
  if (name === 'list') return <svg {...common}><path {...stroke} d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.01M3.75 12h.01M3.75 17.25h.01" /></svg>;
  if (name === 'folder') return <svg {...common}><path {...stroke} d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-6l-2-2H5a2 2 0 0 0-2 2Z" /></svg>;
  if (name === 'arrow') return <svg {...common}><path {...stroke} d="M4.5 12h15m0 0-6.75-6.75M19.5 12l-6.75 6.75" /></svg>;
  if (name === 'search') return <svg {...common}><path {...stroke} d="m21 21-5.2-5.2" /><circle {...stroke} cx="10.5" cy="10.5" r="7.5" /></svg>;
  if (name === 'shield') return <svg {...common}><path {...stroke} d="M9 12l2 2 4-4" /><path {...stroke} d="M20.6 6A12 12 0 0 1 12 3 12 12 0 0 1 3.4 6 12 12 0 0 0 3 9c0 5.6 3.8 10.3 9 11.6 5.2-1.3 9-6 9-11.6 0-1-.1-2-.4-3Z" /></svg>;
  if (name === 'users') return <svg {...common}><path {...stroke} d="M17 20h5v-2a3 3 0 0 0-5.4-1.9M17 20H7m10 0v-2c0-.7-.1-1.3-.4-1.9M7 20H2v-2a3 3 0 0 1 5.4-1.9M15 7a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM7 10a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z" /></svg>;
  if (name === 'chevron') return <svg {...common}><path {...stroke} d="m19.5 8.25-7.5 7.5-7.5-7.5" /></svg>;
  if (name === 'mic') return <svg {...common}><path {...stroke} d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" /></svg>;
  if (name === 'send') return <svg {...common}><line {...stroke} x1="12" y1="19" x2="12" y2="5" /><polyline {...stroke} points="5 12 12 5 19 12" /></svg>;
  if (name === 'copy') return <svg {...common}><path {...stroke} d="M8 7v8a2 2 0 0 0 2 2h6M8 7V5a2 2 0 0 1 2-2h4.6L20 8.4V15a2 2 0 0 1-2 2h-2M8 7H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-2" /></svg>;
  return <svg {...common}><path {...stroke} d="M12 5h.01M12 12h.01M12 19h.01" /></svg>;
}

function AntigravityCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrame = 0;
    let particles: Array<{ x: number; y: number; baseX: number; baseY: number; size: number; color: string; density: number }> = [];
    const mouse = { x: null as number | null, y: null as number | null, targetX: null as number | null, targetY: null as number | null, isPresent: false };
    let activeFade = 0;
    let time = 0;
    const palette = ['#027980', '#039DA6', '#015459', '#80CBC4', '#B2DFDB'];

    const generateSparseGrid = () => {
      particles = [];
      for (let y = 0; y < canvas.height + 36; y += 36) {
        for (let x = 0; x < canvas.width + 36; x += 36) {
          particles.push({
            x: x + (Math.random() - 0.5) * 8,
            y: y + (Math.random() - 0.5) * 8,
            baseX: x,
            baseY: y,
            size: Math.random() * 1.1 + 0.6,
            color: palette[Math.floor(Math.random() * palette.length)],
            density: Math.random() * 20 + 10,
          });
        }
      }
    };

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      generateSparseGrid();
    };

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      time += 0.035;
      if (mouse.isPresent && mouse.targetX !== null && mouse.targetY !== null) {
        mouse.x = mouse.x === null ? mouse.targetX : mouse.x + (mouse.targetX - mouse.x) * 0.08;
        mouse.y = mouse.y === null ? mouse.targetY : mouse.y + (mouse.targetY - mouse.y) * 0.08;
        activeFade += (1 - activeFade) * 0.1;
      } else {
        activeFade += (0 - activeFade) * 0.05;
        if (activeFade < 0.001) {
          activeFade = 0;
          mouse.x = null;
          mouse.y = null;
        }
      }

      for (const particle of particles) {
        if (mouse.x !== null && mouse.y !== null) {
          const dx = mouse.x - particle.x;
          const dy = mouse.y - particle.y;
          const distance = Math.sqrt(dx * dx + dy * dy) || 1;
          if (distance < 130) {
            const force = (130 - distance) / 130;
            particle.x -= (dx / distance) * force * particle.density;
            particle.y -= (dy / distance) * force * particle.density;
          } else {
            particle.x -= (particle.x - particle.baseX) * 0.08;
            particle.y -= (particle.y - particle.baseY) * 0.08;
          }

          if (activeFade > 0) {
            const distToMouse = Math.sqrt((mouse.x - particle.x) ** 2 + (mouse.y - particle.y) ** 2);
            const waveIntensity = Math.pow((Math.sin(distToMouse * 0.075 - time * 1.6) + 1) / 2, 5);
            const falloff = Math.max(0, 1 - distToMouse / 240);
            ctx.beginPath();
            ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
            ctx.fillStyle = particle.color;
            ctx.globalAlpha = waveIntensity * falloff * 0.65 * activeFade;
            ctx.fill();
            ctx.globalAlpha = 1;
          }
        } else {
          particle.x -= (particle.x - particle.baseX) * 0.08;
          particle.y -= (particle.y - particle.baseY) * 0.08;
        }
      }
      animationFrame = requestAnimationFrame(animate);
    };

    const move = (event: MouseEvent) => {
      mouse.targetX = event.clientX;
      mouse.targetY = event.clientY;
      mouse.isPresent = true;
    };
    const leave = () => { mouse.isPresent = false; };
    resize();
    animate();
    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseleave', leave);
    return () => {
      cancelAnimationFrame(animationFrame);
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseleave', leave);
    };
  }, []);

  return <canvas ref={canvasRef} className="samani-canvas" />;
}

function PortalNav({ view, activePatientId }: { view: PortalView; activePatientId?: string }) {
  const swipeNavigate = useSwipeNavigate();
  const chartVisible = view === 'chart' || Boolean(activePatientId);
  return (
    <nav className={`samani-top-nav samani-top-nav--${view} ${chartVisible ? 'samani-top-nav--expanded' : ''}`} aria-label="Portal navigation">
      <button title="Home Console" type="button" onClick={() => swipeNavigate('/')} className={view === 'home' ? 'is-active' : ''}><SvgIcon name="home" /></button>
      <button title="Clinical Patients List" type="button" onClick={() => swipeNavigate('/queue')} className={view === 'queue' ? 'is-active' : ''}><SvgIcon name="list" /></button>
      <button title="Active Patient Chart" type="button" onClick={() => activePatientId ? swipeNavigate(`/patients/${activePatientId}`) : undefined} className={`samani-chart-tab ${view === 'chart' ? 'is-active' : ''} ${chartVisible ? 'is-visible' : ''}`}><SvgIcon name="folder" /></button>
    </nav>
  );
}

function PortalHeader() {
  return (
    <header className="samani-header">
      <Link className="samani-portal-brand" to="/queue">
        <span className="samani-header-icon"><SvgIcon name="folder" /></span>
        <span>
          <b>Patient Discharge Portal</b>
          <small>Clinical operations system</small>
        </span>
      </Link>
      <span className="samani-workspace-pill">
        <span className="samani-user-avatar">DS</span>
        <span>
          <b>Dr Samani</b>
          <small>Clinical Workspace</small>
        </span>
      </span>
    </header>
  );
}

interface AIInsightData {
  title: string;
  text: string;
  signals: string[];
  likelihood: string;
  abscess: string;
  confidence: string;
}

interface LabReportManifestEntry {
  patient_id: string;
  encounter_id: string;
  report_type: string;
  structured_category: string;
  simulated_numeric_result: string;
  unit: string;
  status_label: string;
  json_path: string;
  md_path: string;
}

interface LabReportData {
  metadata: {
    patient_name: string;
    synthetic_mrn: string;
    patient_id: string;
    encounter_id: number | string;
    age_display: number | string;
    gender: string;
    primary_physician: string;
    reviewed_by: string;
    collection_datetime: string;
    reported_datetime: string;
    report_type?: string;
    report_id?: string;
  };
  result: {
    test_name: string;
    investigation: string;
    simulated_numeric_result: number | string;
    unit: string;
    structured_category: string;
    reference_range_text: string;
    status_label: string;
  };
  interpretation: string;
  limitation: string;
}

const APP_BASE_PATH = import.meta.env.BASE_URL === '/'
  ? ''
  : import.meta.env.BASE_URL.replace(/\/$/, '');
const LAB_REPORT_BASE = `${APP_BASE_PATH}/lab_reports`;
const LAB_REPORT_SAFETY_NOTE = 'Portfolio simulation note: This lab report is generated from structured categorical lab data in the public source dataset. The numeric value is simulated within the recorded category for demonstration and is not an original laboratory value.';

const MOCK_AI_INSIGHTS: Record<string, AIInsightData> = {
  "DEMO-001": {
    title: "Early Infection Possibility",
    text: "AI analysis indicates a potential early-stage urinary tract infection affecting recovery speed, based on localized urinary leukocytes and increasing body temperature.",
    signals: [
      "Urinary leukocytes trending upward",
      "Mild temperature spike (38.1°C)",
      "Increased patient-reported fatigue"
    ],
    likelihood: "Moderate",
    abscess: "Possible if untreated",
    confidence: "74%"
  },
  "DEMO-002": {
    title: "Hypoglycemia Risk Alert",
    text: "AI models suggest a high risk of nocturnal hypoglycemia over the next 24 hours based on rapid descent of insulin infusion rates and low carbohydrate intake during dinner.",
    signals: [
      "Subcutaneous insulin overlap",
      "Decreased carbohydrate consumption",
      "Historical nocturnal drops"
    ],
    likelihood: "High",
    abscess: "Severe if unmitigated",
    confidence: "82%"
  },
  "DEMO-003": {
    title: "Atrial Fibrillation Susceptibility",
    text: "Heart rate variability indexes indicate high risk of post-operative atrial fibrillation onset within 12 hours.",
    signals: [
      "Ectopic heartbeats noted during sleep",
      "Decreased HRV score",
      "Slight fluid accumulation markers"
    ],
    likelihood: "Elevated",
    abscess: "Possible fluid retention",
    confidence: "71%"
  }
};

const DEFAULT_AI_INSIGHT: AIInsightData = {
  title: "Stable Recovery Context",
  text: "Patient indicators are returning to baseline smoothly with low indicators of system readmission stress.",
  signals: [
    "Normalization of core body temperature",
    "No localized infection signs detected",
    "Vital parameters within normal bounds"
  ],
  likelihood: "Low",
  abscess: "Negligible",
  confidence: "90%"
};

function HomeConsole({ 
  active, 
  onSubmit, 
  loading 
}: { 
  active: boolean; 
  onSubmit: (prompt: string) => void; 
  loading: boolean; 
}) {
  const [prompt, setPrompt] = useState('');
  const [interimText, setInterimText] = useState('');  // live interim transcript
  const [isListening, setIsListening] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const [inputHeight, setInputHeight] = useState(56);
  const [showIntro, setShowIntro] = useState(() => {
    if (typeof window === 'undefined') return true;
    return window.localStorage.getItem('samani-patient-demo-intro-seen') !== 'true';
  });
  const [introClosing, setIntroClosing] = useState(false);
  const navigate = useNavigate();
  const recognitionRef = useRef<any>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const promptRef = useRef('');
  const interimRef = useRef('');
  const audioContextRef = useRef<AudioContext | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const analyserFrameRef = useRef<number | null>(null);

  const setPromptValue = (value: string) => {
    promptRef.current = value;
    setPrompt(value);
  };

  const setInterimValue = (value: string) => {
    interimRef.current = value;
    setInterimText(value);
  };

  const commitInterimTranscript = () => {
    const interim = interimRef.current.trim();
    if (!interim) return;
    const nextPrompt = promptRef.current
      ? `${promptRef.current.trimEnd()} ${interim}`.trim()
      : interim;
    setPromptValue(nextPrompt);
    setInterimValue('');
  };

  const stopMicLevelMonitor = () => {
    if (analyserFrameRef.current !== null) {
      cancelAnimationFrame(analyserFrameRef.current);
      analyserFrameRef.current = null;
    }
    micStreamRef.current?.getTracks().forEach((track) => track.stop());
    micStreamRef.current = null;
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      void audioContextRef.current.close();
    }
    audioContextRef.current = null;
    setMicLevel(0);
  };

  const startMicLevelMonitor = async () => {
    if (!navigator.mediaDevices?.getUserMedia) return;
    stopMicLevelMonitor();
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    const audioContext = new AudioContextClass();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 512;
    analyser.smoothingTimeConstant = 0.72;
    source.connect(analyser);
    const data = new Uint8Array(analyser.fftSize);

    micStreamRef.current = stream;
    audioContextRef.current = audioContext;

    const tick = () => {
      analyser.getByteTimeDomainData(data);
      let sumSquares = 0;
      for (let i = 0; i < data.length; i += 1) {
        const centered = (data[i] - 128) / 128;
        sumSquares += centered * centered;
      }
      const rms = Math.sqrt(sumSquares / data.length);
      const level = Math.min(1, Math.max(0, rms * 8));
      setMicLevel(level);
      analyserFrameRef.current = requestAnimationFrame(tick);
    };
    tick();
  };

  const startListening = async () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser. Please try Chrome or Safari.");
      return;
    }
    const rec = new SpeechRecognition();
    rec.continuous = true;          // keep listening until user stops
    rec.interimResults = true;      // stream partial results live
    rec.lang = navigator.language || 'en-US';
    
    rec.onstart = () => {
      setIsListening(true);
      setInterimValue('');
    };
    
    rec.onresult = (e: any) => {
      let finalPart = '';
      let interimPart = '';

      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) {
          finalPart += t;
        } else {
          interimPart += t;
        }
      }

      if (finalPart) {
        const nextPrompt = promptRef.current
          ? `${promptRef.current.trimEnd()} ${finalPart.trim()}`.trim()
          : finalPart.trim();
        setPromptValue(nextPrompt);
        setInterimValue('');
      } else {
        setInterimValue(interimPart.trim());
      }
    };
    
    rec.onerror = (e: any) => {
      console.error("Speech recognition error", e);
      commitInterimTranscript();
      setIsListening(false);
      stopMicLevelMonitor();
    };
    
    rec.onend = () => {
      commitInterimTranscript();
      setIsListening(false);
      stopMicLevelMonitor();
    };
    
    recognitionRef.current = rec;
    try {
      await startMicLevelMonitor();
    } catch (error) {
      console.warn('Microphone level monitor unavailable', error);
    }
    try {
      rec.start();
    } catch (error) {
      stopMicLevelMonitor();
      throw error;
    }
  };

  const stopListening = () => {
    commitInterimTranscript();
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    stopMicLevelMonitor();
    setIsListening(false);
  };

  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      void startListening().catch((error) => {
        console.error('Unable to start speech capture', error);
        setIsListening(false);
        stopMicLevelMonitor();
      });
    }
  };

  const handleSend = () => {
    const finalPrompt = (promptRef.current + (interimRef.current ? ' ' + interimRef.current : '')).trim();
    if (finalPrompt && !loading) {
      if (isListening) stopListening();
      setPromptValue(finalPrompt);
      setInterimValue('');
      onSubmit(finalPrompt);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChipClick = (text: string) => {
    closeIntroWithAnimation();
    setPromptValue(text);
    onSubmit(text);
  };

  const dismissIntro = () => {
    setShowIntro(false);
    setIntroClosing(false);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('samani-patient-demo-intro-seen', 'true');
    }
  };

  const closeIntroWithAnimation = () => {
    if (introClosing) return;
    setIntroClosing(true);
    window.setTimeout(dismissIntro, 220);
  };

  const startFromQueue = () => {
    closeIntroWithAnimation();
    window.setTimeout(() => navigate('/queue'), 220);
  };

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop?.();
      stopMicLevelMonitor();
    };
  }, []);

  const displayedPrompt = isListening && interimText
    ? prompt + (prompt ? ' ' : '') + interimText
    : prompt;
  const hasText = Boolean(prompt.trim() || interimText.trim());
  const isSpeaking = micLevel > 0.055;
  const waveformHeights = [
    7 + micLevel * 9,
    16 - micLevel * 7,
    12 + micLevel * 10,
    16 - micLevel * 7,
    7 + micLevel * 9,
  ];

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const availableWidth = Math.max(180, textarea.clientWidth - 96);
    const charsPerLine = Math.max(24, Math.floor(availableWidth / 7.6));
    const visualLines = displayedPrompt
      .split('\n')
      .reduce((total, line) => total + Math.max(1, Math.ceil(line.length / charsPerLine)), 0);
    const nextHeight = Math.min(112, Math.max(24, visualLines * 24));
    textarea.style.height = `${nextHeight}px`;
    setInputHeight(nextHeight + 16);
  }, [displayedPrompt, active]);

  return (
    <main className={`samani-chat-view ${active ? 'is-active' : 'is-inactive'}`}>
      {showIntro && createPortal(
        <div className={`samani-demo-intro-backdrop ${introClosing ? 'is-closing' : ''}`} role="presentation" onMouseDown={closeIntroWithAnimation}>
          <section
            className={`samani-demo-intro ${introClosing ? 'is-closing' : ''}`}
            aria-label="Platform introduction"
            role="dialog"
            aria-modal="true"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="samani-demo-intro__halo" aria-hidden="true" />
            <div className="samani-demo-intro__header">
              <span className="samani-demo-intro__eyebrow">Clinical AI demo guide</span>
              <button type="button" onClick={closeIntroWithAnimation} aria-label="Close introduction">×</button>
            </div>
            <div className="samani-demo-intro__body">
              <div>
                <h2>Before you explore the discharge workspace</h2>
                <p>
                  This platform is built on the public <b>Diabetes 130-US hospitals dataset
                  for years 1999-2008</b>, derived from real patient encounters. A machine
                  learning model uses the structured case data to estimate each patient&apos;s
                  probability of readmission within 30 days.
                </p>
                <p>
                  To make the real-world use of the system easier to feel inside the interface,
                  selected contextual details such as patient names are synthetically generated
                  with GenAI, while the clinical structure remains grounded in the source dataset.
                </p>
              </div>
              <div className="samani-demo-intro__grid">
                <article>
                  <span>ML</span>
                  <b>Readmission risk prediction</b>
                  <p>Each patient case is ranked by calibrated 30-day readmission risk.</p>
                </article>
                <article>
                  <span>XAI</span>
                  <b>SHAP model evidence</b>
                  <p>Feature-level SHAP values explain which signals pushed risk higher or lower.</p>
                </article>
                <article>
                  <span>RAG</span>
                  <b>Evidence-aware copilot</b>
                  <p>The AI Copilot combines chart facts, retrieved evidence, and model signals.</p>
                </article>
                <article>
                  <span>AI</span>
                  <b>Agentic query routing</b>
                  <p>Natural-language prompts can route to the patient list or the right digital case.</p>
                </article>
              </div>
              <div className="samani-demo-intro__testing">
                <b>Recommended ways to test</b>
                <ol>
                  <li>Use the recommended prompts on the home screen.</li>
                  <li>Start from the patient list, review a few cases, then ask follow-up prompts.</li>
                  <li>Use a desktop browser for the intended layout and interaction quality.</li>
                </ol>
              </div>
            </div>
            <div className="samani-demo-intro__actions">
              <button type="button" className="samani-demo-intro__primary" onClick={closeIntroWithAnimation}>
                Start with prompts
              </button>
              <button type="button" className="samani-demo-intro__secondary" onClick={startFromQueue}>
                Open patient list
              </button>
            </div>
          </section>
        </div>,
        document.body
      )}
      <h1>Hi <span>Dr Samani</span>, How can I help?</h1>

      {/* Glow ring: outer div that holds the animated blur glow via ::before/::after */}
      <div className={[
        'samani-glow-ring',
        loading     ? 'is-loading'   : '',
        isListening ? 'is-listening' : '',
      ].filter(Boolean).join(' ')}>
        <div
          className={`samani-chat-input-wrap ${inputHeight > 56 ? 'is-expanded' : ''}`}
          style={{ height: `${inputHeight}px` }}
        >
          <textarea
            ref={textareaRef}
            value={displayedPrompt}
            disabled={loading}
            className={isListening && interimText ? 'has-interim' : ''}
            onChange={(event) => {
              if (!isListening) setPromptValue(event.target.value);
            }}
            onKeyDown={handleKeyDown}
            placeholder={
              loading     ? 'Routing AI intent…'    :
              isListening ? 'Listening… speak now'  :
                            'Ask about patients'
            }
            rows={1}
          />
          <button 
            type="button"
            className={`samani-mic-btn ${hasText ? 'has-text' : ''} ${isListening ? 'is-listening' : ''} ${isSpeaking ? 'is-speaking' : 'is-silent'}`} 
            title={isListening ? 'Stop recording' : 'Dictate medical query'}
            onClick={toggleListening}
            disabled={loading}
            style={{
              '--mic-level': micLevel,
            } as any}
          >
            <SvgIcon name="mic" />
            <span className="samani-mic-waveform" aria-hidden="true">
              {waveformHeights.map((height, index) => (
                <span key={index} style={{ '--bar-height': `${height}px` } as any} />
              ))}
            </span>
          </button>
          <button 
            type="button"
            className={`samani-send-btn ${hasText ? 'has-text' : ''}`} 
            title="Send to Dr Samani AI" 
            onClick={handleSend}
            disabled={loading || !hasText}
          >
            <SvgIcon name="send" />
          </button>
        </div>
      </div>
      {loading && (
        <div className="samani-home-processing" role="status" aria-live="polite">
          <span />
          Processing clinical query
        </div>
      )}
      <div className="samani-prompt-chips">
        <button 
          type="button" 
          disabled={loading}
          onClick={() => handleChipClick("Review whether Olivia Patel is ready for discharge")}
        >
          Review whether Olivia Patel is ready for discharge
        </button>
        <button 
          type="button" 
          disabled={loading}
          onClick={() => handleChipClick("Show Dr Carter patient aged 30-50 who came from the ER")}
        >
          Show Dr Carter patient aged 30-50 who came from the ER
        </button>
        <button
          type="button"
          disabled={loading}
          onClick={() => handleChipClick("What was the comment on Samuel Scott's lab results?")}
        >
          What was the comment on Samuel Scott's lab results?
        </button>
      </div>
    </main>
  );
}

function riskTone(category: string | null | undefined) {
  const text = String(category ?? '').toLowerCase();
  if (text.includes('high')) return 'high';
  if (text.includes('medium')) return 'medium';
  if (text.includes('low')) return 'low';
  return 'neutral';
}

function riskPercent(value: number | null) {
  return typeof value === 'number' ? `${value.toFixed(2)}%` : '--';
}

function CustomSelect({ label, value, icon, options, onChange }: { label: string; value: string; icon?: React.ReactNode; options: Array<{ label: string; value: string; icon?: React.ReactNode }>; onChange: (value: string) => void }) {
  const [open, setOpen] = useState(false);
  const active = options.find((option) => option.value === value) ?? options[0];
  return (
    <div className="samani-filter-select">
      <label>{label}</label>
      <button type="button" onClick={() => setOpen((current) => !current)}>
        <span>{active.icon ?? icon}{active.label}</span>
        <SvgIcon name="chevron" />
      </button>
      <div className={`samani-dropdown ${open ? 'show' : ''}`}>
        {options.map((option) => (
          <button key={option.value} type="button" onClick={() => { onChange(option.value); setOpen(false); }}>
            {option.icon}{option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function PatientListDashboard({ 
  active, 
  patients, 
  loading, 
  error,
  search,
  setSearch,
  risk,
  setRisk,
  gender,
  setGender,
  diagnosis,
  setDiagnosis,
  aiMode,
  setAiMode,
  aiFilters,
  setAiFilters,
  onAiSubmit,
  aiLoading
}: { 
  active: boolean; 
  patients: PatientQueueItem[]; 
  loading: boolean; 
  error: string | null;
  search: string;
  setSearch: (s: string) => void;
  risk: string;
  setRisk: (r: string) => void;
  gender: string;
  setGender: (g: string) => void;
  diagnosis: string;
  setDiagnosis: (d: string) => void;
  aiMode: boolean;
  setAiMode: (updater: boolean | ((current: boolean) => boolean)) => void;
  aiFilters: any;
  setAiFilters: (f: any) => void;
  onAiSubmit: (prompt: string) => void;
  aiLoading: boolean;
}) {
  const swipeNavigate = useSwipeNavigate();
  const [queryLabelProcessing, setQueryLabelProcessing] = useState(false);

  const diagnosisOptions = useMemo(() => {
    const values = new Map<string, string>();
    patients.forEach((patient) => {
      const raw = patient.primary_diagnosis_group_raw ?? patient.primary_diagnosis_group;
      if (raw) values.set(raw, formatDisplayLabel(patient.primary_diagnosis_group) ?? raw);
    });
    return [{ value: 'all', label: '✓ All diagnosis groups' }, ...Array.from(values, ([value, label]) => ({ value, label }))];
  }, [patients]);

  const filteredPatients = useMemo(() => {
    const query = search.trim().toLowerCase();
    return patients.filter((patient) => {
      const nameMatch = patient.patient_name.toLowerCase().includes(query) || patient.patient_id.toLowerCase().includes(query);
      const riskMatch = risk === 'all' || patient.risk_category_raw === risk || patient.risk_category === risk;
      const genderMatch = gender === 'all' || patient.gender_raw === gender || patient.gender === gender;
      const diagnosisMatch = diagnosis === 'all' || patient.primary_diagnosis_group_raw === diagnosis || patient.primary_diagnosis_group === diagnosis;
      if (aiMode && query) return riskMatch && genderMatch && diagnosisMatch;
      return nameMatch && riskMatch && genderMatch && diagnosisMatch;
    });
  }, [aiMode, diagnosis, gender, patients, risk, search]);

  const [sortKey, setSortKey] = useState<'patient_name' | 'display_age' | 'calibrated_risk_pct' | 'risk_category'>('calibrated_risk_pct');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const sortedPatients = useMemo(() => {
    const sorted = [...filteredPatients];
    sorted.sort((a, b) => {
      let valA: any = a[sortKey];
      let valB: any = b[sortKey];

      if (sortKey === 'display_age') {
        valA = a.display_age ?? (parseInt(a.age) || 0);
        valB = b.display_age ?? (parseInt(b.age) || 0);
      }

      // Handle nulls/undefined safely (put them at the end of sorting)
      if (valA === null || valA === undefined) return 1;
      if (valB === null || valB === undefined) return -1;

      if (sortKey === 'risk_category') {
        const severity = (cat: string | null) => {
          if (!cat) return 0;
          const lower = cat.toLowerCase();
          if (lower.includes('high')) return 3;
          if (lower.includes('med')) return 2;
          if (lower.includes('low')) return 1;
          return 0;
        };
        valA = severity(valA);
        valB = severity(valB);
      }

      if (typeof valA === 'string' && typeof valB === 'string') {
        return sortOrder === 'asc'
          ? valA.localeCompare(valB)
          : valB.localeCompare(valA);
      }

      if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
      if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [filteredPatients, sortKey, sortOrder]);

  const handleSort = (key: 'patient_name' | 'display_age' | 'calibrated_risk_pct' | 'risk_category') => {
    if (sortKey === key) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortOrder(key === 'patient_name' ? 'asc' : 'desc');
    }
  };

  const handleRemoveAiFilter = (key: string) => {
    if (key === 'risk_category') setRisk('all');
    if (key === 'gender') setGender('all');
    if (key === 'primary_diagnosis_group') setDiagnosis('all');
    setAiFilters((prev: any) => {
      if (!prev) return null;
      const copy = { ...prev };
      delete copy[key];
      return Object.keys(copy).length > 0 ? copy : null;
    });
  };

  const submitAiQuery = () => {
    const prompt = search.trim();
    if (!aiMode || !prompt || aiLoading) return;
    setQueryLabelProcessing(true);
    onAiSubmit(prompt);
  };

  useEffect(() => {
    if (aiLoading) {
      setQueryLabelProcessing(true);
      return;
    }
    if (!queryLabelProcessing) return;
    const timeout = window.setTimeout(() => setQueryLabelProcessing(false), 650);
    return () => window.clearTimeout(timeout);
  }, [aiLoading, queryLabelProcessing]);

  return (
    <main className={`samani-list-view ${active ? 'is-active' : 'is-inactive'} animate-domino`}>
      <div className="samani-list-head">
        <div>
          <span />
          <h2>Clinical Patients Dashboard</h2>
        </div>
        <strong>Active Monitoring • {filteredPatients.length} Patients</strong>
      </div>

      <div className="samani-filter-bar">
        <label className="samani-live-search">
          <div>
            <span className={`samani-search-label ${aiMode && queryLabelProcessing ? 'is-processing' : ''}`} aria-live="polite">
              <b>{aiMode && queryLabelProcessing ? 'Processing your Query' : 'Search'}</b>
            </span>
            <button type="button" className="samani-ai-toggle" onClick={() => setAiMode((current) => !current)}>
              <span className={aiMode ? 'is-active' : ''}>AI Query Mode</span>
              <i className={aiMode ? 'is-active' : ''}><b /></i>
            </button>
          </div>
          <div className={`samani-search-box ${aiMode ? 'is-ai' : ''} ${aiLoading ? 'is-processing' : ''}`}>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              onKeyDown={(event) => {
                if (aiMode && event.key === 'Enter') {
                  event.preventDefault();
                  submitAiQuery();
                }
              }}
              disabled={aiLoading}
              placeholder={aiMode ? "Ask AI, e.g. 'Has Chris Baker had an A1c test?'" : 'Name, patient ID, or encounter'}
            />
            {aiMode ? (
              <button
                type="button"
                className="samani-search-submit"
                onClick={submitAiQuery}
                disabled={aiLoading || !search.trim()}
                aria-label="Submit AI query"
              >
                <SvgIcon name="search" />
              </button>
            ) : (
              <SvgIcon name="search" />
            )}
          </div>
        </label>
        <CustomSelect label="Risk Category" value={risk} icon={<SvgIcon name="shield" />} onChange={setRisk} options={[
          { value: 'all', label: 'All risks', icon: <SvgIcon name="shield" /> },
          { value: 'High Risk', label: 'High Risk' },
          { value: 'Medium Risk', label: 'Medium Risk' },
          { value: 'Low Risk', label: 'Low Risk' },
        ]} />
        <CustomSelect label="Gender" value={gender} icon={<SvgIcon name="users" />} onChange={setGender} options={[
          { value: 'all', label: 'All genders', icon: <SvgIcon name="users" /> },
          { value: 'Male', label: 'Male' },
          { value: 'Female', label: 'Female' },
        ]} />
        <CustomSelect label="Diagnosis Group" value={diagnosis} onChange={setDiagnosis} options={diagnosisOptions} />
        <button className="samani-clear-btn" type="button" onClick={() => { setSearch(''); setRisk('all'); setGender('all'); setDiagnosis('all'); setAiFilters(null); setAiMode(false); }}>Clear</button>
      </div>

      {aiFilters && (
        <div className="samani-ai-pills">
          <span style={{ fontSize: '11px', color: '#6b7280', display: 'flex', alignItems: 'center', fontWeight: 'bold', marginRight: '4px' }}>
            ✦ AI Filters Active:
          </span>
          {aiFilters.min_age !== undefined && (
            <span className="samani-ai-pill">
              Age ≥ {aiFilters.min_age}
              <button type="button" onClick={() => handleRemoveAiFilter('min_age')}>×</button>
            </span>
          )}
          {aiFilters.max_age !== undefined && (
            <span className="samani-ai-pill">
              Age ≤ {aiFilters.max_age}
              <button type="button" onClick={() => handleRemoveAiFilter('max_age')}>×</button>
            </span>
          )}
          {aiFilters.min_time_in_hospital !== undefined && (
            <span className="samani-ai-pill">
              Stay ≥ {aiFilters.min_time_in_hospital} days
              <button type="button" onClick={() => handleRemoveAiFilter('min_time_in_hospital')}>×</button>
            </span>
          )}
          {aiFilters.max_time_in_hospital !== undefined && (
            <span className="samani-ai-pill">
              Stay ≤ {aiFilters.max_time_in_hospital} days
              <button type="button" onClick={() => handleRemoveAiFilter('max_time_in_hospital')}>×</button>
            </span>
          )}
          {aiFilters.duplicate_first_name && (
            <span className="samani-ai-pill">
              Repeated first names
              <button type="button" onClick={() => handleRemoveAiFilter('duplicate_first_name')}>×</button>
            </span>
          )}
          {aiFilters.first_name && (
            <span className="samani-ai-pill">
              First name: {aiFilters.first_name}
              <button type="button" onClick={() => handleRemoveAiFilter('first_name')}>×</button>
            </span>
          )}
          {aiFilters.gender && (
            <span className="samani-ai-pill">
              Gender: {aiFilters.gender}
              <button type="button" onClick={() => handleRemoveAiFilter('gender')}>×</button>
            </span>
          )}
          {aiFilters.risk_category && (
            <span className="samani-ai-pill">
              Risk: {aiFilters.risk_category}
              <button type="button" onClick={() => handleRemoveAiFilter('risk_category')}>×</button>
            </span>
          )}
          {aiFilters.primary_diagnosis_group && (
            <span className="samani-ai-pill">
              Diagnosis: {formatDisplayLabel(aiFilters.primary_diagnosis_group)}
              <button type="button" onClick={() => handleRemoveAiFilter('primary_diagnosis_group')}>×</button>
            </span>
          )}
          {aiFilters.race && (
            <span className="samani-ai-pill">
              Race: {aiFilters.race}
              <button type="button" onClick={() => handleRemoveAiFilter('race')}>×</button>
            </span>
          )}
          {aiFilters.primary_physician && (
            <span className="samani-ai-pill">
              Physician: {aiFilters.primary_physician}
              <button type="button" onClick={() => handleRemoveAiFilter('primary_physician')}>×</button>
            </span>
          )}
          {aiFilters.ward_unit && (
            <span className="samani-ai-pill">
              Ward: {aiFilters.ward_unit}
              <button type="button" onClick={() => handleRemoveAiFilter('ward_unit')}>×</button>
            </span>
          )}
          {aiFilters.room_number && (
            <span className="samani-ai-pill">
              Room: {aiFilters.room_number}
              <button type="button" onClick={() => handleRemoveAiFilter('room_number')}>×</button>
            </span>
          )}
          {aiFilters.has_lab_report !== undefined && (
            <span className="samani-ai-pill">
              {aiFilters.has_lab_report ? 'Has lab report' : 'No lab report'}
              <button type="button" onClick={() => handleRemoveAiFilter('has_lab_report')}>×</button>
            </span>
          )}
          {aiFilters.lab_report_type && (
            <span className="samani-ai-pill">
              Report: {aiFilters.lab_report_type}
              <button type="button" onClick={() => handleRemoveAiFilter('lab_report_type')}>×</button>
            </span>
          )}
          {aiFilters.lab_report_status && (
            <span className="samani-ai-pill">
              Report status: {aiFilters.lab_report_status}
              <button type="button" onClick={() => handleRemoveAiFilter('lab_report_status')}>×</button>
            </span>
          )}
          {aiFilters.admission_source && (
            <span className="samani-ai-pill">
              Admission: {formatDisplayLabel(aiFilters.admission_source)}
              <button type="button" onClick={() => handleRemoveAiFilter('admission_source')}>×</button>
            </span>
          )}
          {aiFilters.discharge_destination && (
            <span className="samani-ai-pill">
              Discharge: {formatDisplayLabel(aiFilters.discharge_destination)}
              <button type="button" onClick={() => handleRemoveAiFilter('discharge_destination')}>×</button>
            </span>
          )}
          {aiFilters.min_risk !== undefined && (
            <span className="samani-ai-pill">
              Risk ≥ {aiFilters.min_risk}%
              <button type="button" onClick={() => handleRemoveAiFilter('min_risk')}>×</button>
            </span>
          )}
          {aiFilters.max_risk !== undefined && (
            <span className="samani-ai-pill">
              Risk ≤ {aiFilters.max_risk}%
              <button type="button" onClick={() => handleRemoveAiFilter('max_risk')}>×</button>
            </span>
          )}
        </div>
      )}

      {loading ? <div className="samani-state">Loading patient queue...</div> : null}
      {error ? <div className="samani-state">{error}</div> : null}
      {!loading && !error ? (
        <div className="samani-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Patient ID</th>
                <th onClick={() => handleSort('patient_name')} style={{ cursor: 'pointer' }}>
                  <div className="samani-th-sortable">
                    Patient Name
                    <span className={`samani-sort-icon ${sortKey === 'patient_name' ? 'is-active' : ''}`}>
                      {sortKey === 'patient_name' ? (sortOrder === 'asc' ? '↑' : '↓') : '↕'}
                    </span>
                  </div>
                </th>
                <th onClick={() => handleSort('display_age')} style={{ cursor: 'pointer' }}>
                  <div className="samani-th-sortable">
                    Age
                    <span className={`samani-sort-icon ${sortKey === 'display_age' ? 'is-active' : ''}`}>
                      {sortKey === 'display_age' ? (sortOrder === 'asc' ? '↑' : '↓') : '↕'}
                    </span>
                  </div>
                </th>
                <th>Gender</th>
                <th>Primary Diagnosis Group</th>
                <th>Admission Source</th>
                <th>Discharge Destination</th>
                <th onClick={() => handleSort('calibrated_risk_pct')} style={{ cursor: 'pointer' }}>
                  <div className="samani-th-sortable">
                    Calibrated Risk %
                    <span className={`samani-sort-icon ${sortKey === 'calibrated_risk_pct' ? 'is-active' : ''}`}>
                      {sortKey === 'calibrated_risk_pct' ? (sortOrder === 'asc' ? '↑' : '↓') : '↕'}
                    </span>
                  </div>
                </th>
                <th onClick={() => handleSort('risk_category')} style={{ cursor: 'pointer' }}>
                  <div className="samani-th-sortable">
                    Risk Category
                    <span className={`samani-sort-icon ${sortKey === 'risk_category' ? 'is-active' : ''}`}>
                      {sortKey === 'risk_category' ? (sortOrder === 'asc' ? '↑' : '↓') : '↕'}
                    </span>
                  </div>
                </th>
                <th>View Digital Chart</th>
              </tr>
            </thead>
            <tbody>
              {sortedPatients.map((patient, index) => (
                <tr className="domino-row" style={{ animationDelay: `${40 + index * 40}ms` }} key={patient.patient_id}>
                  <td>{patient.patient_id}</td>
                  <td>{patient.patient_name}</td>
                  <td>{displayAge(patient.display_age, patient.age_band)}</td>
                  <td>{formatDisplayLabel(patient.gender) ?? '--'}</td>
                  <td>{formatDisplayLabel(patient.primary_diagnosis_group) ?? '--'}</td>
                  <td>{formatDisplayLabel(patient.admission_source) ?? '--'}</td>
                  <td>{formatDisplayLabel(patient.discharge_destination) ?? '--'}</td>
                  <td>{riskPercent(patient.calibrated_risk_pct)}</td>
                  <td><span className={`samani-risk samani-risk--${riskTone(patient.risk_category)}`}>{patient.risk_category}</span></td>
                  <td><button type="button" onClick={() => swipeNavigate(`/patients/${patient.patient_id}`)}>Open Chart</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </main>
  );
}

function chartValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '--';
  if (typeof value === 'number') return String(value);
  return formatDisplayLabel(value) ?? value;
}

function parseLabReportManifest(csv: string): LabReportManifestEntry[] {
  const [headerLine, ...lines] = csv.trim().split(/\r?\n/);
  if (!headerLine) return [];
  const headers = headerLine.split(',').map((header) => header.trim());

  return lines
    .map((line) => {
      const values = line.split(',').map((value) => value.trim());
      return headers.reduce<Record<string, string>>((row, header, index) => {
        row[header] = values[index] ?? '';
        return row;
      }, {});
    })
    .filter((row) => row.patient_id && row.json_path)
    .map((row) => ({
      patient_id: row.patient_id,
      encounter_id: row.encounter_id,
      report_type: row.report_type,
      structured_category: row.structured_category,
      simulated_numeric_result: row.simulated_numeric_result,
      unit: row.unit,
      status_label: row.status_label,
      json_path: row.json_path,
      md_path: row.md_path,
    }));
}

function reportDisplayName(entry: LabReportManifestEntry | null | undefined) {
  if (!entry) return 'Lab Report';
  if (entry.report_type === 'HBA1C') return 'HbA1c Report';
  if (entry.report_type === 'GLUCOSE') return 'Glucose Report';
  return `${formatDisplayLabel(entry.report_type) ?? entry.report_type} Report`;
}

function ChartInfo({ label, value, strong }: { label: string; value: React.ReactNode; strong?: boolean }) {
  return <div><span>{label}</span><strong className={strong ? 'is-strong' : ''}>{value}</strong></div>;
}

function renderStatusBadge(type: 'yes-no' | 'insulin' | 'change' | 'reconciliation' | 'education' | 'glycemic', val: string | number | null | undefined) {
  if (val === null || val === undefined || val === '') return '--';
  const str = String(val).trim();
  const lower = str.toLowerCase();
  
  if (type === 'yes-no') {
    if (lower === 'yes') return <span className="samani-risk samani-risk--low">{str}</span>;
    if (lower === 'no') return <span className="samani-risk samani-risk--neutral">{str}</span>;
  }
  
  if (type === 'insulin') {
    if (lower === 'no') return <span className="samani-risk samani-risk--neutral">{str}</span>;
    if (lower === 'steady') return <span className="samani-risk samani-risk--low">Steady</span>;
    if (lower === 'up') return <span className="samani-risk samani-risk--high">Titrated Up</span>;
    if (lower === 'down') return <span className="samani-risk samani-risk--low">Titrated Down</span>;
  }
  
  if (type === 'change') {
    if (lower === 'no') return <span className="samani-risk samani-risk--neutral">No Change</span>;
    if (lower === 'ch' || lower === 'yes' || lower === 'changed') return <span className="samani-risk samani-risk--medium">Changed</span>;
  }
  
  if (type === 'reconciliation') {
    if (lower.includes('pending')) return <span className="samani-risk samani-risk--high">{str}</span>;
    if (lower.includes('reconciled') || lower.includes('done') || lower.includes('complete')) {
      return <span className="samani-risk samani-risk--low">{str}</span>;
    }
  }
  
  if (type === 'education') {
    if (lower === 'completed' || lower === 'done') return <span className="samani-risk samani-risk--low">{str}</span>;
    if (lower === 'recommended') return <span className="samani-risk samani-risk--medium">{str}</span>;
    if (lower === 'refused') return <span className="samani-risk samani-risk--high">{str}</span>;
  }
  
  if (type === 'glycemic') {
    if (lower === 'normal') return <span className="samani-risk samani-risk--low">{str}</span>;
    if (lower.includes('>') || lower === 'high' || lower === 'elevated') {
      return <span className="samani-risk samani-risk--high">{str}</span>;
    }
  }
  
  return <span className="samani-risk samani-risk--neutral">{str}</span>;
}

function parseKeyMedications(medsStr: string | string[] | null | undefined): React.ReactNode {
  if (!medsStr) return <span className="samani-med-none">None recorded</span>;
  const str = Array.isArray(medsStr) ? medsStr.join('; ') : String(medsStr);
  const items = str.split(';').map(s => s.trim()).filter(Boolean);
  
  if (items.length === 0) return <span className="samani-med-none">None recorded</span>;
  
  return (
    <div className="samani-med-chips">
      {items.map((item, idx) => {
        const parts = item.split(':').map(p => p.trim());
        const name = parts[0];
        const status = parts[1];
        
        let statusClass = 'neutral';
        if (status) {
          const sLower = status.toLowerCase();
          if (sLower === 'up') statusClass = 'high';
          else if (sLower === 'down') statusClass = 'low';
          else if (sLower === 'steady') statusClass = 'stable';
        }
        
        return (
          <span key={idx} className="samani-med-chip">
            <span className="samani-med-name">{name}</span>
            {status && (
              <span className={`samani-med-status samani-med-status--${statusClass}`}>
                {status}
              </span>
            )}
          </span>
        );
      })}
    </div>
  );
}

function LabReportModal({
  report,
  reportLabel,
  loading,
  error,
  onClose,
}: {
  report: LabReportData | null;
  reportLabel: string;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}) {
  const [isClosing, setIsClosing] = useState(false);

  const closeWithAnimation = () => {
    if (isClosing) return;
    setIsClosing(true);
    window.setTimeout(onClose, 220);
  };

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeWithAnimation();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [closeWithAnimation]);

  const statusTone = report?.result.status_label?.toLowerCase().includes('normal') ? 'low' : 'high';

  return createPortal(
    <div className={`samani-lab-modal-backdrop ${isClosing ? 'is-closing' : ''}`} role="presentation" onMouseDown={closeWithAnimation}>
      <section
        className={`samani-lab-modal ${isClosing ? 'is-closing' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={reportLabel}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button className="samani-lab-modal-close" type="button" onClick={closeWithAnimation} aria-label="Close lab report">
          <span aria-hidden="true" />
        </button>

        {loading ? <div className="samani-lab-modal-state">Loading structured lab report...</div> : null}
        {!loading && error ? <div className="samani-lab-modal-state">{error}</div> : null}
        {!loading && !error && report ? (
          <>
            <header className="samani-lab-modal-head">
              <div>
                <span>{reportLabel}</span>
                <h3>{report.result.test_name}</h3>
              </div>
              <span className={`samani-risk samani-risk--${statusTone}`}>{report.result.status_label}</span>
            </header>

            <div className="samani-lab-patient-strip">
              <div>
                <span>Patient</span>
                <strong>{chartValue(report.metadata.patient_name)}</strong>
              </div>
              <div>
                <span>MRN</span>
                <strong>{chartValue(report.metadata.synthetic_mrn)}</strong>
              </div>
              <div>
                <span>Patient ID</span>
                <strong>{chartValue(report.metadata.patient_id)}</strong>
              </div>
              <div>
                <span>Encounter</span>
                <strong>{chartValue(report.metadata.encounter_id)}</strong>
              </div>
            </div>

            <div className="samani-lab-result-band">
              <span>{report.result.investigation}</span>
              <strong>{report.result.simulated_numeric_result} {report.result.unit}</strong>
              <small>{report.result.reference_range_text}</small>
            </div>

            <div className="samani-lab-detail-grid">
              <ChartInfo label="Age / Gender:" value={`${chartValue(report.metadata.age_display)} / ${chartValue(report.metadata.gender)}`} />
              <ChartInfo label="Primary Physician:" value={chartValue(report.metadata.primary_physician)} />
              <ChartInfo label="Reviewed By:" value={chartValue(report.metadata.reviewed_by)} />
              <ChartInfo label="Collection Time:" value={chartValue(report.metadata.collection_datetime)} />
              <ChartInfo label="Reported Time:" value={chartValue(report.metadata.reported_datetime)} />
              <ChartInfo label="Source Category:" value={chartValue(report.result.structured_category)} />
            </div>

            <div className="samani-lab-narrative">
              <section>
                <h4>Interpretation</h4>
                <p>{report.interpretation}</p>
              </section>
            </div>

            <footer className="samani-lab-safety-note">{report.limitation || LAB_REPORT_SAFETY_NOTE}</footer>
          </>
        ) : null}
      </section>
    </div>,
    document.body
  );
}

function renderBoldText(text: string): React.ReactNode {
  const parts = text.split(/\*\*([^*]+)\*\*/g);
  return parts.map((part, index) => {
    if (index % 2 === 1) {
      return <strong key={index} className="font-semibold text-teal-950">{part}</strong>;
    }
    return part;
  });
}

function parseMarkdown(text: string): React.ReactNode {
  if (!text) return null;
  const lines = text.split('\n');
  const renderedElements: React.ReactNode[] = [];
  
  let currentTableRows: string[][] = [];
  let isTable = false;

  const flushTable = (key: number) => {
    if (currentTableRows.length === 0) return;
    const headers = currentTableRows[0];
    let rows = currentTableRows.slice(1);
    if (rows.length > 0 && rows[0].every(cell => cell.trim().startsWith('-') || cell.trim().includes('---') || cell.trim() === '')) {
      rows = rows.slice(1);
    }
    
    renderedElements.push(
      <div key={`table-${key}`} className="overflow-x-auto my-2 rounded-lg border border-slate-200/50">
        <table className="min-w-full divide-y divide-slate-200/50 text-[12px] bg-white/20 backdrop-blur-sm">
          <thead>
            <tr className="bg-slate-100/30">
              {headers.map((h, i) => (
                <th key={i} className="px-3 py-2 text-left font-semibold text-slate-800 border-b border-slate-200/50">{h.trim()}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200/30">
            {rows.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-slate-50/10">
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className="px-3 py-2 text-slate-700">{renderBoldText(cell.trim())}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
    currentTableRows = [];
    isTable = false;
  };

  for (let idx = 0; idx < lines.length; idx++) {
    const line = lines[idx];
    const trimmed = line.trim();

    if (trimmed.startsWith('|')) {
      isTable = true;
      const cells = line.split('|').slice(1, -1);
      currentTableRows.push(cells);
      continue;
    } else if (isTable) {
      flushTable(idx);
    }

    if (trimmed.startsWith('### ')) {
      renderedElements.push(<h3 key={idx} className="text-sm font-bold text-[#027980] mt-3 mb-1" style={{ fontSize: '14px' }}>{trimmed.substring(4)}</h3>);
    } else if (trimmed.startsWith('#### ')) {
      renderedElements.push(<h4 key={idx} className="text-xs font-bold text-teal-700 mt-2 mb-1" style={{ fontSize: '12px' }}>{trimmed.substring(5)}</h4>);
    } else if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
      const content = trimmed.substring(2);
      renderedElements.push(
        <li key={idx} className="ml-4 list-disc text-[13px] text-slate-700 leading-relaxed mb-0.5">
          {renderBoldText(content)}
        </li>
      );
    } else if (/^\d+\.\s/.test(trimmed)) {
      const dotIndex = trimmed.indexOf('.');
      const content = trimmed.substring(dotIndex + 1).trim();
      renderedElements.push(
        <li key={idx} className="ml-4 list-decimal text-[13px] text-slate-700 leading-relaxed mb-0.5" style={{ listStyleType: 'decimal' }}>
          {renderBoldText(content)}
        </li>
      );
    } else if (trimmed === '') {
      renderedElements.push(<div key={idx} className="h-2" />);
    } else {
      renderedElements.push(
        <p key={idx} className="text-[13px] text-slate-700 leading-relaxed mb-1" style={{ margin: '0 0 4px 0' }}>
          {renderBoldText(trimmed)}
        </p>
      );
    }
  }

  if (isTable) {
    flushTable(lines.length);
  }

  return renderedElements;
}

function PatientChartPortal({ 
  active, 
  chart, 
  loading, 
  error, 
  customNotes, 
  onAddCustomNote 
}: { 
  active: boolean; 
  chart: PatientChartResponse | null; 
  loading: boolean; 
  error: string | null; 
  customNotes: Array<{ date: string; note: string; type: string; status: string }>; 
  onAddCustomNote: (text: string) => void 
}) {
  const swipeNavigate = useSwipeNavigate();
  const location = useLocation();
  const navigate = useNavigate();
  const [aiPrompt, setAiPrompt] = useState('');
  const [labReportEntries, setLabReportEntries] = useState<LabReportManifestEntry[]>([]);
  const [selectedLabReportPath, setSelectedLabReportPath] = useState('');
  const [labReport, setLabReport] = useState<LabReportData | null>(null);
  const [labReportLoading, setLabReportLoading] = useState(false);
  const [labReportError, setLabReportError] = useState<string | null>(null);
  const [labReportOpen, setLabReportOpen] = useState(false);
  const [mobileCopilotOpen, setMobileCopilotOpen] = useState(false);

  interface MessageItem {
    id: string;
    role: 'user' | 'assistant';
    content?: string;
    result?: any;
    timestamp: string;
  }

  // AI Copilot state
  const [evaluationState, setEvaluationState] = useState<'idle' | 'evaluating' | 'completed' | 'error'>('idle');
  const [evaluationResult, setEvaluationResult] = useState<CopilotEvaluateResponse | null>(null);
  const [activePhaseIndex, setActivePhaseIndex] = useState(-1);
  const [expandedPhaseIndex, setExpandedPhaseIndex] = useState<number | null>(null);
  const [expandedTechPhases, setExpandedTechPhases] = useState<Record<number, boolean>>({});

  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatLoadingIntent, setChatLoadingIntent] = useState<'evaluate' | 'generic' | null>(null);

  const responseStartRef = useRef<HTMLDivElement>(null);
  const consumedCopilotPromptRef = useRef('');
  const chartPatientId = chart?.patient_id;
  const activePatientRef = useRef<string | undefined>(chartPatientId);
  const chatRequestSeqRef = useRef(0);
  const pendingCopilotPrompt = typeof (location.state as any)?.copilotPrompt === 'string'
    ? ((location.state as any).copilotPrompt as string).trim()
    : '';
  const latestAssistantId = useMemo(
    () => [...messages].reverse().find((message) => message.role === 'assistant')?.id,
    [messages],
  );

  // Reset evaluation state when patient ID changes
  useEffect(() => {
    activePatientRef.current = chartPatientId;
    chatRequestSeqRef.current += 1;
    setEvaluationState('idle');
    setEvaluationResult(null);
    setActivePhaseIndex(-1);
    setExpandedPhaseIndex(null);
    setExpandedTechPhases({});
    setMessages([]);
    setChatLoading(false);
    setChatLoadingIntent(null);
    setMobileCopilotOpen(false);
  }, [chartPatientId]);

  useEffect(() => {
    if (!mobileCopilotOpen) return;

    const mediaQuery = window.matchMedia('(max-width: 980px)');
    const previousOverflow = document.body.style.overflow;
    if (mediaQuery.matches) {
      document.body.style.overflow = 'hidden';
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMobileCopilotOpen(false);
    };

    window.addEventListener('keydown', handleEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', handleEscape);
    };
  }, [mobileCopilotOpen]);

  // Keep new AI results anchored at the start of the response, not at the follow-up prompts.
  useEffect(() => {
    if (!chatLoading && latestAssistantId && responseStartRef.current) {
      responseStartRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [latestAssistantId, chatLoading]);

  const handleSendMessage = async (text: string) => {
    if (!text.trim() || !chartPatientId || chatLoading) return;

    const userMsgText = text.trim();
    const requestPatientId = chartPatientId;
    const requestSeq = chatRequestSeqRef.current + 1;
    chatRequestSeqRef.current = requestSeq;
    const isCurrentRequest = () => (
      activePatientRef.current === requestPatientId &&
      chatRequestSeqRef.current === requestSeq
    );
    setAiPrompt('');

    const userMsg: MessageItem = {
      id: 'user-' + Date.now(),
      role: 'user',
      content: userMsgText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setChatLoading(true);

    const isEvaluate = isDischargeReadinessPrompt(userMsgText);

    setChatLoadingIntent(isEvaluate ? 'evaluate' : 'generic');
    if (isEvaluate) {
      setActivePhaseIndex(0);
    }

    try {
      if (isEvaluate) {
        const response = await chatWithCopilot(chartPatientId, userMsgText);
        if (!isCurrentRequest()) return;
        setChatLoadingIntent('evaluate');
        setActivePhaseIndex(0);

        let currentPhase = 0;
        const interval = setInterval(() => {
          if (!isCurrentRequest()) {
            clearInterval(interval);
            return;
          }
          currentPhase += 1;
          if (currentPhase < 5) {
            setActivePhaseIndex(currentPhase);
          } else {
            clearInterval(interval);
            const assistantMsg: MessageItem = {
              id: 'assistant-' + Date.now(),
              role: 'assistant',
              result: response,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            };
            setMessages((prev) => [...prev, assistantMsg]);
            setChatLoading(false);
            setChatLoadingIntent(null);
            setEvaluationState('completed');
          }
        }, 850);
      } else {
        const history = messages.map((m) => {
          let content = '';
          if (m.role === 'user') {
            content = m.content || '';
          } else {
            content = m.content || m.result?.answer_markdown || m.result?.answer || '';
          }
          return {
            role: m.role,
            content: content,
          };
        });

        const response = await askGeminiCopilot(chartPatientId, userMsgText, history);
        setTimeout(() => {
          if (!isCurrentRequest()) return;
          const assistantMsg: MessageItem = {
            id: 'assistant-' + Date.now(),
            role: 'assistant',
            result: response,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
          setMessages((prev) => [...prev, assistantMsg]);
          setChatLoading(false);
          setChatLoadingIntent(null);
        }, 600);
      }
    } catch (err) {
      if (!isCurrentRequest()) return;
      console.error(err);
      const errorMsg: MessageItem = {
        id: 'assistant-error-' + Date.now(),
        role: 'assistant',
        content: 'AI Copilot is temporarily unavailable. The rule-based discharge checklist is still available.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
      setChatLoading(false);
      setChatLoadingIntent(null);
    }
  };

  useEffect(() => {
    if (!active || loading || error || !chartPatientId || !pendingCopilotPrompt || chatLoading) return;

    const promptKey = `${chartPatientId}:${pendingCopilotPrompt}`;
    if (consumedCopilotPromptRef.current === promptKey) return;

    consumedCopilotPromptRef.current = promptKey;
    setMobileCopilotOpen(true);
    handleSendMessage(pendingCopilotPrompt);
    navigate(location.pathname, { replace: true, state: {} });
  }, [active, loading, error, chartPatientId, pendingCopilotPrompt, chatLoading, location.pathname, navigate]);
  
  const activeClass = active ? 'is-active' : 'is-inactive';

  useEffect(() => {
    let cancelled = false;
    setLabReportEntries([]);
    setSelectedLabReportPath('');
    setLabReport(null);
    setLabReportError(null);
    setLabReportOpen(false);

    if (!chartPatientId) {
      return () => {
        cancelled = true;
      };
    }

    fetch(`${LAB_REPORT_BASE}/lab_report_manifest.csv`)
      .then((response) => {
        if (!response.ok) throw new Error('Lab report manifest is not available.');
        return response.text();
      })
      .then((csv) => {
        if (cancelled) return;
        const entries = parseLabReportManifest(csv).filter((entry) => entry.patient_id === chartPatientId);
        setLabReportEntries(entries);
        setSelectedLabReportPath(entries[0]?.json_path ?? '');
      })
      .catch(() => {
        if (!cancelled) setLabReportEntries([]);
      });

    return () => {
      cancelled = true;
    };
  }, [chartPatientId]);

  if (loading) return <main className={`samani-chart-view ${activeClass}`}><div className="samani-state">Loading patient chart...</div></main>;
  if (error) return <main className={`samani-chart-view ${activeClass}`}><div className="samani-state">{error}</div></main>;
  if (!chart) return <main className={`samani-chart-view ${activeClass}`}><div className="samani-state">No patient chart found.</div></main>;

  const identity = chart.box_1_demographics_encounter.patient_identity;
  const demographics = chart.box_1_demographics_encounter.demographics;
  const encounter = chart.box_1_demographics_encounter.encounter_context;
  const labs = chart.box_3_clinical_review.labs_glycemic_monitoring;
  const meds = chart.box_3_clinical_review.medication_review;
  const diagnosis = chart.box_3_clinical_review.diagnosis_review;
  const age = displayAge(demographics.display_age ?? (typeof demographics.age === 'number' ? demographics.age : null), demographics.age_band ?? null);

  const patientInsight = MOCK_AI_INSIGHTS[chart.patient_id] || DEFAULT_AI_INSIGHT;
  const selectedLabReportEntry = labReportEntries.find((entry) => entry.json_path === selectedLabReportPath) ?? labReportEntries[0] ?? null;

  const handleSendPrompt = () => {
    const text = aiPrompt.trim();
    if (text) {
      onAddCustomNote(text);
      setAiPrompt('');
    }
  };

  const handleOpenLabReport = async () => {
    const entry = selectedLabReportEntry;
    if (!entry) return;
    setLabReportOpen(true);
    setLabReportLoading(true);
    setLabReportError(null);
    setLabReport(null);

    try {
      const response = await fetch(`${LAB_REPORT_BASE}/${entry.json_path}`);
      if (!response.ok) throw new Error('Unable to load this structured lab report.');
      const data = await response.json() as LabReportData;
      setLabReport(data);
    } catch (err) {
      setLabReportError(err instanceof Error ? err.message : 'Unable to load this structured lab report.');
    } finally {
      setLabReportLoading(false);
    }
  };

  return (
    <main className={`samani-chart-view ${activeClass}`}>
      <div className="samani-chart-left">
        <section className="samani-chart-card samani-chart-head-card">
          <div className="samani-patient-hero-main">
            <span className="samani-avatar">👤</span>
            <div className="samani-patient-summary">
              <div className="samani-patient-title">
                <h3>{chartValue(identity.patient_name)}</h3>
                <span className={`samani-risk samani-risk--${riskTone(identity.risk_category)}`}>{identity.risk_category}</span>
              </div>
              <div className="samani-patient-meta-pills" aria-label="Patient case details">
                <span>{chartValue(identity.mrn)}</span>
                <span>{age} years old</span>
                <span>{chartValue(demographics.gender)}</span>
                <span>{chartValue(identity.ward_unit)}</span>
              </div>
            </div>
          </div>
          <div className="samani-patient-hero-actions">
            <small>Case workspace</small>
            <button type="button" onClick={() => swipeNavigate('/queue')}>← Back to Queue</button>
          </div>
        </section>

        <section className="samani-demographic-grid">
          <article className="samani-chart-card">
            <h4>Primary Provider</h4>
            <ChartInfo label="Physician:" value={chartValue(identity.primary_physician)} strong />
            <ChartInfo label="Ward / Unit:" value={chartValue(identity.ward_unit)} />
            <ChartInfo label="Room Number:" value={chartValue(identity.room_number)} strong />
          </article>
          <article className="samani-chart-card">
            <h4>Demographics</h4>
            <ChartInfo label="Age / Gender:" value={`${age} / ${chartValue(demographics.gender)}`} />
            <ChartInfo label="Age Band:" value={chartValue(demographics.age_band)} />
            <ChartInfo label="Race:" value={chartValue(demographics.race)} />
          </article>
          <article className="samani-chart-card">
            <h4>Encounter Context</h4>
            <ChartInfo label="Admission Type:" value={chartValue(encounter.admission_type)} />
            <ChartInfo label="Time in Hospital:" value={`${encounter.time_in_hospital ?? '--'} Days`} />
            <ChartInfo label="Scheduled Discharge:" value={`${encounter.scheduled_discharge_date ?? '--'} at ${encounter.scheduled_discharge_time ?? '--'}`} strong />
          </article>
        </section>

        <section className="samani-stat-grid">
          <article className="samani-chart-card">
            <h4>🔬 Labs & Glycemic Monitoring</h4>
            
            <div className="samani-card-subgroup">
              <h5>Glycemic Status</h5>
              <ChartInfo label="HbA1c Result / Status:" value={renderStatusBadge('glycemic', labs.hba1c_result_status)} />
              <ChartInfo label="Max Glucose Result / Status:" value={renderStatusBadge('glycemic', labs.max_glucose_result_status)} />
            </div>

            <div className="samani-card-subgroup" style={{ marginTop: '24px' }}>
              <h5>Lab Activity & Review</h5>
              <ChartInfo label="Lab Procedures Count:" value={<strong>{labs.lab_procedures_count ?? '--'}</strong>} />
              <ChartInfo label="Last Lab Review:" value={<span>{labs.last_lab_review_timestamp ?? '--'}</span>} />
              <ChartInfo label="Reviewed By:" value={<span style={{ fontWeight: 600, color: '#374151' }}>👩‍⚕️ {chartValue(labs.reviewed_by)}</span>} />
              {labReportEntries.length > 0 ? (
                <div className="samani-lab-report-actions">
                  {labReportEntries.length > 1 ? (
                    <select
                      aria-label="Choose lab report"
                      value={selectedLabReportPath}
                      onChange={(event) => setSelectedLabReportPath(event.target.value)}
                    >
                      {labReportEntries.map((entry) => (
                        <option key={entry.json_path} value={entry.json_path}>{reportDisplayName(entry)}</option>
                      ))}
                    </select>
                  ) : null}
                  <button type="button" onClick={handleOpenLabReport}>
                    <span aria-hidden="true">↗</span>
                    View Lab Report
                  </button>
                </div>
              ) : null}
            </div>
          </article>

          <article className="samani-chart-card">
            <h4>💊 Medication Review</h4>
            
            <div className="samani-status-row-grid">
              <div className="samani-status-cell">
                <span className="label">Diabetes Meds</span>
                {renderStatusBadge('yes-no', meds.diabetes_medication_used)}
              </div>
              <div className="samani-status-cell">
                <span className="label">Insulin Status</span>
                {renderStatusBadge('insulin', meds.insulin_status)}
              </div>
              <div className="samani-status-cell">
                <span className="label">Med Change</span>
                {renderStatusBadge('change', meds.medication_change_during_stay)}
              </div>
            </div>

            <div className="samani-card-subgroup">
              <h5>Active Prescriptions</h5>
              <ChartInfo label="Active Medication Count:" value={<strong>{meds.active_medication_count ?? '--'}</strong>} />
              <ChartInfo label="Key Diabetes Medications:" value={parseKeyMedications(meds.key_diabetes_medications)} />
            </div>

            <div className="samani-card-subgroup" style={{ marginTop: '20px' }}>
              <h5>Discharge & Pharmacy Review</h5>
              <ChartInfo label="Medication Reconciliation:" value={renderStatusBadge('reconciliation', meds.medication_reconciliation_status)} />
              <ChartInfo label="Diabetes Education:" value={renderStatusBadge('education', meds.diabetes_education_status)} />
              <ChartInfo label="Pharmacist Review:" value={<span style={{ fontWeight: 600, color: '#374151' }}>👨‍🔬 {chartValue(meds.reviewed_by_pharmacist)}</span>} />
            </div>
          </article>
        </section>

        <section className="samani-chart-card samani-timeline-section">
          <h4>📝 Diagnosis Timeline & Clinical Notes</h4>
          {(() => {
            const combinedTimeline: Array<{
              id: string;
              date: string;
              title: string;
              content: string;
              type: 'Diagnosis' | 'Copilot Feed';
              diagnosedBy?: string | null;
              department?: string | null;
              group?: string | null;
              rank?: number | null;
            }> = [];

            // Add custom notes
            customNotes.forEach((note, idx) => {
              combinedTimeline.push({
                id: `custom-${idx}`,
                date: note.date,
                title: 'Dr Samani Prompt Reply',
                content: note.note,
                type: 'Copilot Feed',
                diagnosedBy: 'MedviseAI Copilot',
                department: 'AI Assistant',
              });
            });

            // Add diagnosis timeline
            diagnosis.diagnosis_timeline.forEach((item) => {
              combinedTimeline.push({
                id: `diagnosis-${item.diagnosis_rank}-${item.date_recorded}`,
                date: item.date_recorded ?? '',
                title: item.diagnosis_label ?? 'Diagnosis',
                content: item.clinical_note ?? '',
                type: 'Diagnosis',
                diagnosedBy: item.diagnosed_by,
                department: item.department_specialty,
                group: item.diagnosis_group,
                rank: item.diagnosis_rank,
              });
            });

            // Sort chronologically (oldest date first)
            combinedTimeline.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

            if (combinedTimeline.length === 0) {
              return <p className="samani-state">No timeline events recorded.</p>;
            }

            return (
              <div className="samani-timeline-container">
                <div className="samani-timeline-line" />
                {combinedTimeline.map((item, idx) => {
                  const isCopilot = item.type === 'Copilot Feed';
                  return (
                    <div key={item.id} className="samani-timeline-item">
                      <div className="samani-timeline-badge">{idx + 1}</div>
                      <div className="samani-timeline-card">
                        <div className="samani-timeline-header">
                          <span className="samani-timeline-date">{chartValue(item.date)}</span>
                          <span className={`samani-timeline-type ${isCopilot ? 'samani-timeline-type--copilot' : ''}`}>
                            {item.type}
                          </span>
                        </div>
                        <h5 className="samani-timeline-title">
                          {isCopilot ? (
                            <>
                              <span style={{ color: '#027980' }}>MedviseAI:</span> {item.title}
                            </>
                          ) : (
                            item.title
                          )}
                        </h5>
                        <p className="samani-timeline-content">"{item.content}"</p>
                        
                        <div className="samani-timeline-details">
                          <div className="samani-timeline-details-item">
                            <span>Diagnosed By / Source</span>
                            <strong>{chartValue(item.diagnosedBy ?? 'Attending Physician')}</strong>
                          </div>
                          <div className="samani-timeline-details-item">
                            <span>Department / Specialty</span>
                            <strong>{chartValue(item.department ?? 'General Medicine')}</strong>
                          </div>
                          {!isCopilot && item.group && (
                            <div className="samani-timeline-details-item">
                              <span>Diagnosis Group</span>
                              <strong>{chartValue(item.group)}</strong>
                            </div>
                          )}
                          {!isCopilot && typeof item.rank === 'number' && (
                            <div className="samani-timeline-details-item">
                              <span>Diagnosis Rank</span>
                              <strong>Primary Rank {item.rank}</strong>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })()}
        </section>
      </div>

      <button
        type="button"
        className={`samani-mobile-copilot-backdrop ${mobileCopilotOpen ? 'is-open' : ''}`}
        aria-label="Close Clinical AI Copilot"
        onClick={() => setMobileCopilotOpen(false)}
      />

      <button
        type="button"
        className={`samani-mobile-copilot-fab ${mobileCopilotOpen ? 'is-hidden' : ''}`}
        aria-label="Open Clinical AI Copilot"
        aria-expanded={mobileCopilotOpen}
        onClick={() => setMobileCopilotOpen(true)}
      >
        <span aria-hidden="true">✦</span>
        <strong>AI Copilot</strong>
        <small>Ask about this case</small>
      </button>

      <aside className={`samani-ai-card ${mobileCopilotOpen ? 'is-mobile-open' : ''}`}>
        <button
          type="button"
          className="samani-mobile-copilot-close"
          aria-label="Close Clinical AI Copilot"
          onClick={() => setMobileCopilotOpen(false)}
        >
          ×
        </button>
        <div className="samani-ai-body" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
          <div className="samani-ai-head">
            <div className="w-6 h-6 rounded-full bg-teal-50 text-[#027980] flex items-center justify-center font-bold text-sm">✦</div>
            <span className="text-[11px] text-[#027980] uppercase font-bold tracking-widest block" style={{ letterSpacing: '0.08em' }}>Clinical AI Copilot</span>
          </div>
          {messages.length === 0 && !chatLoading ? (
            <div className="samani-copilot-intro" style={{ padding: '20px' }}>
              <h4 className="text-sm font-semibold text-teal-800 mb-2" style={{ fontSize: '14px', color: '#0f766e', fontWeight: 600 }}>Hello! How can I assist you with this patient today?</h4>
              <p className="samani-copilot-intro-text" style={{ fontSize: '13px', lineHeight: '1.45', color: '#4b5563', margin: '0 0 16px 0' }}>
                I can review structured clinical records, translate risk predictions, and evaluate discharge readiness. Ask a free-form question or use the quick actions below:
              </p>
              
              <button 
                className="samani-evaluate-btn" 
                type="button" 
                onClick={() => handleSendMessage("Evaluate discharge readiness")}
                style={{ width: '100%', padding: '10px', background: '#027980', color: '#fff', border: 'none', borderRadius: '6px', fontWeight: 600, cursor: 'pointer', marginBottom: '16px' }}
              >
                ✦ Evaluate Discharge Readiness
              </button>

              <div className="samani-copilot-phases-preview" style={{ marginBottom: '16px', background: 'rgba(243, 244, 246, 0.4)', padding: '12px', borderRadius: '8px' }}>
                <h5 style={{ fontSize: '12px', fontWeight: 600, color: '#374151', margin: '0 0 8px 0' }}>Checklist Phases Evaluated</h5>
                <ul style={{ display: 'flex', flexDirection: 'column', gap: '6px', padding: 0, margin: 0, listStyle: 'none' }}>
                  <li style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#4b5563' }}><span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '18px', height: '18px', borderRadius: '50%', background: '#e0f2f1', color: '#00695c', fontSize: '10px', fontWeight: 'bold' }}>1</span> Historical Risk Profile</li>
                  <li style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#4b5563' }}><span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '18px', height: '18px', borderRadius: '50%', background: '#e0f2f1', color: '#00695c', fontSize: '10px', fontWeight: 'bold' }}>2</span> Current Encounter Complexity</li>
                  <li style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#4b5563' }}><span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '18px', height: '18px', borderRadius: '50%', background: '#e0f2f1', color: '#00695c', fontSize: '10px', fontWeight: 'bold' }}>3</span> Labs & Glycemic Review</li>
                  <li style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#4b5563' }}><span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '18px', height: '18px', borderRadius: '50%', background: '#e0f2f1', color: '#00695c', fontSize: '10px', fontWeight: 'bold' }}>4</span> Medication & Diabetes Regimen</li>
                  <li style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#4b5563' }}><span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '18px', height: '18px', borderRadius: '50%', background: '#e0f2f1', color: '#00695c', fontSize: '10px', fontWeight: 'bold' }}>5</span> Discharge Readiness & Care Transition</li>
                </ul>
              </div>

              <div className="samani-copilot-suggested-title" style={{ fontSize: '12px', fontWeight: 600, color: '#374151', margin: '0 0 8px 0' }}>Suggested Inquiries</div>
              <div className="samani-copilot-suggested-chips" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {[
                  "Why is this patient high risk?",
                  "Review labs",
                  "Review medications",
                  "Summarize diagnoses",
                  "Review follow-up needs"
                ].map((q, idx) => (
                  <button key={idx} type="button" className="samani-copilot-chip" onClick={() => handleSendMessage(q)} style={{ background: '#f3f4f6', border: '1px solid #e5e7eb', padding: '6px 12px', borderRadius: '16px', fontSize: '12px', color: '#374151', cursor: 'pointer' }}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="samani-copilot-chat-history" style={{ padding: '20px' }}>
              {messages.map((msg, index) => {
                const isUser = msg.role === 'user';
                return (
                  <div
                    key={msg.id}
                    ref={!isUser && msg.id === latestAssistantId ? responseStartRef : null}
                    className={`samani-chat-row ${isUser ? 'is-user' : 'is-assistant'} ${!isUser ? 'samani-chat-row--fresh' : ''}`}
                  >
                    {isUser ? (
                      <div className="samani-chat-bubble-user">
                        {msg.content}
                      </div>
                    ) : (
                      <div className="samani-chat-bubble-assistant" style={{ width: '100%' }}>
                        {msg.result ? (
                          <>
                            {/* Render plain language answer parsed with regex-markdown */}
                            <div className="samani-chat-text-response">
                              {parseMarkdown(msg.result.answer_markdown || msg.result.answer || '')}
                            </div>
                            
                            {/* If it's Gemini chat response, show context used inside technical evidence accordion */}
                            {msg.result.mode === 'gemini_patient_chat' ? (
                              <div className="samani-copilot-response-gemini" style={{ width: '100%', marginTop: '6px' }}>
                                {msg.result.context_used && (
                                  <div className="samani-copilot-tech-accordion">
                                    <div 
                                      className="samani-copilot-tech-header" 
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setExpandedTechPhases(prev => ({ ...prev, [999 + index]: !prev[999 + index] }));
                                      }}
                                    >
                                      <span>
                                        <strong>Model evidence</strong>
                                        <small>Audit details</small>
                                      </span>
                                      <i>{expandedTechPhases[999 + index] ? 'Hide' : 'Show'}</i>
                                    </div>
                                    {expandedTechPhases[999 + index] && (
                                      <div className="samani-copilot-tech-content">
                                        <h6 style={{ fontSize: '10px', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', margin: '0 0 6px 0' }}>Patient Context Utilized</h6>
                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                          {Object.entries(msg.result.context_used).map(([key, val]) => {
                                            if (!val) return null;
                                            const label = key
                                              .split('_')
                                              .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                                              .join(' ');
                                            return (
                                              <span key={key} style={{ background: 'rgba(2, 121, 128, 0.05)', color: '#0f766e', border: '1px solid rgba(2, 121, 128, 0.1)', padding: '2px 8px', borderRadius: '12px', fontSize: '10px', fontWeight: 500 }}>
                                                {label}
                                              </span>
                                            );
                                          })}
                                        </div>
                                        {msg.result.safety_note && (
                                          <div style={{ fontSize: '10px', color: '#6b7280', marginTop: '8px', fontStyle: 'italic', borderTop: '1px solid #f3f4f6', paddingTop: '6px' }}>
                                            {msg.result.safety_note}
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            ) : msg.result.intent === 'evaluate_discharge_readiness' && msg.result.overall_assessment && msg.result.phases ? (
                              <div className="samani-copilot-response-evaluate" style={{ width: '100%', marginTop: '12px' }}>
                                <div className={`samani-overall-assessment-card ${msg.result.overall_assessment.risk_category === 'High Risk' ? 'has-concern' : msg.result.overall_assessment.risk_category === 'Medium Risk' ? 'has-review' : 'has-clear'}`}>
                                  <h5>
                                    <span>Overall Assessment</span>
                                    <span className={`samani-copilot-phase-badge ${msg.result.overall_assessment.risk_category === 'High Risk' ? 'concern' : msg.result.overall_assessment.risk_category === 'Medium Risk' ? 'review' : 'clear'}`} style={{ padding: '2px 8px', fontSize: '10px', fontWeight: 600 }}>
                                      {msg.result.overall_assessment.risk_category}
                                    </span>
                                  </h5>
                                  <p>{msg.result.overall_assessment.summary}</p>
                                </div>

                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
                                  {msg.result.phases.map((phase: any, idx: number) => {
                                    const isExpanded = expandedPhaseIndex === idx;
                                    const statusTone = phase.status;
                                    const techExpanded = !!expandedTechPhases[phase.phase_number];

                                    return (
                                      <div 
                                        key={phase.phase_number} 
                                        className={`samani-copilot-phase-card has-${statusTone}`} 
                                      >
                                        <div 
                                          className="samani-copilot-phase-header" 
                                          onClick={() => setExpandedPhaseIndex(isExpanded ? null : idx)}
                                        >
                                          <div className="samani-copilot-phase-title">
                                            <span>
                                              {phase.phase_number}
                                            </span>
                                            {phase.phase_name}
                                          </div>
                                          <span className={`samani-copilot-phase-badge ${statusTone}`} style={{ padding: '2px 8px', fontSize: '10px', fontWeight: 600 }}>
                                            {statusTone === 'concern' ? 'Concern' : statusTone === 'review' ? 'Review' : 'Clear'}
                                          </span>
                                        </div>
                                        
                                        {/* Plain summary (copilot_note) displayed collapsed or expanded */}
                                        <div className="samani-copilot-note-shell">
                                          <p className="samani-copilot-note-text">{phase.copilot_note}</p>
                                        </div>

                                        <div className={`samani-copilot-phase-content-shell ${isExpanded ? 'is-expanded' : ''}`}>
                                          <div className="samani-copilot-phase-content">
                                            {phase.evidence_used && phase.evidence_used.length > 0 && (
                                              <div style={{ marginTop: '10px' }}>
                                                <h6 className="samani-copilot-section-title" style={{ fontSize: '11px', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', margin: '4px 0' }}>Evidence Observed</h6>
                                                <ul className="samani-copilot-evidence-list">
                                                  {phase.evidence_used.map((ev: any, eIdx: number) => (
                                                    <li key={eIdx}>{ev}</li>
                                                  ))}
                                                </ul>
                                              </div>
                                            )}
                                            
                                            {/* Nested Technical Model Evidence segment */}
                                            <div className="samani-copilot-tech-accordion">
                                              <div 
                                                className="samani-copilot-tech-header" 
                                                onClick={(e) => {
                                                  e.stopPropagation();
                                                  setExpandedTechPhases(prev => ({ ...prev, [phase.phase_number]: !techExpanded }));
                                                }}
                                              >
                                                <span>
                                                  <strong>Model evidence</strong>
                                                  <small>SHAP audit trail</small>
                                                </span>
                                                <i>{techExpanded ? 'Hide' : 'Show'}</i>
                                              </div>
                                              {techExpanded && (
                                                <div className="samani-copilot-tech-content">
                                                  {phase.shap_context && phase.shap_context.length > 0 ? (
                                                    <div>
                                                      <h6 className="samani-copilot-section-title" style={{ fontSize: '10px', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase' }}>Model Explanation (SHAP)</h6>
                                                      <ul className="samani-copilot-shap-list">
                                                        {phase.shap_context.map((sh: any, sIdx: number) => (
                                                          <li key={sIdx}>{sh}</li>
                                                        ))}
                                                      </ul>
                                                    </div>
                                                  ) : (
                                                    <div style={{ fontSize: '11px', color: '#9ca3af' }}>No model feature metrics available for this phase.</div>
                                                  )}
                                                </div>
                                              )}
                                            </div>
                                          </div>
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            ) : (
                              /* Generic intents rendering: show technical evidence accordion below the bubble if any exists */
                              <div className="samani-copilot-response-generic" style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%', marginTop: '6px' }}>
                                {msg.result.technical_evidence && (msg.result.technical_evidence.shap_context?.length > 0 || msg.result.technical_evidence.structured_fields_used?.length > 0) && (
                                  <div className="samani-copilot-tech-accordion">
                                    <div 
                                      className="samani-copilot-tech-header" 
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setExpandedTechPhases(prev => ({ ...prev, [999 + index]: !prev[999 + index] }));
                                      }}
                                    >
                                      <span>
                                        <strong>Model evidence</strong>
                                        <small>Audit details</small>
                                      </span>
                                      <i>{expandedTechPhases[999 + index] ? 'Hide' : 'Show'}</i>
                                    </div>
                                    {expandedTechPhases[999 + index] && (
                                      <div className="samani-copilot-tech-content">
                                        {msg.result.technical_evidence.shap_context?.length > 0 && (
                                          <div style={{ marginBottom: '8px' }}>
                                            <h6 style={{ fontSize: '10px', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', margin: '0 0 4px 0' }}>SHAP Explanation context</h6>
                                            <ul style={{ paddingLeft: '14px', listStyleType: 'disc', margin: 0 }}>
                                              {msg.result.technical_evidence.shap_context.map((sh: any, sIdx: number) => (
                                                <li key={sIdx} style={{ color: '#6b7280', marginBottom: '2px' }}>{sh}</li>
                                              ))}
                                            </ul>
                                          </div>
                                        )}
                                        {msg.result.technical_evidence.structured_fields_used?.length > 0 && (
                                          <div>
                                            <h6 style={{ fontSize: '10px', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', margin: '0 0 4px 0' }}>Structured fields utilized</h6>
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '2px' }}>
                                              {msg.result.technical_evidence.structured_fields_used.map((field: any, fIdx: number) => (
                                                <span key={fIdx} style={{ background: '#f3f4f6', padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontFamily: 'monospace' }}>{field}</span>
                                              ))}
                                            </div>
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            )}
                          </>
                        ) : (
                          <div className="samani-chat-text-response">
                            {parseMarkdown(msg.content || '')}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {chatLoading && chatLoadingIntent === 'evaluate' && (
                <div className="samani-chat-row is-assistant">
                  <div className="samani-copilot-reasoning-box">
                    <div className="samani-copilot-reasoning-title">Checking 5-Phase Checklist...</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {[
                        { name: "Historical Risk Profile", micro: "Reading prior utilization..." },
                        { name: "Current Encounter Complexity", micro: "Checking encounter complexity..." },
                        { name: "Labs & Glycemic Review", micro: "Reviewing lab visibility..." },
                        { name: "Medication & Diabetes Regimen", micro: "Reviewing medication context..." },
                        { name: "Discharge Readiness & Care Transition", micro: "Checking discharge destination..." }
                      ].map((p, idx) => {
                        const isCompleted = idx < activePhaseIndex;
                        const isActive = idx === activePhaseIndex;
                        return (
                          <div key={idx} className={`samani-reasoning-step ${isCompleted ? 'is-completed' : ''} ${isActive ? 'is-active' : ''}`}>
                            <span className="samani-reasoning-dot" />
                            <span>
                              {isActive ? p.micro : `Phase ${idx + 1} — ${p.name} ${isCompleted ? '✓' : ''}`}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {chatLoading && chatLoadingIntent === 'generic' && (
                <div className="samani-chat-row is-assistant">
                  <div className="samani-copilot-loading-bubble">
                    <span className="samani-loading-text">
                      Analyzing patient context and generating the clinical response...
                    </span>
                  </div>
                </div>
              )}

              {messages.length > 0 && !chatLoading && (
                <div className="samani-copilot-suggested-title" style={{ marginTop: '16px' }}>Suggested Questions</div>
              )}
              {messages.length > 0 && !chatLoading && (
                <div className="samani-copilot-suggested-chips">
                  {(() => {
                    const latestAssistantMsg = [...messages].reverse().find(m => m.role === 'assistant');
                    const chips = latestAssistantMsg?.result?.follow_up_questions || [
                      "Evaluate discharge readiness",
                      "Why is this patient high risk?",
                      "Review labs",
                      "Review medications",
                      "Summarize diagnoses",
                      "Review follow-up needs"
                    ];
                    return chips.map((q: string, idx: number) => (
                      <button key={idx} type="button" className="samani-copilot-chip" onClick={() => handleSendMessage(q)}>
                        <span>{q}</span>
                      </button>
                    ));
                  })()}
                </div>
              )}
            </div>
          )}
        </div>
        
        <div className={`samani-ai-footer ${aiPrompt.trim() ? 'has-text' : ''}`} style={{ opacity: 1 }}>
          <span>✦</span>
          <input 
            value={aiPrompt}
            onChange={(e) => setAiPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSendMessage(aiPrompt);
              }
            }}
            placeholder="Ask a question about this patient..." 
          />
          <button 
            type="button" 
            onClick={() => handleSendMessage(aiPrompt)}
            aria-label="Send copilot prompt"
          >
            <SvgIcon name="send" />
          </button>
        </div>
      </aside>

      {labReportOpen ? (
        <LabReportModal
          report={labReport}
          reportLabel={reportDisplayName(selectedLabReportEntry)}
          loading={labReportLoading}
          error={labReportError}
          onClose={() => setLabReportOpen(false)}
        />
      ) : null}
    </main>
  );
}

export function ClinicalPortalPage({ view }: { view: PortalView }) {
  const { patientId } = useParams();
  const navigate = useNavigate();
  const [patients, setPatients] = useState<PatientQueueItem[]>([]);
  const [queueLoading, setQueueLoading] = useState(true);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [chart, setChart] = useState<PatientChartResponse | null>(null);
  const [chartLoading, setChartLoading] = useState(view === 'chart');
  const [chartError, setChartError] = useState<string | null>(null);
  
  // Lifted filters state
  const [search, setSearch] = useState('');
  const [risk, setRisk] = useState('all');
  const [gender, setGender] = useState('all');
  const [diagnosis, setDiagnosis] = useState('all');
  const [aiFilters, setAiFilters] = useState<any>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [queueAiMode, setQueueAiMode] = useState(false);

  // Custom timeline appended notes state keyed by patient ID
  const [customNotes, setCustomNotes] = useState<Record<string, Array<{ date: string; note: string; type: string; status: string }>>>({});

  // Refetch when advanced AI filters change
  useEffect(() => {
    let cancelled = false;
    setQueueLoading(true);
    setQueueError(null);

    const params: any = {
      limit: 100,
      offset: 0,
      sort_by: 'calibrated_risk_pct',
      sort_order: 'desc'
    };

    if (aiFilters) {
      Object.assign(params, aiFilters);
    }

    fetchPatients(params)
      .then((response) => { if (!cancelled) setPatients(response.items); })
      .catch((error: Error) => { if (!cancelled) setQueueError(error.message); })
      .finally(() => { if (!cancelled) setQueueLoading(false); });
    return () => { cancelled = true; };
  }, [aiFilters]);

  useEffect(() => {
    if (view !== 'chart' || !patientId) return;
    let cancelled = false;
    setChartLoading(true);
    setChartError(null);
    setChart((current) => current?.patient_id === patientId ? current : null);
    fetchPatientChart(patientId)
      .then((response) => { if (!cancelled) setChart(response); })
      .catch((error: Error) => { if (!cancelled) setChartError(error.message); })
      .finally(() => { if (!cancelled) setChartLoading(false); });
    return () => { cancelled = true; };
  }, [patientId, view]);

  const handleAiSubmit = async (promptText: string) => {
    const submittedPrompt = promptText.trim();
    if (!submittedPrompt) return;
    const loadingStartedAt = performance.now();
    setAiLoading(true);
    try {
      const res = await routeNaturalLanguageQuery(submittedPrompt);
      if (res.route === 'chart' && res.patient_id) {
        // Route to the patient chart and hand the original clinical question to the chart copilot.
        navigate(`/patients/${res.patient_id}`, {
          state: {
            copilotPrompt: submittedPrompt,
            source: 'ai-query',
          },
        });
      } else if (res.route === 'queue') {
        setQueueAiMode(true);
        // Apply filters
        const filters = res.filters || {};
        
        // Sync basic filters to UI state
        if (filters.risk_category) setRisk(filters.risk_category);
        else setRisk('all');
        
        if (filters.gender) setGender(filters.gender);
        else setGender('all');
        
        if (filters.primary_diagnosis_group) setDiagnosis(filters.primary_diagnosis_group);
        else setDiagnosis('all');
        
        if (filters.search) setSearch(filters.search);
        else setSearch(submittedPrompt);

        // Collect advanced filters for server-side SQL matching
        const advanced: any = {};
        if (filters.risk_category !== undefined) advanced.risk_category = filters.risk_category;
        if (filters.gender !== undefined) advanced.gender = filters.gender;
        if (filters.primary_diagnosis_group !== undefined) advanced.primary_diagnosis_group = filters.primary_diagnosis_group;
        if (filters.min_age !== undefined) advanced.min_age = filters.min_age;
        if (filters.max_age !== undefined) advanced.max_age = filters.max_age;
        if (filters.min_time_in_hospital !== undefined) advanced.min_time_in_hospital = filters.min_time_in_hospital;
        if (filters.max_time_in_hospital !== undefined) advanced.max_time_in_hospital = filters.max_time_in_hospital;
        if (filters.duplicate_first_name !== undefined) advanced.duplicate_first_name = filters.duplicate_first_name;
        if (filters.first_name !== undefined) advanced.first_name = filters.first_name;
        if (filters.race !== undefined) advanced.race = filters.race;
        if (filters.primary_physician !== undefined) advanced.primary_physician = filters.primary_physician;
        if (filters.ward_unit !== undefined) advanced.ward_unit = filters.ward_unit;
        if (filters.room_number !== undefined) advanced.room_number = filters.room_number;
        if (filters.has_lab_report !== undefined) advanced.has_lab_report = filters.has_lab_report;
        if (filters.lab_report_type !== undefined) advanced.lab_report_type = filters.lab_report_type;
        if (filters.lab_report_status !== undefined) advanced.lab_report_status = filters.lab_report_status;
        if (filters.lab_report_source_basis !== undefined) advanced.lab_report_source_basis = filters.lab_report_source_basis;
        if (filters.admission_source !== undefined) advanced.admission_source = filters.admission_source;
        if (filters.discharge_destination !== undefined) advanced.discharge_destination = filters.discharge_destination;
        if (filters.min_risk !== undefined) advanced.min_risk = filters.min_risk;
        if (filters.max_risk !== undefined) advanced.max_risk = filters.max_risk;

        setAiFilters(Object.keys(advanced).length > 0 ? advanced : null);
        
        // Route to patient dashboard
        navigate('/queue');
      }
    } catch (err: any) {
      alert(`AI Cognitive Routing failed: ${err.message}`);
    } finally {
      const elapsed = performance.now() - loadingStartedAt;
      if (elapsed < 650) {
        await new Promise((resolve) => setTimeout(resolve, 650 - elapsed));
      }
      setAiLoading(false);
    }
  };

  const chartMatchesRoute = Boolean(patientId && chart?.patient_id === patientId);
  const chartForRoute = chartMatchesRoute ? chart : null;
  const chartLoadingForRoute = chartLoading || (view === 'chart' && Boolean(patientId) && !chartMatchesRoute);

  return (
    <div className="samani-portal">
      <style>{`
        .samani-ai-pills {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 12px;
          margin-bottom: 12px;
          padding: 0 4px;
        }
        .samani-ai-pill {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: rgba(2, 121, 128, 0.08);
          border: 1px solid rgba(2, 121, 128, 0.2);
          color: #027980;
          padding: 4px 10px;
          border-radius: 9999px;
          font-size: 11px;
          font-weight: 600;
        }
        .samani-ai-pill button {
          background: transparent;
          border: none;
          color: #027980;
          cursor: pointer;
          padding: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          opacity: 0.6;
          transition: opacity 0.2s;
        }
        .samani-ai-pill button:hover {
          opacity: 1;
        }
        .samani-chat-input-wrap.is-loading {
          border-color: #027980 !important;
          opacity: 0.75;
          pointer-events: none;
        }

        /* Intro styling */
        .samani-copilot-intro {
          display: flex;
          flex-direction: column;
          gap: 16px;
          color: #374151;
        }
        .samani-copilot-intro-badge {
          align-self: flex-start;
          background: rgba(2, 121, 128, 0.1);
          border: 1px solid rgba(2, 121, 128, 0.3);
          color: #027980;
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          padding: 2px 8px;
          border-radius: 9999px;
        }
        .samani-copilot-intro-text {
          font-size: 13px;
          line-height: 1.5;
          color: #4b5563;
          margin: 0;
        }
        .samani-copilot-phases-preview {
          background: rgba(255, 255, 255, 0.5);
          border: 1px solid rgba(2, 121, 128, 0.15);
          border-radius: 12px;
          padding: 14px;
        }
        .samani-copilot-phases-preview h5 {
          margin: 0 0 10px 0;
          font-size: 12px;
          text-transform: uppercase;
          color: #027980;
          letter-spacing: 0.05em;
          font-weight: 700;
        }
        .samani-copilot-phases-preview ul {
          list-style: none;
          padding: 0;
          margin: 0;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .samani-copilot-phases-preview li {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 12px;
          color: #4b5563;
          font-weight: 550;
        }
        .samani-copilot-phases-preview li span {
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: rgba(2, 121, 128, 0.1);
          color: #027980;
          display: grid;
          place-items: center;
          font-size: 10px;
          font-weight: 700;
        }
        .samani-evaluate-btn {
          width: 100%;
          background: linear-gradient(135deg, #027980 0%, #015459 100%);
          color: white;
          border: none;
          padding: 12px;
          border-radius: 12px;
          font-weight: 600;
          font-size: 13px;
          cursor: pointer;
          transition: transform 0.2s, box-shadow 0.2s;
          box-shadow: 0 4px 12px rgba(2, 121, 128, 0.2);
        }
        .samani-evaluate-btn:hover {
          transform: translateY(-1px);
          box-shadow: 0 6px 16px rgba(2, 121, 128, 0.3);
        }

        /* Chat bubble styling */
        .samani-chat-bubble-user {
          position: relative;
          overflow: hidden;
          align-self: flex-end;
          background:
            radial-gradient(circle at 92% 12%, rgba(255, 255, 255, 0.18), transparent 34%),
            linear-gradient(135deg, rgba(2, 121, 128, 0.96), rgba(1, 97, 104, 0.9));
          color: #ffffff;
          padding: 11px 14px 12px;
          border: 1px solid rgba(255, 255, 255, 0.24);
          border-radius: 15px 15px 5px 15px;
          font-size: 12.5px;
          font-weight: 760;
          line-height: 1.24;
          max-width: min(82%, 270px);
          box-shadow:
            0 12px 26px rgba(2, 121, 128, 0.16),
            inset 0 1px 0 rgba(255, 255, 255, 0.16);
          margin-bottom: 8px;
          animation: samani-user-bubble-in 0.3s cubic-bezier(0.2, 0.8, 0.2, 1) both;
        }
        .samani-chat-bubble-user::after {
          content: "";
          position: absolute;
          inset: 0;
          background: linear-gradient(110deg, transparent, rgba(255, 255, 255, 0.12), transparent);
          transform: translateX(-120%);
          animation: samani-thinking-sheen 2.4s ease-in-out 0.15s 1;
          pointer-events: none;
        }

        /* Reasoning loading timeline */
        .samani-copilot-reasoning-box {
          position: relative;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          gap: 12px;
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.72), rgba(239, 252, 252, 0.44));
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border: 1px solid rgba(2, 121, 128, 0.12);
          border-radius: 16px;
          padding: 16px;
          color: #374151;
          width: 100%;
          box-shadow: 0 12px 32px rgba(2, 121, 128, 0.045);
          animation: samani-response-reveal 0.42s ease both;
        }
        .samani-copilot-reasoning-box::before {
          content: "";
          position: absolute;
          inset: 0;
          background: linear-gradient(110deg, transparent 0%, rgba(255, 255, 255, 0.62) 42%, transparent 74%);
          transform: translateX(-100%);
          animation: samani-thinking-sheen 1.8s ease-in-out infinite;
          pointer-events: none;
        }
        .samani-copilot-reasoning-title {
          font-size: 12px;
          text-transform: uppercase;
          color: #027980;
          font-weight: 700;
          letter-spacing: 0.05em;
          margin-bottom: 4px;
        }
        .samani-reasoning-step {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 12.5px;
          color: #9ca3af;
          transition: color 0.3s, transform 0.3s, opacity 0.3s;
          opacity: 0.78;
        }
        .samani-reasoning-step.is-active {
          color: #027980;
          font-weight: 600;
          opacity: 1;
          transform: translateX(2px);
          animation: pulse-shimmer 1.5s infinite alternate;
        }
        .samani-reasoning-step.is-completed {
          color: #059669;
          opacity: 1;
        }
        .samani-reasoning-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #d1d5db;
          transition: background 0.3s, transform 0.3s;
        }
        .samani-reasoning-step.is-active .samani-reasoning-dot {
          background: #027980;
          transform: scale(1.3);
        }
        .samani-reasoning-step.is-completed .samani-reasoning-dot {
          background: #059669;
        }

        @keyframes pulse-shimmer {
          0% { opacity: 0.6; }
          100% { opacity: 1; }
        }

        /* Completed results rendering */
        .samani-copilot-response {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .samani-copilot-response-evaluate,
        .samani-copilot-response-gemini,
        .samani-copilot-response-generic {
          animation: samani-response-reveal 0.48s cubic-bezier(0.2, 0.8, 0.2, 1) both;
          transform-origin: top center;
        }
        .samani-copilot-response-evaluate .samani-overall-assessment-card {
          animation: samani-response-reveal 0.46s cubic-bezier(0.2, 0.8, 0.2, 1) both;
        }
        .samani-copilot-response-evaluate .samani-copilot-phase-card {
          animation: samani-response-reveal 0.5s cubic-bezier(0.2, 0.8, 0.2, 1) both;
        }
        .samani-copilot-response-evaluate .samani-copilot-phase-card:nth-child(1) { animation-delay: 0.04s; }
        .samani-copilot-response-evaluate .samani-copilot-phase-card:nth-child(2) { animation-delay: 0.08s; }
        .samani-copilot-response-evaluate .samani-copilot-phase-card:nth-child(3) { animation-delay: 0.12s; }
        .samani-copilot-response-evaluate .samani-copilot-phase-card:nth-child(4) { animation-delay: 0.16s; }
        .samani-copilot-response-evaluate .samani-copilot-phase-card:nth-child(5) { animation-delay: 0.2s; }
        .samani-overall-assessment-card {
          position: relative;
          overflow: hidden;
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.78), rgba(247, 252, 252, 0.52));
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border: 1px solid rgba(2, 121, 128, 0.12);
          border-radius: 12px;
          padding: 14px;
          margin-bottom: 12px;
          box-shadow: 0 10px 28px rgba(15, 23, 42, 0.035);
          color: #1f2937;
        }
        .samani-overall-assessment-card::before {
          content: "";
          position: absolute;
          inset: 0;
          pointer-events: none;
          background: radial-gradient(circle at 92% 12%, rgba(2, 121, 128, 0.1), transparent 34%);
        }
        .samani-overall-assessment-card.has-concern {
          border-color: rgba(244, 63, 94, 0.16);
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.82), rgba(255, 247, 249, 0.56));
        }
        .samani-overall-assessment-card.has-review {
          border-color: rgba(245, 158, 11, 0.18);
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.82), rgba(255, 251, 235, 0.56));
        }
        .samani-overall-assessment-card.has-clear {
          border-color: rgba(16, 185, 129, 0.16);
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.82), rgba(236, 253, 245, 0.48));
        }
        .samani-overall-assessment-card h5 {
          position: relative;
          margin: 0 0 8px 0;
          font-size: 13px;
          font-weight: 800;
          color: #015459;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .samani-overall-assessment-card p {
          position: relative;
          margin: 0;
          font-size: 13px;
          line-height: 1.45;
          color: #374151;
        }

        /* Phase findings accordion */
        .samani-copilot-phase-card {
          isolation: isolate;
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border: 1px solid rgba(2, 121, 128, 0.1);
          border-radius: 14px;
          overflow: hidden;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 8px 22px rgba(15, 23, 42, 0.026);
          position: relative;
          margin-bottom: 10px;
        }
        .samani-copilot-phase-card::before {
          content: "";
          position: absolute;
          inset: 0;
          z-index: -1;
          opacity: 0.9;
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.82), rgba(247, 252, 252, 0.42));
        }
        .samani-copilot-phase-card:hover {
          transform: translateY(-1px);
          box-shadow: 0 8px 24px rgba(2, 121, 128, 0.06);
        }

        /* Glassmorphic card backgrounds with soft status gradients */
        .samani-copilot-phase-card.has-concern {
          border-color: rgba(244, 63, 94, 0.14);
        }
        .samani-copilot-phase-card.has-concern::before {
          background:
            radial-gradient(circle at 94% 18%, rgba(244, 63, 94, 0.09), transparent 32%),
            linear-gradient(135deg, rgba(255, 255, 255, 0.84), rgba(255, 247, 249, 0.46));
        }
        .samani-copilot-phase-card.has-concern:hover {
          border-color: rgba(244, 63, 94, 0.22);
          box-shadow: 0 10px 26px rgba(244, 63, 94, 0.055);
        }

        .samani-copilot-phase-card.has-review {
          border-color: rgba(245, 158, 11, 0.15);
        }
        .samani-copilot-phase-card.has-review::before {
          background:
            radial-gradient(circle at 94% 18%, rgba(245, 158, 11, 0.09), transparent 32%),
            linear-gradient(135deg, rgba(255, 255, 255, 0.84), rgba(255, 251, 235, 0.46));
        }
        .samani-copilot-phase-card.has-review:hover {
          border-color: rgba(245, 158, 11, 0.24);
          box-shadow: 0 10px 26px rgba(245, 158, 11, 0.055);
        }

        .samani-copilot-phase-card.has-clear {
          border-color: rgba(16, 185, 129, 0.14);
        }
        .samani-copilot-phase-card.has-clear::before {
          background:
            radial-gradient(circle at 94% 18%, rgba(16, 185, 129, 0.08), transparent 32%),
            linear-gradient(135deg, rgba(255, 255, 255, 0.84), rgba(236, 253, 245, 0.4));
        }
        .samani-copilot-phase-card.has-clear:hover {
          border-color: rgba(16, 185, 129, 0.22);
          box-shadow: 0 10px 26px rgba(16, 185, 129, 0.05);
        }

        .samani-copilot-phase-header {
          padding: 13px 14px 10px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          cursor: pointer;
          user-select: none;
          background: transparent;
        }
        .samani-copilot-phase-header:hover {
          background: rgba(255, 255, 255, 0.22);
        }
        .samani-copilot-phase-title {
          min-width: 0;
          font-size: 12.5px;
          font-weight: 800;
          color: #1f2937;
          display: flex;
          align-items: center;
          gap: 10px;
          line-height: 1.18;
        }

        /* Color-coded index circle matching card status */
        .samani-copilot-phase-title span {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 22px;
          height: 22px;
          border-radius: 50%;
          font-size: 11px;
          font-weight: 700;
          transition: all 0.2s ease;
          flex: 0 0 auto;
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
        }
        .samani-copilot-phase-card.has-concern .samani-copilot-phase-title span {
          background: rgba(244, 63, 94, 0.12);
          color: #e11d48;
          border: 1px solid rgba(244, 63, 94, 0.25);
        }
        .samani-copilot-phase-card.has-review .samani-copilot-phase-title span {
          background: rgba(245, 158, 11, 0.12);
          color: #d97706;
          border: 1px solid rgba(245, 158, 11, 0.25);
        }
        .samani-copilot-phase-card.has-clear .samani-copilot-phase-title span {
          background: rgba(16, 185, 129, 0.12);
          color: #059669;
          border: 1px solid rgba(16, 185, 129, 0.25);
        }

        .samani-copilot-phase-badge {
          font-size: 9px;
          font-weight: 850;
          text-transform: uppercase;
          padding: 2px 8px;
          border-radius: 9999px;
          letter-spacing: 0.04em;
          backdrop-filter: blur(4px);
          -webkit-backdrop-filter: blur(4px);
        }
        .samani-copilot-phase-badge.concern {
          background: rgba(244, 63, 94, 0.12);
          color: #e11d48;
          border: 1px solid rgba(244, 63, 94, 0.2);
        }
        .samani-copilot-phase-badge.review {
          background: rgba(245, 158, 11, 0.12);
          color: #d97706;
          border: 1px solid rgba(245, 158, 11, 0.2);
        }
        .samani-copilot-phase-badge.clear {
          background: rgba(16, 185, 129, 0.12);
          color: #059669;
          border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .samani-copilot-phase-content-shell {
          display: grid;
          grid-template-rows: 0fr;
          opacity: 0;
          overflow: hidden;
          transform: translateY(-6px);
          transition:
            grid-template-rows 0.42s cubic-bezier(0.2, 0.8, 0.2, 1),
            opacity 0.28s ease,
            transform 0.34s ease;
        }
        .samani-copilot-phase-content-shell.is-expanded {
          grid-template-rows: 1fr;
          opacity: 1;
          transform: translateY(0);
        }
        .samani-copilot-phase-content {
          min-height: 0;
          overflow: hidden;
          padding: 0 14px 14px;
          border-top: 1px solid rgba(229, 231, 235, 0.34);
          background: rgba(255, 255, 255, 0.18);
          display: flex;
          flex-direction: column;
          gap: 10px;
          transition: padding 0.32s ease, border-color 0.32s ease;
        }
        .samani-copilot-phase-content-shell:not(.is-expanded) .samani-copilot-phase-content {
          padding-top: 0;
          padding-bottom: 0;
          border-top-color: transparent;
        }
        .samani-copilot-section-title {
          font-size: 10.5px;
          font-weight: 700;
          text-transform: uppercase;
          color: #6b7280;
          letter-spacing: 0.03em;
          margin: 0 0 4px 0;
        }
        .samani-copilot-evidence-list {
          list-style: none;
          padding: 0;
          margin: 6px 0 0 0;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .samani-copilot-evidence-list li {
          font-size: 12px;
          color: #4b5563;
          display: flex;
          align-items: flex-start;
          gap: 6px;
          line-height: 1.4;
        }
        .samani-copilot-evidence-list li::before {
          content: "";
          width: 5px;
          height: 5px;
          border-radius: 999px;
          background: #027980;
          color: #027980;
          font-weight: bold;
          font-size: 14px;
          line-height: 1;
          margin-top: 6px;
          flex: 0 0 auto;
        }
        .samani-copilot-shap-list {
          list-style: none;
          padding: 0;
          margin: 0;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .samani-copilot-shap-list li {
          font-size: 11px;
          color: #4b5563;
          line-height: 1.35;
        }
        .samani-copilot-note-text {
          font-size: 12px;
          font-weight: 550;
          line-height: 1.4;
          margin: 0;
          padding: 10px 12px;
          border-radius: 10px;
          color: #374151;
        }
        .samani-copilot-note-shell {
          padding: 0 14px 12px;
        }
        .samani-copilot-phase-card.has-concern .samani-copilot-note-text {
          background: rgba(255, 255, 255, 0.48);
          color: #5f2432;
          border: 1px solid rgba(244, 63, 94, 0.11);
        }
        .samani-copilot-phase-card.has-review .samani-copilot-note-text {
          background: rgba(255, 255, 255, 0.48);
          color: #65420d;
          border: 1px solid rgba(245, 158, 11, 0.12);
        }
        .samani-copilot-phase-card.has-clear .samani-copilot-note-text {
          background: rgba(255, 255, 255, 0.48);
          color: #145044;
          border: 1px solid rgba(16, 185, 129, 0.11);
        }

        .samani-copilot-tech-accordion {
          margin-top: 12px;
          overflow: hidden;
          border: 1px solid rgba(2, 121, 128, 0.1);
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.42);
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62);
          animation: samani-evidence-card-in 0.32s cubic-bezier(0.2, 0.8, 0.2, 1) both;
          transform-origin: top center;
        }
        .samani-copilot-tech-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          min-height: 38px;
          padding: 8px 10px 8px 12px;
          cursor: pointer;
          color: #4b5563;
          transition: background 0.2s ease, color 0.2s ease;
        }
        .samani-copilot-tech-header:hover {
          background: rgba(2, 121, 128, 0.035);
          color: #027980;
        }
        .samani-copilot-tech-header span {
          display: flex;
          min-width: 0;
          flex-direction: column;
          gap: 1px;
        }
        .samani-copilot-tech-header strong {
          color: #374151;
          font-size: 11px;
          font-weight: 800;
          line-height: 1.1;
        }
        .samani-copilot-tech-header small {
          color: #9ca3af;
          font-size: 9px;
          font-weight: 800;
          line-height: 1.1;
          text-transform: uppercase;
        }
        .samani-copilot-tech-header i {
          flex: 0 0 auto;
          padding: 4px 8px;
          border: 1px solid rgba(2, 121, 128, 0.12);
          border-radius: 999px;
          background: rgba(247, 252, 252, 0.72);
          color: #027980;
          font-size: 10px;
          font-style: normal;
          font-weight: 800;
          transition: transform 0.2s ease, background 0.2s ease, border-color 0.2s ease;
        }
        .samani-copilot-tech-header:hover i {
          transform: translateY(-1px);
          background: rgba(235, 248, 248, 0.88);
          border-color: rgba(2, 121, 128, 0.24);
        }
        .samani-copilot-tech-content {
          padding: 10px 12px 12px;
          border-top: 1px solid rgba(229, 231, 235, 0.34);
          background: rgba(255, 255, 255, 0.5);
          color: #4b5563;
          font-size: 11px;
          animation: samani-evidence-open 0.34s cubic-bezier(0.2, 0.8, 0.2, 1) both;
          transform-origin: top center;
        }

        /* Key reviews styling */
        .samani-key-reviews-card {
          background: rgba(255, 255, 255, 0.85);
          border: 1px solid rgba(2, 121, 128, 0.15);
          border-radius: 14px;
          padding: 14px;
          color: #374151;
        }
        .samani-key-reviews-card h5 {
          margin: 0 0 10px 0;
          font-size: 13px;
          font-weight: 700;
          color: #015459;
          text-transform: uppercase;
          letter-spacing: 0.03em;
        }
        .samani-key-reviews-card ul {
          padding-left: 18px;
          margin: 0;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .samani-key-reviews-card li {
          font-size: 12px;
          line-height: 1.4;
          color: #374151;
          font-weight: 550;
        }

        /* Limitations */
        .samani-copilot-limitations {
          font-size: 11px;
          line-height: 1.45;
          color: #6b7280;
          padding: 12px;
          background: rgba(255, 255, 255, 0.2);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          border-radius: 10px;
          border: 1px solid rgba(255, 255, 255, 0.35);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.01);
        }
        .samani-copilot-limitations h6 {
          margin: 0 0 4px 0;
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          color: #4b5563;
        }
        .samani-copilot-limitations ul {
          padding-left: 14px;
          margin: 0;
        }
        .samani-copilot-limitations li {
          margin-bottom: 2px;
        }

        /* Suggested Prompt Chips */
        .samani-copilot-suggested-title {
          position: relative;
          font-size: 10.5px;
          text-transform: uppercase;
          color: #027980;
          font-weight: 850;
          letter-spacing: 0.08em;
          margin-top: 18px;
          margin-bottom: 9px;
          animation: samani-response-reveal 0.38s ease both;
        }
        .samani-copilot-suggested-chips {
          display: grid;
          grid-template-columns: 1fr;
          gap: 7px;
          margin-bottom: 8px;
          animation: samani-response-reveal 0.42s ease both;
        }
        .samani-copilot-chip {
          width: 100%;
          min-height: 34px;
          max-height: 46px;
          display: flex;
          align-items: center;
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.62), rgba(239, 252, 252, 0.36));
          border: 1px solid rgba(2, 121, 128, 0.16);
          color: #027980;
          font-size: 11.25px;
          font-weight: 750;
          padding: 7px 11px;
          border-radius: 13px;
          cursor: pointer;
          transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
          text-align: left;
          box-shadow: 0 6px 18px rgba(2, 121, 128, 0.026);
        }
        .samani-copilot-chip span {
          display: -webkit-box;
          overflow: hidden;
          -webkit-box-orient: vertical;
          -webkit-line-clamp: 2;
          line-height: 1.25;
        }
        .samani-copilot-chip:hover {
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.84), rgba(229, 247, 247, 0.58));
          border-color: rgba(2, 121, 128, 0.26);
          box-shadow: 0 10px 24px rgba(2, 121, 128, 0.055);
          transform: translateY(-1px) scale(1.004);
        }

        /* Chat bubbles & generic response styles */
        .samani-copilot-chat-history {
          display: flex;
          flex-direction: column;
          gap: 16px;
          overflow-y: auto;
          flex-grow: 1;
        }
        .samani-chat-row {
          display: flex;
          flex-direction: column;
          width: 100%;
        }
        .samani-chat-row--fresh {
          scroll-margin-top: 14px;
        }
        .samani-chat-row.is-user {
          align-items: flex-end;
        }
        .samani-chat-row.is-assistant {
          align-items: flex-start;
        }
        .samani-chat-bubble-assistant {
          align-self: flex-start;
          background: transparent;
          border: none;
          border-radius: 0;
          padding: 4px 0 12px 0;
          font-size: 13.5px;
          color: #1f2937;
          width: 100%;
          box-shadow: none;
          display: flex;
          flex-direction: column;
          gap: 10px;
          animation: samani-response-reveal 0.42s cubic-bezier(0.2, 0.8, 0.2, 1) both;
        }
        .samani-chat-text-response {
          font-size: 13.5px;
          line-height: 1.5;
          color: #374151;
        }
        .samani-copilot-generic-answer {
          margin: 0;
          line-height: 1.5;
        }
        .samani-copilot-evidence-box,
        .samani-copilot-shap-box,
        .samani-copilot-related-phases {
          background: rgba(255, 255, 255, 0.4);
          border: 1px solid rgba(229, 231, 235, 0.6);
          border-radius: 12px;
          padding: 10px 12px;
        }
        .samani-copilot-phase-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 4px;
        }
        .samani-copilot-phase-tag {
          font-size: 10px;
          font-weight: 700;
          background: rgba(2, 121, 128, 0.08);
          color: #015459;
          padding: 2px 6px;
          border-radius: 4px;
        }

        /* Loading bubble */
        .samani-copilot-loading-bubble {
          position: relative;
          overflow: hidden;
          width: 100%;
          min-height: 54px;
          display: inline-flex;
          align-items: center;
          justify-content: flex-start;
          background: transparent;
          backdrop-filter: none;
          -webkit-backdrop-filter: none;
          border: 0;
          border-radius: 0;
          padding: 8px 4px 10px;
          box-shadow: none;
          animation: samani-response-reveal 0.36s ease both;
        }
        .samani-copilot-loading-bubble::before {
          display: none;
        }
        .samani-loading-text {
          position: relative;
          display: block;
          max-width: 300px;
          color: transparent;
          background: linear-gradient(100deg, #5f6f75 0%, #027980 34%, #2aa5a4 52%, #5f6f75 76%);
          background-size: 220% 100%;
          -webkit-background-clip: text;
          background-clip: text;
          font-size: 13.5px;
          font-weight: 820;
          letter-spacing: 0;
          line-height: 1.42;
          text-wrap: balance;
          animation:
            samani-loading-text-flow 2.8s ease-in-out infinite,
            samani-thinking-gradient 4.2s ease-in-out infinite;
        }
        .samani-loading-text::after {
          content: "";
          position: absolute;
          left: 0;
          bottom: -8px;
          width: min(150px, 54%);
          height: 1px;
          border-radius: 999px;
          background: linear-gradient(90deg, rgba(2, 121, 128, 0), rgba(2, 121, 128, 0.24), rgba(95, 198, 188, 0));
          transform-origin: center;
          animation: samani-loading-underline 2.8s ease-in-out infinite;
        }
        @keyframes samani-bounce {
          0%, 80%, 100% {
            transform: scale(0);
          }
          40% {
            transform: scale(1.0);
          }
        }
        @keyframes samani-response-reveal {
          from {
            opacity: 0;
            transform: translateY(-10px) scale(0.985);
            clip-path: inset(0 0 18% 0 round 12px);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
            clip-path: inset(0 0 0 0 round 12px);
          }
        }
        @keyframes samani-thinking-sheen {
          0% { transform: translateX(-115%); opacity: 0; }
          18% { opacity: 1; }
          58% { opacity: 0.72; }
          100% { transform: translateX(115%); opacity: 0; }
        }
        @keyframes samani-user-bubble-in {
          from {
            opacity: 0;
            transform: translateY(8px) scale(0.98);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        @keyframes samani-evidence-card-in {
          from {
            opacity: 0;
            transform: translateY(-5px) scale(0.99);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        @keyframes samani-evidence-open {
          from {
            opacity: 0;
            transform: translateY(-8px);
            clip-path: inset(0 0 28% 0 round 10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
            clip-path: inset(0 0 0 0 round 10px);
          }
        }
        @keyframes samani-loading-text-flow {
          0%, 100% {
            opacity: 0.72;
            transform: translateY(0);
            filter: blur(0);
          }
          50% {
            opacity: 0.96;
            transform: translateY(-0.5px);
            filter: blur(0.04px);
          }
        }
        @keyframes samani-thinking-gradient {
          0% {
            background-position: 0% 50%;
          }
          50% {
            background-position: 100% 50%;
          }
          100% {
            background-position: 0% 50%;
          }
        }
        @keyframes samani-loading-underline {
          0%, 100% {
            transform: scaleX(0.22);
            opacity: 0.2;
          }
          50% {
            transform: scaleX(1);
            opacity: 0.72;
          }
        }

      `}</style>
      <AntigravityCanvas />
      <div className="samani-glow" />
      <div className="dot-grid" />
      <PortalNav view={view} activePatientId={patientId} />
      <PortalHeader />
      <div className={`samani-content samani-content--${view}`}>
        <HomeConsole active={view === 'home'} onSubmit={handleAiSubmit} loading={aiLoading} />
        <PatientListDashboard 
          active={view === 'queue'} 
          patients={patients} 
          loading={queueLoading} 
          error={queueError}
          search={search}
          setSearch={setSearch}
          risk={risk}
          setRisk={setRisk}
          gender={gender}
          setGender={setGender}
          diagnosis={diagnosis}
          setDiagnosis={setDiagnosis}
          aiMode={queueAiMode}
          setAiMode={setQueueAiMode}
          aiFilters={aiFilters}
          setAiFilters={setAiFilters}
          onAiSubmit={handleAiSubmit}
          aiLoading={aiLoading}
        />
        <PatientChartPortal 
          active={view === 'chart'} 
          chart={chartForRoute} 
          loading={chartLoadingForRoute} 
          error={chartError}
          customNotes={chartForRoute && chartForRoute.patient_id ? (customNotes[chartForRoute.patient_id] || []) : []}
          onAddCustomNote={(text) => {
            if (chartForRoute && chartForRoute.patient_id) {
              const activeChartId = chartForRoute.patient_id;
              const today = new Date().toISOString().slice(0, 10);
              const newNote = {
                date: today,
                note: text,
                type: 'Copilot Feed',
                status: 'Appended'
              };
              setCustomNotes(prev => ({
                ...prev,
                [activeChartId]: [newNote, ...(prev[activeChartId] || [])]
              }));
            }
          }}
        />
      </div>
      <footer className="samani-footer">Interactive background is reacting dynamically in wave fronts centered on your cursor.</footer>
    </div>
  );
}
