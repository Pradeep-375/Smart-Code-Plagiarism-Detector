import { useAuth } from '../contexts/AuthContext'
import AdminDashboard from './AdminDashboard'
import FacultyDashboard from './FacultyDashboard'
import StudentDashboard from './StudentDashboard'

export default function Dashboard() {
  const { user } = useAuth()
  if (user?.role_name === 'admin') return <AdminDashboard />
  if (user?.role_name === 'faculty') return <FacultyDashboard />
  return <StudentDashboard />
}
