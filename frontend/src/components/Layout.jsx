import { Link, useLocation } from 'react-router-dom';

export default function Layout({ children }) {
  const { pathname } = useLocation();

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-icon">⇄</span>
          <div>
            <strong>Migration Utility</strong>
            <small>Extract · Validate · Transform · Load</small>
          </div>
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
