import { Link, useLocation } from 'react-router-dom';
import BrandLogo from './BrandLogo';

export default function Layout({ children }) {
  const { pathname } = useLocation();
  const isProject = pathname.startsWith('/projects/');

  if (isProject) {
    return <div className="app-shell project-route">{children}</div>;
  }

  return (
    <div className="app-shell">
      <header className="topbar dashboard-topbar">
        <Link to="/" className="brand">
          <BrandLogo size={48} subtitle="Extract · Validate · Transform · Load" />
        </Link>
        <nav className="topnav">
          <Link to="/" className={pathname === '/' ? 'active' : ''}>
            Projects
          </Link>
        </nav>
      </header>
      <main className="main-content">{children}</main>
    </div>
  );
}

function StatusBadge({ status }) {
  const cls = ['badge', status].join(' ');
  return <span className={cls}>{status}</span>;
}

export { StatusBadge };
