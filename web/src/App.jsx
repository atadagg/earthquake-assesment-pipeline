import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import DBBrowser from './pages/DBBrowser';
import URLTester from './pages/URLTester';
import DetectorTester from './pages/DetectorTester';
import Validation from './pages/Validation';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/db-browser" element={<DBBrowser />} />
            <Route path="/url-tester" element={<URLTester />} />
            <Route path="/detector" element={<DetectorTester />} />
            <Route path="/validation" element={<Validation />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
