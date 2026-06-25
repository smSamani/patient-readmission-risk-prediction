import { Link } from 'react-router-dom';

type WorkspaceChromeSection = 'home' | 'queue' | 'chart';

interface WorkspaceChromeProps {
  active: WorkspaceChromeSection;
  chartPath?: string;
}

function ChromeIcon({ name }: { name: WorkspaceChromeSection }) {
  const common = { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', xmlns: 'http://www.w3.org/2000/svg', 'aria-hidden': true };
  const stroke = { stroke: 'currentColor', strokeWidth: 2.3, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };

  if (name === 'home') {
    return <svg {...common}><path {...stroke} d="m4 11 8-7 8 7" /><path {...stroke} d="M6 10v10h12V10" /><path {...stroke} d="M10 20v-6h4v6" /></svg>;
  }

  if (name === 'chart') {
    return <svg {...common}><path {...stroke} d="M4 7a2 2 0 0 1 2-2h5l2 2h5a2 2 0 0 1 2 2v10H4z" /><path {...stroke} d="M4 11h16" /></svg>;
  }

  return <svg {...common}><path {...stroke} d="M8 6h12" /><path {...stroke} d="M8 12h12" /><path {...stroke} d="M8 18h12" /><path {...stroke} d="M4 6h.01" /><path {...stroke} d="M4 12h.01" /><path {...stroke} d="M4 18h.01" /></svg>;
}

export function WorkspaceChrome({ active, chartPath }: WorkspaceChromeProps) {
  return (
    <div className="reference-app-chrome" aria-label="Clinical workspace navigation">
      <Link className="reference-portal-link" to="/" aria-label="Samani portal queue">
        <span aria-hidden="true">-&gt;</span>
        Samani Portal
      </Link>

      <nav className="reference-floating-nav" aria-label="Workspace views">
        <Link className={active === 'home' ? 'is-active' : ''} to="/" aria-label="Home">
          <ChromeIcon name="home" />
        </Link>
        <Link className={active === 'queue' ? 'is-active' : ''} to="/" aria-label="Patient queue">
          <ChromeIcon name="queue" />
        </Link>
        <Link className={active === 'chart' ? 'is-active' : ''} to={chartPath ?? '/'} aria-label="Patient chart">
          <ChromeIcon name="chart" />
        </Link>
      </nav>

      <span className="reference-workspace-badge">Clinical Workspace</span>
    </div>
  );
}
