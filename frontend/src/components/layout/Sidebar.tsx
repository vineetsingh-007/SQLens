import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  History,
  Sparkles,
  Settings,
  Sun,
  Moon,
  User,
  ChevronLeft,
  ChevronRight,
  UserCheck
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

export const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    return localStorage.getItem('sqlens_sidebar_collapsed') === 'true';
  });

  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState<boolean>(false);
  const profileRef = useRef<HTMLDivElement>(null);

  const toggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('sqlens_sidebar_collapsed', next.toString());
      return next;
    });
  };

  // Close profile popup when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setIsProfileMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/datasets', label: 'My Datasets', icon: Database },
    { to: '/history', label: 'Query History', icon: History },
    { to: '/demo', label: 'Demo', icon: Sparkles }
  ];

  return (
    <aside
      className={`hidden md:flex flex-col justify-between border-r border-slate-800/80 bg-slate-950/80 dark:bg-slate-950/90 backdrop-blur-xl transition-all duration-300 relative z-20 shrink-0 min-h-[calc(100vh-4rem)] ${
        isCollapsed ? 'w-20 p-3' : 'w-64 lg:w-70 p-4.5'
      }`}
    >
      <div className="space-y-6">
        {/* Collapse Toggle Control */}
        <div className="flex items-center justify-between px-2">
          {!isCollapsed && (
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 font-sans">
              Navigation
            </span>
          )}
          <button
            type="button"
            onClick={toggleCollapse}
            className={`p-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 transition-all cursor-pointer ${
              isCollapsed ? 'mx-auto' : ''
            }`}
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                title={isCollapsed ? item.label : undefined}
                className={({ isActive }) =>
                  `flex items-center space-x-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 group relative ${
                    isActive
                      ? 'bg-slate-800 dark:bg-[#414141] text-slate-900 dark:text-[#F2F2F2] border border-slate-300 dark:border-[#555555] font-semibold'
                      : 'text-slate-400 dark:text-[#C7C7C7] hover:text-slate-900 dark:hover:text-[#F2F2F2] hover:bg-slate-100 dark:hover:bg-[#333333] border border-transparent'
                  } ${isCollapsed ? 'justify-center px-0' : ''}`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon className={`w-4.5 h-4.5 shrink-0 transition-transform group-hover:scale-110 ${isActive ? 'text-brand-600 dark:text-[#8AB4F8]' : 'text-slate-400 dark:text-[#B8B8B8]'}`} />
                    {!isCollapsed && <span>{item.label}</span>}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Bottom Controls Area */}
      <div className="space-y-2 pt-4 border-t border-slate-800/80" ref={profileRef}>
        {/* Settings Option */}
        <NavLink
          to="/settings"
          title={isCollapsed ? 'Settings' : undefined}
          className={({ isActive }) =>
            `flex items-center space-x-3.5 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
              isActive
                ? 'bg-slate-900 text-indigo-400 border border-slate-700 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80 border border-transparent'
            } ${isCollapsed ? 'justify-center px-0' : ''}`
          }
        >
          <Settings className="w-4.5 h-4.5 shrink-0" />
          {!isCollapsed && <span>Settings</span>}
        </NavLink>

        {/* Light / Dark Theme Toggle Button */}
        <button
          type="button"
          onClick={toggleTheme}
          title={isCollapsed ? `Theme: ${theme === 'dark' ? 'Dark' : 'Light'}` : undefined}
          className={`w-full flex items-center space-x-3.5 px-4 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-900/80 transition-all cursor-pointer border border-transparent ${
            isCollapsed ? 'justify-center px-0' : ''
          }`}
        >
          {theme === 'dark' ? (
            <Moon className="w-4.5 h-4.5 text-indigo-400 shrink-0" />
          ) : (
            <Sun className="w-4.5 h-4.5 text-amber-400 shrink-0" />
          )}
          {!isCollapsed && (
            <div className="flex items-center justify-between w-full">
              <span>Theme</span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-900 border border-slate-800 text-slate-400 capitalize font-medium">
                {theme}
              </span>
            </div>
          )}
        </button>

        {/* Profile Card & Popup */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setIsProfileMenuOpen((prev) => !prev)}
            className={`w-full flex items-center space-x-3 p-2.5 rounded-xl bg-slate-900/60 hover:bg-slate-900 border border-slate-800/80 transition-all cursor-pointer text-left ${
              isCollapsed ? 'justify-center p-2' : ''
            }`}
            title="User Profile"
          >
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-indigo-600 to-sky-400 flex items-center justify-center text-white shrink-0 shadow-md">
              <User className="w-4.5 h-4.5" />
            </div>

            {!isCollapsed && (
              <div className="overflow-hidden">
                <div className="text-sm font-semibold text-slate-200 truncate">User</div>
                <div className="text-xs text-slate-400 truncate">Profile</div>
              </div>
            )}
          </button>

          {/* Profile Popup Menu */}
          {isProfileMenuOpen && (
            <div
              className={`absolute bottom-12 z-50 w-48 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-1.5 space-y-1 animate-in fade-in zoom-in-95 duration-150 ${
                isCollapsed ? 'left-14' : 'left-0'
              }`}
            >
              <div className="px-3 py-2 border-b border-slate-800 text-xs">
                <div className="font-semibold text-slate-200 flex items-center gap-1.5">
                  <UserCheck className="w-3.5 h-3.5 text-indigo-400" />
                  <span>User Profile</span>
                </div>
                <div className="text-[10px] text-slate-400">Neutral Session</div>
              </div>

              <button
                onClick={() => {
                  setIsProfileMenuOpen(false);
                  navigate('/settings');
                }}
                className="w-full text-left px-3 py-2 rounded-xl text-xs text-slate-300 hover:bg-slate-800 flex items-center space-x-2 transition-colors cursor-pointer"
              >
                <Settings className="w-3.5 h-3.5 text-slate-400" />
                <span>Settings</span>
              </button>

              <button
                onClick={() => {
                  toggleTheme();
                  setIsProfileMenuOpen(false);
                }}
                className="w-full text-left px-3 py-2 rounded-xl text-xs text-slate-300 hover:bg-slate-800 flex items-center space-x-2 transition-colors cursor-pointer"
              >
                {theme === 'dark' ? (
                  <Moon className="w-3.5 h-3.5 text-indigo-400" />
                ) : (
                  <Sun className="w-3.5 h-3.5 text-amber-400" />
                )}
                <span>Theme ({theme})</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};
