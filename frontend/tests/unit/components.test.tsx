import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { DataTable } from '../../src/components/ui'
import ProtectedRoute from '../../src/components/ProtectedRoute'

const mockAuth = vi.hoisted(() => ({ value: { user: null as any, loading: false } }))
vi.mock('../../src/contexts/AuthContext', () => ({ useAuth: () => mockAuth.value }))

describe('DataTable', () => {
  const rows = [{ id: 1, name: 'Asha', role: 'faculty' }, { id: 2, name: 'Ravi', role: 'student' }]
  const columns = [{ key: 'name', header: 'Name', primary: true }, { key: 'role', header: 'Role' }]
  it('renders a table and a mobile card list from the same rows', () => {
    render(<DataTable rows={rows} columns={columns} rowKey={(r) => r.id} />)
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByTestId('mobile-cards').children).toHaveLength(2)
  })
  it('shows an empty state without rows', () => {
    render(<DataTable rows={[]} columns={columns} rowKey={(r: any) => r.id} />)
    expect(screen.getByText('Nothing here yet')).toBeInTheDocument()
  })
})

describe('ProtectedRoute', () => {
  const tree = (path: string) => (
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<div>login page</div>} />
        <Route path="/app/dashboard" element={<div>dashboard</div>} />
        <Route element={<ProtectedRoute roles={['admin']} />}><Route path="/app/users" element={<div>users page</div>} /></Route>
      </Routes>
    </MemoryRouter>
  )
  it('redirects anonymous visitors to login', () => {
    mockAuth.value = { user: null, loading: false }
    render(tree('/app/users'))
    expect(screen.getByText('login page')).toBeInTheDocument()
  })
  it('blocks a role that is not allowed', () => {
    mockAuth.value = { user: { role_name: 'student' }, loading: false }
    render(tree('/app/users'))
    expect(screen.getByText('dashboard')).toBeInTheDocument()
  })
  it('allows an admin', () => {
    mockAuth.value = { user: { role_name: 'admin' }, loading: false }
    render(tree('/app/users'))
    expect(screen.getByText('users page')).toBeInTheDocument()
  })
})
