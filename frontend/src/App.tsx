import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { GeneratePage } from './pages/GeneratePage';
import { PodcastPage } from './pages/PodcastPage';
import { PodcastsLibraryPage } from './pages/PodcastsLibraryPage';
import { VoicesPage } from './pages/VoicesPage';
import { SettingsPage } from './pages/SettingsPage';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/generate" replace />} />
          <Route path="/generate" element={<GeneratePage />} />
          <Route path="/podcast" element={<PodcastPage />} />
          <Route path="/podcasts" element={<PodcastsLibraryPage />} />
          <Route path="/voices" element={<VoicesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;