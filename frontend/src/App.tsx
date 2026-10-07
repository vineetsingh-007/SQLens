import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './components/layout/MainLayout';
import { Home } from './pages/Home';
import { UploadPage } from './pages/UploadPage';
import { DatasetListPage } from './pages/DatasetListPage';
import { DatasetDetailPage } from './pages/DatasetDetailPage';
import { QueryHistoryPage } from './pages/QueryHistoryPage';
import { DemoPage } from './pages/DemoPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Home />} />
          <Route path="dashboard" element={<Home />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="datasets" element={<DatasetListPage />} />
          <Route path="datasets/:datasetId" element={<DatasetDetailPage />} />
          <Route path="history" element={<QueryHistoryPage />} />
          <Route path="demo" element={<DemoPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
