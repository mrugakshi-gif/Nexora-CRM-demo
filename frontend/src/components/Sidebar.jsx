import { useNavigate, Link } from 'react-router-dom';
import { LayoutDashboard, Users, Target, Briefcase, LogOut } from 'lucide-react';
import { auth } from '../services/firebase';
import { signOut } from 'firebase/auth';

export default function Sidebar() {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await signOut(auth);
      navigate('/login');
    } catch (err) {
      console.error("Logout failed", err);
    }
  };

  const navItems = [
    { name: 'Dashboard', icon: LayoutDashboard, path: '/' },
    { name: 'Leads', icon: Target, path: '/leads' },
    { name: 'Opportunities', icon: Briefcase, path: '/opportunities' },
    { name: 'Accounts', icon: Users, path: '/accounts' },
  ];

  return (
    <div className="flex w-64 flex-col border-r bg-white">
      <div className="flex h-16 items-center justify-center border-b px-4">
        <h1 className="text-xl font-bold text-blue-600">Indian B2B CRM</h1>
      </div>
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navItems.map((item) => (
          <Link
            key={item.name}
            to={item.path}
            className="group flex items-center rounded-md px-2 py-2 text-sm font-medium text-gray-600 hover:bg-blue-50 hover:text-blue-600"
          >
            <item.icon className="mr-3 h-5 w-5 flex-shrink-0 text-gray-400 group-hover:text-blue-600" />
            {item.name}
          </Link>
        ))}
      </nav>
      <div className="border-t p-4">
        <button
          onClick={handleLogout}
          className="group flex w-full items-center rounded-md px-2 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
        >
          <LogOut className="mr-3 h-5 w-5 flex-shrink-0 text-red-400 group-hover:text-red-600" />
          Logout
        </button>
      </div>
    </div>
  );
}
