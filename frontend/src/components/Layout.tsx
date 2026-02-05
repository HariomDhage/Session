import { Outlet, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, BookOpen, Users, Plus } from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Manuals', href: '/manuals', icon: BookOpen },
  { name: 'Sessions', href: '/sessions', icon: Users },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <div className="w-64 bg-gray-900 text-white">
        <div className="p-6">
          <h1 className="text-xl font-bold">Session Service</h1>
          <p className="text-gray-400 text-sm">AI Tutor Dashboard</p>
        </div>

        <nav className="mt-6">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href ||
              (item.href !== '/' && location.pathname.startsWith(item.href))
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center gap-3 px-6 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-gray-800 text-white border-r-2 border-blue-500'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <item.icon className="w-5 h-5" />
                {item.name}
              </Link>
            )
          })}
        </nav>

        <div className="mt-8 px-6">
          <p className="text-xs text-gray-500 uppercase font-semibold mb-3">Quick Actions</p>
          <Link
            to="/manuals/create"
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors mb-2"
          >
            <Plus className="w-4 h-4" />
            New Manual
          </Link>
          <Link
            to="/sessions/create"
            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Session
          </Link>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-auto">
        <main className="p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
