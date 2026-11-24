import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './layouts/AppLayout'
import { Spinner } from './components/ui'
import { useAuth } from './contexts/AuthContext'

import Landing from './pages/Landing'
import { Login, Register, ForgotPassword, ResetPassword } from './pages/AuthPages'

const Dashboard = lazy(() => import('./pages/Dashboards'))
const Assignments = lazy(() => import('./pages/Assignments'))
const AssignmentDetail = lazy(() => import('./pages/AssignmentDetail'))
const SubmissionUpload = lazy(() => import('./pages/SubmissionUpload'))
const Analysis = lazy(() => import('./pages/Analysis'))
const Compare = lazy(() => import('./pages/Compare'))
const Reports = lazy(() => import('./pages/Reports'))
const UsersPage = lazy(() => import('./pages/UsersPage'))
const Notifications = lazy(() => import('./pages/Notifications'))
const Profile = lazy(() => import('./pages/Profile'))
const AuditLogs = lazy(() => import('./pages/AuditLogs'))

export default function App() {
  const { user } = useAuth()
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route path="/" element={user ? <Navigate to="/app/dashboard" replace /> : <Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/app" element={<AppLayout />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="assignments" element={<Assignments />} />
            <Route path="assignments/:id" element={<AssignmentDetail />} />
            <Route path="submit/:assignmentId?" element={<SubmissionUpload />} />
            <Route path="notifications" element={<Notifications />} />
            <Route path="profile" element={<Profile />} />
            <Route element={<ProtectedRoute roles={['admin', 'faculty']} />}>
              <Route path="analysis/:assignmentId?" element={<Analysis />} />
              <Route path="compare/:resultId" element={<Compare />} />
              <Route path="reports" element={<Reports />} />
            </Route>
            <Route element={<ProtectedRoute roles={['admin']} />}>
              <Route path="users" element={<UsersPage />} />
              <Route path="audit-logs" element={<AuditLogs />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
