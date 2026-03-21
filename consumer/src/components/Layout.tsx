import { Link } from "react-router-dom";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="layout">
      <div className="navbar">
        <h1>ETL Pipeline</h1>
        <nav>
          <Link to="/setup">Setup</Link>
          <Link to="/dashboard">Dashboard</Link>
        </nav>
      </div>
      {children}
    </div>
  );
}
