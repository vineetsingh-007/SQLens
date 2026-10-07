import React from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { ThemeProvider } from '../../context/ThemeContext';

export const MainLayout: React.FC = () => {
  return (
    <ThemeProvider>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans transition-colors duration-200">
        <Navbar />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar />
          <main className="flex-1 p-5 md:p-6 lg:p-7 max-w-[1536px] mx-auto w-full overflow-y-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </ThemeProvider>
  );
};
