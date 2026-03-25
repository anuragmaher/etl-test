import { Link } from "react-router-dom";

interface Props {
  children: React.ReactNode;
  wide?: boolean;
}

export default function Layout({ children, wide }: Props) {
  return (
    <div className={wide ? "layout layout-wide" : "layout"}>
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
